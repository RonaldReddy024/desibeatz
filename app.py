# -*- coding: utf-8 -*-
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'  # Replace with a strong secret key that stays constant
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

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

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Home page route.
# If the user is logged in, render the logged‑in homepage (index1.html)
# If not, render the non‑logged‑in homepage (index.html)
@app.route('/')
def home():
    if current_user.is_authenticated:
        return render_template('index1.html')
    else:
        return render_template('index.html')

# Login route – displays the login page and processes login submissions.
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
            # Adding remember=True so that the login persists beyond the current session.
            login_user(user, remember=True)
            flash("Login successful!", "success")
            return redirect(url_for('home'))
        else:
            flash("Invalid email or password.", "danger")
            return redirect(url_for('login'))
    return render_template('login.html')

# Signup route – displays the signup page and processes signup submissions.
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
        new_user.password = password  # This uses the password setter to hash the password.
        try:
            db.session.add(new_user)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            app.logger.error("Error creating user: %s", e)
            flash("Internal server error. Please try again later.", "danger")
            return redirect(url_for('signup'))
        flash("Account created! Welcome, {}.".format(username), "success")
        # Also use remember=True here.
        login_user(new_user, remember=True)
        return redirect(url_for('home'))
    return render_template('signup.html')

# Logout route – logs the user out and redirects to the home page.
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for('home'))

if __name__ == '__main__':
    with app.app_context():
        # Create the database tables if they do not exist.
        # Remove or comment out db.drop_all() to ensure that user data persists.
        # db.drop_all()  
        db.create_all()
    app.run(debug=True)
