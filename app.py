# -*- coding: utf-8 -*-
import os
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import (LoginManager, UserMixin, login_user,
                         logout_user, login_required, current_user)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# Initialize Flask app with environment-based configuration.
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your_default_secret_key_here')

# Configure SQLAlchemy with an absolute path for SQLite.
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'site.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configure upload folder for videos.
app.config['UPLOAD_FOLDER'] = os.path.join(basedir, 'uploads')
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# ------------------------------------------------------------------
# Models
# ------------------------------------------------------------------

# User model for storing user details.
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), nullable=False)  # Display name
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    
    @property
    def password(self):
        raise AttributeError("password is not a readable attribute")
    
    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

# Video model for storing video upload information.
class Video(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    uploader_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    # Relationship to associate a video with its uploader.
    uploader = db.relationship('User', backref=db.backref('videos', lazy=True))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------

# Home page route.
# If a user is logged in, render the logged‑in homepage (index1.html). Otherwise, render index.html.
@app.route('/')
def home():
    if current_user.is_authenticated:
        return render_template('index1.html')
    else:
        return render_template('index.html')

# -------------------- Authentication Routes --------------------

# Login route: displays the login page and processes login submissions.
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Retrieve email and password from the login form.
        email = request.form.get('email')
        password = request.form.get('password')
        if not email or not password:
            flash("All fields are required.", "danger")
            return redirect(url_for('login'))
        user = User.query.filter_by(email=email).first()
        if user and user.verify_password(password):
            login_user(user, remember=True)  # Using remember=True to persist sessions.
            flash("Login successful!", "success")
            return redirect(url_for('home'))
        else:
            flash("Invalid email or password.", "danger")
            return redirect(url_for('login'))
    return render_template('login.html')

# Signup route: displays the signup page and processes signup submissions.
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        if not username or not email or not password:
            flash("All fields are required.", "danger")
            return redirect(url_for('signup'))
        if User.query.filter_by(email=email).first():
            flash("Email already exists.", "warning")
            return redirect(url_for('signup'))
        new_user = User(username=username, email=email)
        new_user.password = password  # This hashes the password.
        try:
            db.session.add(new_user)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            app.logger.error("Error creating user: %s", e)
            flash("Internal server error. Please try again later.", "danger")
            return redirect(url_for('signup'))
        flash("Account created! Welcome, {}.".format(username), "success")
        login_user(new_user, remember=True)
        return redirect(url_for('home'))
    return render_template('signup.html')

# Logout route: logs out the user.
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for('home'))

# -------------------- Functional Routes --------------------

# Explore route for logged-in users.
@app.route('/explore')
@login_required
def explore():
    # Replace with: return render_template('explore.html') if you have a template.
    return "<h1>Explore Page (Under Construction)</h1>"

# Upload route: Handles GET to display upload form and POST to process video upload.
@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        # Check if a video file part is in the request.
        if 'video' not in request.files:
            flash("No video file part.", "danger")
            return redirect(request.url)
        file = request.files['video']
        if file.filename == "":
            flash("No selected file.", "danger")
            return redirect(request.url)
        if file:
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            # Save video info in the database.
            new_video = Video(filename=filename, uploader_id=current_user.id)
            db.session.add(new_video)
            db.session.commit()
            flash("Video uploaded successfully!", "success")
            return redirect(url_for('home'))
    return render_template('upload.html')

# Profile route for logged-in users.
@app.route('/profile')
@login_required
def profile():
    # Replace with: return render_template('profile.html') if you have a template.
    return "<h1>Profile Page for {} (Under Construction)</h1>".format(current_user.username)

# Followers route for logged-in users.
@app.route('/followers')
@login_required
def followers():
    # Replace with: return render_template('followers.html') if you have a template.
    return "<h1>Followers Page (Under Construction)</h1>"

# ------------------------------------------------------------------

if __name__ == '__main__':
    with app.app_context():
        # Create the database tables if they do not exist.
        db.create_all()
    # Bind to 0.0.0.0 and use PORT from environment variables, defaulting to 5000 locally.
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
