import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy


app = Flask(__name__)

# Database configuration
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "requests.db")
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{DB_PATH}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'dev-secret-change-me'  # Change in production
db = SQLAlchemy(app)

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


@app.route("/" , methods=["GET"])
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

@app.route("/admin")
def admin():
    items = (RequestItem.query
             .order_by(RequestItem.created_at.desc())
             .all())
    return render_template("admin.html", items=items)

@app.route("/admin/<int:item_id>")
def detail(item_id):
    item = RequestItem.query.get_or_404(item_id)
    return render_template("detail.html", item=item)

@app.route("/admin/<int:item_id>/update", methods=["POST"])
def update(item_id):
    item = RequestItem.query.get_or_404(item_id)
    item.status = request.form.get("status", item.status)
    item.priority = request.form.get("priority", item.priority)
    db.session.commit()
    flash("Updated!", "success")
    return redirect(url_for("detail", item_id=item.id))

if __name__ == "__main__":
    app.run(debug=True)
