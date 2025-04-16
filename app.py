from flask import Flask, render_template_string, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import (LoginManager, UserMixin, login_user,
                         logout_user, login_required, current_user)
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'site.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    @property
    def password(self):
        raise AttributeError("Password is not readable.")

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Create the database tables
with app.app_context():
    db.create_all()

# Home route - dynamically show different HTML based on login state
@app.route('/')
def home():
    if current_user.is_authenticated:
        logged_in_html = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <title>Welcome, {{ current_user.username }}</title>
            <style>
              body {
                font-family: Arial, sans-serif;
                background: url("{{ url_for('static', filename='background1.gif') }}") no-repeat center center fixed;
                background-size: cover;
                margin: 0;
              }
              .navbar { background: #111; padding: 10px; }
              .navbar a { color: white; margin-right: 15px; text-decoration: none; }
              .content { padding: 20px; background: rgba(255, 255, 255, 0.9); margin: 20px; }
            </style>
        </head>
        <body>
            <div class="navbar">
              <a href="{{ url_for('home') }}">Home</a>
              <a href="{{ url_for('upload') }}">Upload Video</a>
              <a href="{{ url_for('livestream') }}">Livestream</a>
              <a href="{{ url_for('profile') }}">Profile</a>
              <a href="{{ url_for('logout') }}">Logout</a>
            </div>
            <div class="content">
              <h1>Welcome, {{ current_user.username }}</h1>
              <p>This is your personalized homepage where you can upload videos and go live.</p>
            </div>
        </body>
        </html>
        """
        return render_template_string(logged_in_html)
    else:
        unlogged_html = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <title>Welcome to Our Site</title>
            <style>
              body {
                font-family: Arial, sans-serif;
                background: url("{{ url_for('static', filename='background1.gif') }}") no-repeat center center fixed;
                background-size: cover;
                margin: 0;
                display: flex;
                align-items: center;
                justify-content: center;
                height: 100vh;
              }
              .login-container {
                background: rgba(255,255,255,0.9);
                padding: 30px;
                border-radius: 10px;
                text-align: center;
              }
              .login-container a {
                margin: 0 10px;
                text-decoration: none;
                color: #007bff;
              }
            </style>
        </head>
        <body>
            <div class="login-container">
              <h1>Welcome to Our Site!</h1>
              <p>Please <a href="{{ url_for('login') }}">Login</a> or <a href="{{ url_for('signup') }}">Sign Up</a></p>
            </div>
        </body>
        </html>
        """
        return render_template_string(unlogged_html)

# Login route using a simple inline HTML form
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        if not email or not password:
            flash("All fields are required.", "danger")
            return redirect(url_for('login'))
        user = User.query.filter_by(email=email).first()
        if user and user.verify_password(password):
            login_user(user)
            flash("Login successful!", "success")
            return redirect(url_for('home'))
        else:
            flash("Invalid email or password.", "danger")
            return redirect(url_for('login'))
    login_form = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <title>Login</title>
      <style>
        body { font-family: Arial, sans-serif; background: #f2f2f2; }
        .login-form { max-width: 400px; margin: 50px auto; background: #fff; padding: 20px; border-radius: 5px; }
        input { width: 100%; padding: 10px; margin: 10px 0; }
        button { padding: 10px; width: 100%; background: #111; color: #fff; border: none; border-radius: 5px; }
      </style>
    </head>
    <body>
      <div class="login-form">
        <h2>Login</h2>
        <form method="POST">
          <input type="text" name="email" placeholder="Email" required>
          <input type="password" name="password" placeholder="Password" required>
          <button type="submit">Login</button>
        </form>
        <p>Don't have an account? <a href="{{ url_for('signup') }}">Sign Up</a></p>
      </div>
    </body>
    </html>
    """
    return render_template_string(login_form)

# Signup route using inline HTML form
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
        new_user.password = password  # Password is hashed by the setter.
        db.session.add(new_user)
        db.session.commit()
        flash("Account created! Welcome, {}.".format(username), "success")
        login_user(new_user)
        return redirect(url_for('home'))
    signup_form = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <title>Sign Up</title>
      <style>
        body { font-family: Arial, sans-serif; background: #f2f2f2; }
        .signup-form { max-width: 400px; margin: 50px auto; background: #fff; padding: 20px; border-radius: 5px; }
        input { width: 100%; padding: 10px; margin: 10px 0; }
        button { padding: 10px; width: 100%; background: #111; color: #fff; border: none; border-radius: 5px; }
      </style>
    </head>
    <body>
      <div class="signup-form">
        <h2>Sign Up</h2>
        <form method="POST">
          <input type="text" name="username" placeholder="Username" required>
          <input type="text" name="email" placeholder="Email" required>
          <input type="password" name="password" placeholder="Password" required>
          <button type="submit">Sign Up</button>
        </form>
        <p>Already have an account? <a href="{{ url_for('login') }}">Login</a></p>
      </div>
    </body>
    </html>
    """
    return render_template_string(signup_form)

# Dummy routes for upload, livestream, profile, etc.
@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        # Dummy upload process. In a real app, process the file upload.
        flash("Video uploaded successfully!", "success")
        return redirect(url_for('home'))
    upload_page = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <title>Upload Video</title>
      <style>
        body { font-family: Arial, sans-serif; background: #f2f2f2; }
        .upload-form { max-width: 400px; margin: 50px auto; background: #fff; padding: 20px; border-radius: 5px; }
        input { width: 100%; padding: 10px; margin: 10px 0; }
        button { padding: 10px; width: 100%; background: #111; color: #fff; border: none; border-radius: 5px; }
      </style>
    </head>
    <body>
      <div class="upload-form">
        <h2>Upload Your Video</h2>
        <form method="POST" enctype="multipart/form-data">
          <input type="file" name="video" required>
          <button type="submit">Upload</button>
        </form>
      </div>
    </body>
    </html>
    """
    return render_template_string(upload_page)

@app.route('/livestream', methods=['GET', 'POST'])
@login_required
def livestream():
    livestream_page = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <title>Livestream</title>
      <style>
        body { font-family: Arial, sans-serif; background: #f2f2f2; text-align: center; padding-top: 50px; }
      </style>
    </head>
    <body>
      <h2>Livestream</h2>
      <p>Livestream functionality is under construction.</p>
      <a href="{{ url_for('home') }}">Back to Home</a>
    </body>
    </html>
    """
    return render_template_string(livestream_page)

@app.route('/profile')
@login_required
def profile():
    profile_page = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <title>Your Profile</title>
      <style>
        body { font-family: Arial, sans-serif; background: #f2f2f2; text-align: center; padding-top: 50px; }
      </style>
    </head>
    <body>
      <h2>Profile for {{ current_user.username }}</h2>
      <p>Profile functionality is under construction.</p>
      <a href="{{ url_for('home') }}">Back to Home</a>
    </body>
    </html>
    """
    return render_template_string(profile_page)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Logged out successfully!", "info")
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)
