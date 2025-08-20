import os
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create Flask app instance
app = Flask(__name__)

# Enable debug mode to see detailed errors
app.config['DEBUG'] = True

# Database configuration
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "requests.db")
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{DB_PATH}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", "dev-secret-change-me")

# Admin credentials from environment
ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASS", "changeme")

db = SQLAlchemy(app)

# Authentication helpers
def logged_in():
    return session.get("admin_logged_in") is True

def require_login(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not logged_in():
            flash("Please log in to access the admin area.", "warning")
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapper

# Request model
class RequestItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    contact = db.Column(db.String(180))
    title = db.Column(db.String(200), nullable=False)
    details = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(80))
    priority = db.Column(db.String(20), default='normal', nullable=False)  # low|normal|high
    status = db.Column(db.String(20), default='new', nullable=False)  # new|in_progress|done
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def as_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'contact': self.contact,
            'title': self.title,
            'details': self.details,
            'category': self.category,
            'priority': self.priority,
            'status': self.status,
            'created_at': self.created_at
        }

# CLI command to initialize database
@app.cli.command("init-db")
def init_db_cmd():
    db.create_all()
    print("✅ Database initialized:", DB_PATH)

# Routes
@app.route("/", methods=["GET"])
def home():
    return render_template("submit.html")

@app.route("/submit", methods=["POST"])
def submit():
    form = request.form
    name = (form.get("name") or "").strip()
    title = (form.get("title") or "").strip()
    details = (form.get("details") or "").strip()

    if not name or not title or not details:
        flash("Name, Title and Details are required.", "danger")
        return redirect(url_for("home"))

    item = RequestItem(
        name=name,
        contact=(form.get("contact") or "").strip(),
        title=title,
        details=details,
        category=(form.get("category") or "").strip() or None,
        priority=form.get("priority") or "normal",
    )

    db.session.add(item)
    db.session.commit()

    return render_template("thanks.html", item=item)

# Authentication routes
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if username == ADMIN_USER and password == ADMIN_PASS:
            session["admin_logged_in"] = True
            flash("Successfully logged in!", "success")
            next_url = request.args.get("next") or url_for("admin")
            return redirect(next_url)
        else:
            flash("Invalid credentials. Please try again.", "danger")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("Successfully logged out.", "success")
    return redirect(url_for("home"))

# Protected admin routes
@app.route("/admin")
@require_login
def admin():
    try:
        # Get query parameters
        q = request.args.get("q", "").strip()
        status = request.args.get("status", "")
        priority = request.args.get("priority", "")
        category = request.args.get("category", "")

        # Build query incrementally
        query = RequestItem.query

        # Text search across title, details, and name
        if q:
            like = f"%{q}%"
            query = query.filter(
                or_(
                    RequestItem.title.ilike(like),
                    RequestItem.details.ilike(like),
                    RequestItem.name.ilike(like),
                )
            )

        # Filter by status
        if status:
            query = query.filter_by(status=status)

        # Filter by priority
        if priority:
            query = query.filter_by(priority=priority)

        # Filter by category
        if category:
            query = query.filter_by(category=category)

        # Execute query with ordering
        items = query.order_by(RequestItem.created_at.desc()).all()

        # Get distinct categories for dropdown (excluding None/empty)
        categories = [c[0] for c in db.session.query(RequestItem.category).distinct().all() if c[0]]
        categories.sort()  # Sort alphabetically

        return render_template("admin.html",
                             items=items,
                             q=q,
                             status=status,
                             priority=priority,
                             category=category,
                             categories=categories)
    except Exception as e:
        return f"Error in admin route: {str(e)}"

@app.route("/admin/<int:item_id>")
@require_login
def detail(item_id):
    item = RequestItem.query.get_or_404(item_id)
    return render_template("detail.html", item=item)

@app.route("/admin/<int:item_id>/update", methods=["POST"])
@require_login
def update(item_id):
    item = RequestItem.query.get_or_404(item_id)
    item.status = request.form.get("status", item.status)
    item.priority = request.form.get("priority", item.priority)
    db.session.commit()
    flash("Updated!", "success")
    return redirect(url_for("detail", item_id=item.id))

# Run the app only if this file is executed directly
if __name__ == "__main__":
    app.run(debug=True)
