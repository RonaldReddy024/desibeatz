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

# Default route that redirects to /index.html
@app.route('/')
def home():
    return redirect(url_for('index_html'))

# User model
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

# Explicit routes with .html URLs

@app.route('/index.html')
def index_html():
    if current_user.is_authenticated:
        app.logger.debug("Rendering index1.html for authenticated user.")
        return render_template('index1.html')
    app.logger.debug("Rendering index.html for non-authenticated user.")
    return render_template('index.html')

@app.route('/explore.html')
def explore_html():
    if current_user.is_authenticated:
        app.logger.debug("Rendering explore1.html for authenticated user.")
        return render_template('explore1.html')
    app.logger.debug("Rendering explore.html for non-authenticated user.")
    return render_template('explore.html')

@app.route('/profile.html')
@login_required
def profile_html():
    app.logger.debug("Rendering profile1.html for authenticated user.")
    return render_template('profile1.html')

@app.route('/upload.html')
@login_required
def upload_html():
    app.logger.debug("Rendering upload1.html for authenticated user.")
    return render_template('upload1.html')

@app.route('/live.html')
def live_html():
    if current_user.is_authenticated:
        app.logger.debug("Rendering video1.html for authenticated user.")
        return render_template('video1.html')
    app.logger.debug("Rendering video.html for non-authenticated user.")
    return render_template('video.html')

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if not username or not password:
            flash('All fields are required.', 'danger')
            return redirect(url_for('login'))
        user = User.query.filter_by(username=username).first()
        if user and user.verify_password(password):
            login_user(user)
            flash('Login successful!', 'success')
            app.logger.debug("Login successful for user: %s", username)
            return redirect(url_for('index_html'))
        else:
            flash('Invalid username or password.', 'danger')
            app.logger.debug("Login failed for user: %s", username)
    return render_template('login.html')

# Signup route
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
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
        flash('Account created! Please log in.', 'success')
        app.logger.debug("New user created: %s", username)
        return redirect(url_for('login'))
    return render_template('signup.html')

# Logout route
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    app.logger.debug("User logged out.")
    return redirect(url_for('index_html'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Ensure the database and tables are created
    app.run(debug=True)
