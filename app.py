from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Optional: Force HTTPS in production
@app.before_request
def redirect_to_https():
    if not app.debug and request.headers.get('X-Forwarded-Proto', 'http') == 'http':
        url = request.url.replace('http://', 'https://', 1)
        return redirect(url, code=301)

# Default route for the root URL
@app.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('index1_html'))
    return redirect(url_for('index_html'))

# Updated User model with separate username and email fields
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), nullable=False)  # Display name
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    
    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')
    
    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Non-authenticated homepage route
@app.route('/index.html')
def index_html():
    return render_template('index.html')

# Authenticated homepage route (logged-in experience)
@app.route('/index1.html')
@login_required
def index1_html():
    return render_template('index1.html')

# Explore route: if logged in, show explore1.html; else explore.html
@app.route('/explore.html')
def explore_html():
    if current_user_
