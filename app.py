# ecosustain app

from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date, timedelta

# stting flask 
app = Flask(__name__)
app.config["SECRET_KEY"] = "change-this-key"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///ecosustain.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)


# user model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    display_name = db.Column(db.String(80), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
  
class ActionType(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    default_co2_saving = db.Column(db.Float, nullable=False)


# log 
class Log(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    action_type_id = db.Column(db.Integer, db.ForeignKey("action_type.id"), nullable=False)
    date = db.Column(db.Date, nullable=False)
    co2_saving = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship("User", backref="logs")
    action_type = db.relationship("ActionType")


# create tables and add default actions
def init_db():
    db.create_all()
    # add default actions if none exist
    if ActionType.query.count() == 0:
        actions = [
            ("Walked instead of driving", 1.5),
            ("Cycled instead of driving", 2.0),
            ("Used public transport", 1.0),
            ("Ate a vegetarian meal", 0.8),
            ("Reduced home energy use", 0.5),
        ]
        
        for name, co2 in actions:
            db.session.add(ActionType(name=name, default_co2_saving=co2))
        db.session.commit()


# decorator to check if logged in
def login_required(view):
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    wrapper.__name__ = view.__name__
    return wrapper

# get logged in user
def get_current_user():
    if "user_id" in session:
        return User.query.get(session["user_id"])
    return None


# home page
@app.route("/")
def index():
    if get_current_user():
        return redirect(url_for("dashboard"))
    return render_template("index.html")


# register page
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        # get form data
        email = request.form.get("email", "").strip().lower()
        name = request.form.get("display_name", "").strip()
        password = request.form.get("password", "")

        # check all fields done
        if not email or not name or not password:
            flash("All fields required.", "danger")
            return redirect(url_for("register"))

        # check email exist
        if User.query.filter_by(email=email).first():
            flash("Email exists.", "warning")
            return redirect(url_for("login"))

        # create user
        hashed = generate_password_hash(password)
        user = User(email=email, display_name=name, password_hash=hashed)
        db.session.add(user)
        db.session.commit()
        flash("Registered.", "success")
        return redirect(url_for("login"))
    return render_template("register.html")


# login page
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        # get form data
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        # find user
        user = User.query.filter_by(email=email).first()
        # check password
        if not user or not check_password_hash(user.password_hash, password):
            flash("Wrong details.", "danger")
            return redirect(url_for("login"))
        # log them in
        session["user_id"] = user.id
        flash("Logged in.", "success")
        return redirect(url_for("dashboard"))
    return render_template("login.html")


# logout
@app.route("/logout")
def logout():
    session.pop("user_id", None)
    flash("Logged out.", "info")
    return redirect(url_for("index"))

# dashboard page
@app.route("/dashboard")
@login_required
def dashboard():
    user = get_current_user()
    today = date.today()
    week_ago = today - timedelta(days=6)

    # get logs from last 7 days
    logs = Log.query.filter(Log.user_id == user.id, Log.date >= week_ago, Log.date <= today).order_by(Log.date.desc()).all()

    # calculate totals
    total_week = sum(l.co2_saving for l in logs)
    total_today = sum(l.co2_saving for l in logs if l.date == today)
    return render_template("dashboard.html", user=user, logs=logs, total_week=total_week, total_today=total_today)


# add new log
@app.route("/log/new", methods=["GET", "POST"])
@login_required
def new_log():
    action_types = ActionType.query.order_by(ActionType.name).all()

    if request.method == "POST":
        # get form data
        action_type_id = request.form.get("action_type")
        date_str = request.form.get("date")

        # validate action
        try:
            action_type_id = int(action_type_id)
        except:
            flash("Pick an action.", "danger")
            return redirect(url_for("new_log"))

        # get date
        if not date_str:
            log_date = date.today()
        else:
            log_date = datetime.strptime(date_str, "%Y-%m-%d").date()

        # save log
        action = ActionType.query.get(action_type_id)
        log = Log(user_id=get_current_user().id, action_type_id=action.id, date=log_date, co2_saving=action.default_co2_saving)
        db.session.add(log)
        db.session.commit()
        flash("Saved.", "success")
        return redirect(url_for("dashboard"))

    
    today_str = date.today().strftime("%Y-%m-%d")
    return render_template("new_log.html", action_types=action_types, today=today_str)


# logs page
@app.route("/logs")
@login_required
def all_logs():
    user = get_current_user()
    logs = Log.query.filter_by(user_id=user.id).order_by(Log.date.desc()).all()
    return render_template("logs.html", logs=logs)


# run app
if __name__ == "__main__":
    with app.app_context():
        init_db()
    app.run(debug=True)


