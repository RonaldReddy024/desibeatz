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

@app.route('/')
def home():
    """
    HOME ROUTE
    1. If user is logged in, show the sidebar with pink/black styling.
    2. If user is not logged in, show the 'welcome' splash with the same background.
    """
    if current_user.is_authenticated:
        logged_in_html = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <title>Welcome, {{ current_user.username }}</title>
            <style>
                body {
                    margin: 0;
                    padding: 0;
                    font-family: Arial, sans-serif;
                    /* Keep the same background image */
                    background: url("{{ url_for('static', filename='background1.gif') }}") no-repeat center center fixed;
                    background-size: cover;
                }
                .sidebar {
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 220px;
                    height: 100vh;
                    background-color: #000; /* black background */
                    display: flex;
                    flex-direction: column;
                    justify-content: space-between;
                }
                .sidebar ul {
                    list-style-type: none;
                    margin: 0;
                    padding: 0;
                }
                .sidebar li a {
                    display: block;
                    text-decoration: none;
                    color: #fff;
                    padding: 15px 20px;
                    transition: background-color 0.3s;
                }
                .sidebar li a:hover {
                    background-color: #ff0066; /* pink highlight on hover */
                }
                /* Optional heading or logo at the top of sidebar */
                .sidebar .sidebar-header {
                    color: #fff;
                    text-align: center;
                    padding: 20px;
                    font-weight: bold;
                }
                .login-btn, .logout-btn {
                    text-align: center;
                    padding: 20px;
                }
                .login-btn a, .logout-btn a {
                    text-decoration: none;
                    color: #fff;
                    background-color: #ff0066; /* pink button */
                    padding: 10px 20px;
                    border-radius: 4px;
                }
                /* Main content to the right of sidebar */
                .main-content {
                    margin-left: 220px; /* Same as sidebar width */
                    padding: 20px;
                    background: rgba(255, 255, 255, 0.9);
                    min-height: 100vh;
                }
            </style>
        </head>
        <body>
            <div class="sidebar">
                <div>
                    <div class="sidebar-header">
                        <h2>App Logo</h2>
                    </div>
                    <ul>
                        <!-- Example Sidebar Items -->
                        <li><a href="{{ url_for('home') }}">For You</a></li>
                        <li><a href="{{ url_for('home') }}">Explore</a></li>
                        <li><a href="{{ url_for('home') }}">Following</a></li>
                        <li><a href="{{ url_for('upload') }}">Upload</a></li>
                        <li><a href="{{ url_for('livestream') }}">LIVE</a></li>
                        <li><a href="{{ url_for('profile') }}">Profile</a></li>
                    </ul>
                </div>
                <div class="logout-btn">
                    <a href="{{ url_for('logout') }}">Logout</a>
                </div>
            </div>
            <div class="main-content">
                <h1>Welcome, {{ current_user.username }}</h1>
                <p>This is your personalized homepage where you can upload videos, go live, and more!</p>
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
                    margin: 0;
                    padding: 0;
                    font-family: Arial, sans-serif;
                    /* Keep the same background image */
                    background: url("{{ url_for('static', filename='background1.gif') }}") no-repeat center center fixed;
                    background-size: cover;
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
                    color: #ff0066; /* Pink links */
                    font-weight: bold;
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
        body {
          font-family: Arial, sans-serif;
          background: #f2f2f2;
          margin: 0; 
          padding: 0;
          display: flex; 
          justify-content: center; 
          align-items: center;
          height: 100vh;
        }
        .login-form {
          max-width: 400px;
          width: 90%;
          background: #fff;
          padding: 20px;
          border-radius: 5px;
          box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }
        input {
          width: 100%;
          padding: 10px; 
          margin: 10px 0; 
          box-sizing: border-box;
        }
        button {
          padding: 10px; 
          width: 100%; 
          background: #111; 
          color: #fff; 
          border: none; 
          border-radius: 5px;
          cursor: pointer;
        }
        button:hover {
          background: #444;
        }
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
        new_user.password = password
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
        body {
          font-family: Arial, sans-serif;
          background: #f2f2f2;
          margin: 0; 
          padding: 0;
          display: flex; 
          justify-content: center; 
          align-items: center;
          height: 100vh;
        }
        .signup-form {
          max-width: 400px;
          width: 90%;
          background: #fff;
          padding: 20px;
          border-radius: 5px;
          box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }
        input {
          width: 100%;
          padding: 10px; 
          margin: 10px 0; 
          box-sizing: border-box;
        }
        button {
          padding: 10px; 
          width: 100%; 
          background: #111; 
          color: #fff; 
          border: none; 
          border-radius: 5px;
          cursor: pointer;
        }
        button:hover {
          background: #444;
        }
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

