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

# User model – using "username" as the login credential
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
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

# Non‑authenticated homepage route
@app.route('/index.html')
def index_html():
    return render_template('index.html')

# Authenticated homepage route (protected)
@app.route('/index1.html')
@login_required
def index1_html():
    return render_template('index1.html')

# Explore route: if logged in, show explore1.html; otherwise, show explore.html
@app.route('/explore.html')
def explore_html():
    if current_user.is_authenticated:
        return render_template('explore1.html')
    return render_template('explore.html')

# Profile route (protected)
@app.route('/profile.html')
@login_required
def profile_html():
    return render_template('profile1.html')

# Upload route (protected)
@app.route('/upload.html')
@login_required
def upload_html():
    return render_template('upload1.html')

# Live route: if logged in, show video1.html; otherwise, video.html
@app.route('/live.html')
def live_html():
    if current_user.is_authenticated:
        return render_template('video1.html')
    return render_template('video.html')

# Login route – expects form fields "username" and "password"
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Get the username and password from the POSTed form
        username = request.form.get('username')
        password = request.form.get('password')
        if not username or not password:
            flash('All fields are required.', 'danger')
            return redirect(url_for('login'))
        user = User.query.filter_by(username=username).first()
        if user and user.verify_password(password):
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('index1_html'))
        else:
            flash('Invalid username or password.', 'danger')
            return redirect(url_for('login'))
    return render_template('login.html')

# Signup route – expects a username and password
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if not username or not password:
            flash('All fields are required.', 'danger')
            return redirect(url_for('signup'))
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists.', 'warning')
            return redirect(url_for('signup'))
        new_user = User(username=username)
        new_user.password = password
        db.session.add(new_user)
        db.session.commit()
        flash('Account created! You can now log in.', 'success')
        return redirect(url_for('login'))
    return render_template('signup.html')

# Logout route
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index_html'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Ensure database tables are created
    app.run(debug=True)
