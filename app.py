import os
from datetime import datetime
from flask import Flask, render_template_string, request, redirect, url_for, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import (LoginManager, UserMixin, login_user,
                         logout_user, login_required, current_user)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'site.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configure upload folder and allowed extensions
UPLOAD_FOLDER = os.path.join(basedir, 'static/uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'mov', 'avi'}

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Many-to-many table for followers (self-referential relationship)
followers = db.Table('followers',
    db.Column('follower_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('followed_id', db.Integer, db.ForeignKey('user.id'))
)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    bio = db.Column(db.Text, default='')
    # For simplicity, profile_picture stores the filename (a default is provided)
    profile_picture = db.Column(db.String(120), default='default_profile.png')
    # One-to-many: user can have many videos
    videos = db.relationship('Video', backref='uploader', lazy=True)
    # Self-referential followers relationship
    followers = db.relationship(
        'User', secondary=followers,
        primaryjoin=(followers.c.followed_id == id),
        secondaryjoin=(followers.c.follower_id == id),
        backref=db.backref('following', lazy='dynamic'), lazy='dynamic'
    )

    @property
    def password(self):
        raise AttributeError("Password is not readable.")
    
    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

class Video(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(120), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    # is_livestream: if True, this record represents a livestream recording
    is_livestream = db.Column(db.Boolean, default=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

with app.app_context():
    db.create_all()

# Route to serve uploaded files (profile pictures and videos)
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Home route (shows navigation links)
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
            <a href="{{ url_for('explore') }}">Explore</a>
            <a href="{{ url_for('logout') }}">Logout</a>
          </div>
          <div class="content">
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

# Login route
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

# Signup route
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

# Upload route for video files
@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        if 'video' not in request.files:
            flash("No video file part", "danger")
            return redirect(request.url)
        file = request.files['video']
        if file.filename == '':
            flash("No selected file", "danger")
            return redirect(request.url)
        if file:
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            new_video = Video(filename=filename, user_id=current_user.id)
            db.session.add(new_video)
            db.session.commit()
            flash("Video uploaded successfully!", "success")
            return redirect(url_for('profile'))
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

# Livestream route with getUserMedia integration
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
        body { font-family: Arial, sans-serif; background: #f2f2f2; text-align: center; }
        video { width: 50%; margin-top: 20px; }
        button { padding: 10px 20px; background: #111; color: #fff; border: none; border-radius: 5px; cursor: pointer; }
        button:hover { background: #444; }
      </style>
    </head>
    <body>
      <h2>Go Live</h2>
      <button id="startBtn">Start Livestream</button>
      <div>
        <video id="liveVideo" autoplay muted></video>
      </div>
      <script>
        const startBtn = document.getElementById('startBtn');
        const liveVideo = document.getElementById('liveVideo');

        startBtn.addEventListener('click', async () => {
          if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
            try {
              const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
              liveVideo.srcObject = stream;
              // Here you could integrate WebRTC or another protocol to send the stream to a server.
              startBtn.disabled = true;
              startBtn.innerText = "Livestreaming...";
            } catch (error) {
              alert("Error accessing camera/microphone: " + error);
            }
          } else {
            alert("getUserMedia not supported in this browser.");
          }
        });
      </script>
      <br>
      <a href="{{ url_for('home') }}">Back to Home</a>
    </body>
    </html>
    """
    return render_template_string(livestream_page)

# Explore route: publicly display all uploaded videos (except livestreams)
@app.route('/explore')
def explore():
    videos = Video.query.filter_by(is_livestream=False).order_by(Video.timestamp.desc()).all()
    explore_page = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <title>Explore Videos</title>
      <style>
        body { font-family: Arial, sans-serif; background: #f2f2f2; padding: 20px; }
        .video-container { margin: 10px; display: inline-block; }
        video { width: 320px; height: 240px; background: #000; }
      </style>
    </head>
    <body>
      <h2>Explore Videos</h2>
      {% for vid in videos %}
        <div class="video-container">
          <p>Uploaded by: {{ vid.uploader.username }}</p>
          <video controls>
            <source src="{{ url_for('uploaded_file', filename=vid.filename) }}" type="video/mp4">
            Your browser does not support the video tag.
          </video>
        </div>
      {% endfor %}
      <br>
      <a href="{{ url_for('home') }}">Back to Home</a>
    </body>
    </html>
    """
    return render_template_string(explore_page, videos=videos)

# Profile route (GET and POST) to update bio and profile picture,
# while displaying the user's videos, livestream recordings, and followers.
@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    # If the form is submitted, update bio and profile picture
    if request.method == 'POST':
        bio = request.form.get('bio')
        current_user.bio = bio
        if 'profile_picture' in request.files:
            file = request.files['profile_picture']
            if file and file.filename != '':
                filename = secure_filename(file.filename)
                file_ext = filename.rsplit('.', 1)[1].lower()
                if file_ext in ALLOWED_IMAGE_EXTENSIONS:
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    current_user.profile_picture = filename
                else:
                    flash("Invalid image file.", "danger")
                    return redirect(url_for('profile'))
        db.session.commit()
        flash("Profile updated successfully!", "success")
        return redirect(url_for('profile'))

    # Retrieve user videos (non‑livestream), livestream recordings, and followers list.
    user_videos = Video.query.filter_by(user_id=current_user.id, is_livestream=False).order_by(Video.timestamp.desc()).all()
    user_livestreams = Video.query.filter_by(user_id=current_user.id, is_livestream=True).order_by(Video.timestamp.desc()).all()
    followers_list = current_user.followers.all()

    profile_page = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <title>Your Profile</title>
      <style>
        body { font-family: Arial, sans-serif; background: #f2f2f2; padding: 20px; }
        .profile-container { max-width: 800px; margin: 0 auto; background: #fff; padding: 20px; border-radius: 5px; }
        .profile-header { display: flex; align-items: center; }
        .profile-header img { width: 100px; height: 100px; border-radius: 50%; margin-right: 20px; }
        .profile-info { flex: 1; }
        .section { margin-top: 30px; }
        .video-item, .livestream-item, .follower-item { margin-bottom: 15px; }
        video { width: 320px; height: 240px; background: #000; }
      </style>
    </head>
    <body>
      <div class="profile-container">
        <div class="profile-header">
          <img src="{{ url_for('uploaded_file', filename=current_user.profile_picture) }}" alt="Profile Picture">
          <div class="profile-info">
            <h2>{{ current_user.username }}</h2>
            <p>{{ current_user.bio }}</p>
            <form method="POST" enctype="multipart/form-data">
              <textarea name="bio" rows="3" placeholder="Update your bio...">{{ current_user.bio }}</textarea><br>
              <input type="file" name="profile_picture">
              <button type="submit">Update Profile</button>
            </form>
          </div>
        </div>
        <div class="section">
          <h3>Your Videos</h3>
          {% for vid in user_videos %}
            <div class="video-item">
              <p>Uploaded on {{ vid.timestamp.strftime('%Y-%m-%d %H:%M') }}</p>
              <video controls>
                <source src="{{ url_for('uploaded_file', filename=vid.filename) }}" type="video/mp4">
                Your browser does not support the video tag.
              </video>
            </div>
          {% else %}
            <p>No videos uploaded yet.</p>
          {% endfor %}
        </div>
        <div class="section">
          <h3>Your Livestreams</h3>
          {% for live in user_livestreams %}
            <div class="livestream-item">
              <p>Livestream on {{ live.timestamp.strftime('%Y-%m-%d %H:%M') }}</p>
              <video controls>
                <source src="{{ url_for('uploaded_file', filename=live.filename) }}" type="video/mp4">
                Your browser does not support the video tag.
              </video>
            </div>
          {% else %}
            <p>No livestreams available.</p>
          {% endfor %}
        </div>
        <div class="section">
          <h3>Your Followers</h3>
          {% for follower in followers_list %}
            <div class="follower-item">
              <img src="{{ url_for('uploaded_file', filename=follower.profile_picture) }}" alt="Follower Picture" width="50" height="50">
              <span>{{ follower.username }}</span>
            </div>
          {% else %}
            <p>You have no followers yet.</p>
          {% endfor %}
        </div>
        <br>
        <a href="{{ url_for('home') }}">Back to Home</a>
      </div>
    </body>
    </html>
    """
    return render_template_string(profile_page, user_videos=user_videos, user_livestreams=user_livestreams, followers_list=followers_list)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Logged out successfully!", "info")
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)