@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        flash("Video uploaded successfully!", "success")
        return redirect(url_for('home'))

    # Same sidebar layout for consistency
    upload_page = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <title>Upload Video</title>
      <style>
        body {
          margin: 0;
          padding: 0;
          font-family: Arial, sans-serif;
          background: url("{{ url_for('static', filename='background1.gif') }}") no-repeat center center fixed;
          background-size: cover;
        }
        .sidebar {
            position: fixed;
            top: 0;
            left: 0;
            width: 220px;
            height: 100vh;
            background-color: #000;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }
        .sidebar ul {
            list-style-type: none;
            margin: 0;
            padding: 0;
        }
        .sidebar li a {
            display: block;
            text-decoration: none;
            color: #fff;
            padding: 15px 20px;
            transition: background-color 0.3s;
        }
        .sidebar li a:hover {
            background-color: #ff0066;
        }
        .sidebar .sidebar-header {
            color: #fff;
            text-align: center;
            padding: 20px;
            font-weight: bold;
        }
        .logout-btn {
            text-align: center;
            padding: 20px;
        }
        .logout-btn a {
            text-decoration: none;
            color: #fff;
            background-color: #ff0066;
            padding: 10px 20px;
            border-radius: 4px;
        }
        .main-content {
            margin-left: 220px;
            padding: 20px;
            background: rgba(255, 255, 255, 0.9);
            min-height: 100vh;
        }
        .upload-form {
          max-width: 400px;
          margin: 50px auto;
          background: #fff;
          padding: 20px;
          border-radius: 5px;
        }
        input {
          width: 100%;
          padding: 10px; 
          margin: 10px 0; 
          box-sizing: border-box;
        }
        button {
          padding: 10px; 
          width: 100%; 
          background: #111; 
          color: #fff; 
          border: none; 
          border-radius: 5px;
          cursor: pointer;
        }
        button:hover {
          background: #444;
        }
      </style>
    </head>
    <body>
      <div class="sidebar">
        <div>
            <div class="sidebar-header">
                <h2>App Logo</h2>
            </div>
            <ul>
                <li><a href="{{ url_for('home') }}">For You</a></li>
                <li><a href="{{ url_for('home') }}">Explore</a></li>
                <li><a href="{{ url_for('home') }}">Following</a></li>
                <li><a href="{{ url_for('upload') }}">Upload</a></li>
                <li><a href="{{ url_for('livestream') }}">LIVE</a></li>
                <li><a href="{{ url_for('profile') }}">Profile</a></li>
            </ul>
        </div>
        <div class="logout-btn">
            <a href="{{ url_for('logout') }}">Logout</a>
        </div>
      </div>
      <div class="main-content">
        <h2>Upload Your Video</h2>
        <div class="upload-form">
          <form method="POST" enctype="multipart/form-data">
            <input type="file" name="video" required>
            <button type="submit">Upload</button>
          </form>
        </div>
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
        body {
            margin: 0;
            padding: 0;
            font-family: Arial, sans-serif;
            background: url("{{ url_for('static', filename='background1.gif') }}") no-repeat center center fixed;
            background-size: cover;
        }
        .sidebar {
            position: fixed;
            top: 0;
            left: 0;
            width: 220px;
            height: 100vh;
            background-color: #000;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }
        .sidebar ul {
            list-style-type: none;
            margin: 0;
            padding: 0;
        }
        .sidebar li a {
            display: block;
            text-decoration: none;
            color: #fff;
            padding: 15px 20px;
            transition: background-color 0.3s;
        }
        .sidebar li a:hover {
            background-color: #ff0066;
        }
        .sidebar .sidebar-header {
            color: #fff;
            text-align: center;
            padding: 20px;
            font-weight: bold;
        }
        .logout-btn {
            text-align: center;
            padding: 20px;
        }
        .logout-btn a {
            text-decoration: none;
            color: #fff;
            background-color: #ff0066;
            padding: 10px 20px;
            border-radius: 4px;
        }
        .main-content {
            margin-left: 220px;
            padding: 20px;
            background: rgba(255, 255, 255, 0.9);
            min-height: 100vh;
            text-align: center;
        }
      </style>
    </head>
    <body>
      <div class="sidebar">
        <div>
            <div class="sidebar-header">
                <h2>App Logo</h2>
            </div>
            <ul>
                <li><a href="{{ url_for('home') }}">For You</a></li>
                <li><a href="{{ url_for('home') }}">Explore</a></li>
                <li><a href="{{ url_for('home') }}">Following</a></li>
                <li><a href="{{ url_for('upload') }}">Upload</a></li>
                <li><a href="{{ url_for('livestream') }}">LIVE</a></li>
                <li><a href="{{ url_for('profile') }}">Profile</a></li>
            </ul>
        </div>
        <div class="logout-btn">
            <a href="{{ url_for('logout') }}">Logout</a>
        </div>
      </div>
      <div class="main-content">
        <h2>Livestream</h2>
        <p>Livestream functionality is under construction.</p>
        <a href="{{ url_for('home') }}">Back to Home</a>
      </div>
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
        body {
            margin: 0;
            padding: 0;
            font-family: Arial, sans-serif;
            background: url("{{ url_for('static', filename='background1.gif') }}") no-repeat center center fixed;
            background-size: cover;
        }
        .sidebar {
            position: fixed;
            top: 0;
            left: 0;
            width: 220px;
            height: 100vh;
            background-color: #000;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }
        .sidebar ul {
            list-style-type: none;
            margin: 0;
            padding: 0;
        }
        .sidebar li a {
            display: block;
            text-decoration: none;
            color: #fff;
            padding: 15px 20px;
            transition: background-color 0.3s;
        }
        .sidebar li a:hover {
            background-color: #ff0066;
        }
        .sidebar .sidebar-header {
            color: #fff;
            text-align: center;
            padding: 20px;
            font-weight: bold;
        }
        .logout-btn {
            text-align: center;
            padding: 20px;
        }
        .logout-btn a {
            text-decoration: none;
            color: #fff;
            background-color: #ff0066;
            padding: 10px 20px;
            border-radius: 4px;
        }
        .main-content {
            margin-left: 220px;
            padding: 20px;
            background: rgba(255, 255, 255, 0.9);
            min-height: 100vh;
            text-align: center;
        }
      </style>
    </head>
    <body>
      <div class="sidebar">
        <div>
            <div class="sidebar-header">
                <h2>App Logo</h2>
            </div>
            <ul>
                <li><a href="{{ url_for('home') }}">For You</a></li>
                <li><a href="{{ url_for('home') }}">Explore</a></li>
                <li><a href="{{ url_for('home') }}">Following</a></li>
                <li><a href="{{ url_for('upload') }}">Upload</a></li>
                <li><a href="{{ url_for('livestream') }}">LIVE</a></li>
                <li><a href="#">Profile</a></li>
            </ul>
        </div>
        <div class="logout-btn">
            <a href="{{ url_for('logout') }}">Logout</a>
        </div>
      </div>
      <div class="main-content">
        <h2>Profile for {{ current_user.username }}</h2>
        <p>Profile functionality is under construction.</p>
        <a href="{{ url_for('home') }}">Back to Home</a>
      </div>
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
