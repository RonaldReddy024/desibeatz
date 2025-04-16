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

# Many-to-many tables for followers, likes, and bookmarks
followers = db.Table('followers',
    db.Column('follower_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('followed_id', db.Integer, db.ForeignKey('user.id'))
)

likes_table = db.Table('likes',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('video_id', db.Integer, db.ForeignKey('video.id'))
)

bookmarks_table = db.Table('bookmarks',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('video_id', db.Integer, db.ForeignKey('video.id'))
)

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    bio = db.Column(db.Text, default='')
    # profile_picture stores the filename (a default is provided)
    profile_picture = db.Column(db.String(120), default='default_profile.png')
    # One-to-many: a user can have many videos
    videos = db.relationship('Video', backref='uploader', lazy=True)
    # Self-referential followers relationship
    followers = db.relationship(
        'User', secondary=followers,
        primaryjoin=(followers.c.followed_id == id),
        secondaryjoin=(followers.c.follower_id == id),
        backref=db.backref('following', lazy='dynamic'), lazy='dynamic'
    )
    # Relationship for comments (if needed)
    comments = db.relationship('Comment', backref='author', lazy=True)

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
    title = db.Column(db.String(255), nullable=False)  # Video title
    filename = db.Column(db.String(120), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    # if True, this record represents a livestream recording
    is_livestream = db.Column(db.Boolean, default=False)
    # Relationships for interactive features:
    liked_by = db.relationship('User', secondary=likes_table, backref=db.backref('liked_videos', lazy='dynamic'))
    bookmarked_by = db.relationship('User', secondary=bookmarks_table, backref=db.backref('bookmarked_videos', lazy='dynamic'))
    comments = db.relationship('Comment', backref='video', lazy=True)

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    video_id = db.Column(db.Integer, db.ForeignKey('video.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

with app.app_context():
    db.create_all()

# Route to serve uploaded files (profile pictures and videos)
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# --------------------- Sidebar Template (Always Visible) ----------------------
# This sidebar will be visible on the homepage (and can be included elsewhere)
sidebar_template = """
<div class="sidebar">
  <div class="sidebar-header">
    <img src="{{ url_for('static', filename='images/desibeatz_logo.png') }}" alt="Logo" style="width:150px; display:block; margin: 0 auto;">
  </div>
  <ul>
    <li><a href="{{ url_for('home') }}">Home</a></li>
    <li><a href="{{ url_for('upload') }}">Upload Video</a></li>
    <li><a href="{{ url_for('livestream') }}">Livestream</a></li>
    {% if current_user.is_authenticated %}
      <li><a href="{{ url_for('profile') }}">Profile</a></li>
      <li><a href="{{ url_for('logout') }}">Logout</a></li>
    {% else %}
      <li><a href="{{ url_for('login') }}">Login</a></li>
      <li><a href="{{ url_for('signup') }}">Sign Up</a></li>
    {% endif %}
    <li><a href="{{ url_for('explore') }}">Explore</a></li>
  </ul>
</div>
<style>
  .sidebar {
    position: fixed;
    top: 0;
    left: 0;
    width: 220px;
    height: 100vh;
    background-color: #000;
    color: #fff;
    padding-top: 20px;
  }
  .sidebar .sidebar-header {
    text-align: center;
    margin-bottom: 20px;
  }
  .sidebar ul {
    list-style-type: none;
    padding: 0;
  }
  .sidebar ul li {
    margin: 15px 0;
  }
  .sidebar ul li a {
    color: #fff;
    text-decoration: none;
    font-weight: bold;
    display: block;
    padding: 10px 20px;
  }
  .sidebar ul li a:hover {
    background-color: #ff0066;
  }
</style>
"""

# --------------------- Routes ----------------------

# Home route: displays a default video feed with the sidebar always visible.
@app.route('/')
def home():
    videos = Video.query.order_by(Video.timestamp.desc()).all()
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <title>Welcome to Desibeatz</title>
      <style>
        body {
          font-family: Arial, sans-serif;
          background: url("{{ url_for('static', filename='background1.gif') }}") no-repeat center center fixed;
          background-size: cover;
          margin: 0;
        }
        .main-content {
          margin-left: 220px;
          padding: 20px;
          background: rgba(255, 255, 255, 0.9);
          min-height: 100vh;
        }
        .video-grid {
          display: flex;
          flex-wrap: wrap;
          gap: 20px;
        }
        .video-item {
          width: 320px;
          background: #fff;
          padding: 10px;
          border-radius: 5px;
        }
        .video-item video {
          width: 100%;
          height: auto;
        }
      </style>
    </head>
    <body>
      {%% include 'sidebar' %%}
      <div class="main-content">
        <h1>Welcome to Desibeatz</h1>
        <div class="video-grid">
          {% for vid in videos %}
            <div class="video-item">
              <h3>{{ vid.title }}</h3>
              <p>By: {{ vid.uploader.username }} on {{ vid.timestamp.strftime('%Y-%m-%d %H:%M') }}</p>
              <video controls>
                <source src="{{ url_for('uploaded_file', filename=vid.filename) }}" type="video/mp4">
                Your browser does not support the video tag.
              </video>
            </div>
          {% endfor %}
        </div>
      </div>
    </body>
    </html>
    """
    # Inject sidebar_template into the HTML by replacing the placeholder
    html = html.replace("{%% include 'sidebar' %%}", sidebar_template)
    return render_template_string(html, videos=videos)

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

# Upload route for video files (with title input)
@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        title = request.form.get('title')
        if not title:
            flash("Please provide a video title.", "danger")
            return redirect(url_for('upload'))
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
            new_video = Video(title=title, filename=filename, user_id=current_user.id, is_livestream=False)
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
        input, textarea { width: 100%; padding: 10px; margin: 10px 0; }
        button { padding: 10px; width: 100%; background: #111; color: #fff; border: none; border-radius: 5px; }
      </style>
    </head>
    <body>
      <div class="upload-form">
        <h2>Upload Your Video</h2>
        <form method="POST" enctype="multipart/form-data">
          <input type="text" name="title" placeholder="Video Title" required>
          <input type="file" name="video" required>
          <button type="submit">Upload</button>
        </form>
      </div>
    </body>
    </html>
    """
    return render_template_string(upload_page)

# Livestream route with getUserMedia integration and title input
@app.route('/livestream', methods=['GET', 'POST'])
@login_required
def livestream():
    if request.method == 'POST':
        title = request.form.get('title')
        if not title:
            flash("Please provide a livestream title.", "danger")
            return redirect(url_for('livestream'))
        # Simulate livestream saving by creating a dummy video record.
        dummy_filename = "livestream_" + secure_filename(title) + ".mp4"
        new_video = Video(title=title, filename=dummy_filename, user_id=current_user.id, is_livestream=True)
        db.session.add(new_video)
        db.session.commit()
        flash("Livestream recorded successfully (simulation)!", "success")
        return redirect(url_for('profile'))
    livestream_page = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <title>Livestream</title>
      <style>
        body { font-family: Arial, sans-serif; background: #f2f2f2; text-align: center; }
        video { width: 50%; margin-top: 20px; }
        input { padding: 10px; margin: 10px 0; width: 50%; }
        button { padding: 10px 20px; background: #111; color: #fff; border: none; border-radius: 5px; cursor: pointer; }
        button:hover { background: #444; }
      </style>
    </head>
    <body>
      <h2>Go Live</h2>
      <form method="POST">
        <input type="text" name="title" placeholder="Livestream Title" required><br>
        <button id="startBtn" type="button">Start Livestream Preview</button>
        <button type="submit" style="margin-left:10px;">Save Livestream</button>
      </form>
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

# Explore route: publicly display all uploaded videos (with interactive features)
@app.route('/explore', methods=['GET', 'POST'])
def explore():
    if request.method == 'POST' and current_user.is_authenticated:
        video_id = request.form.get('video_id')
        comment_text = request.form.get('comment')
        if video_id and comment_text:
            new_comment = Comment(content=comment_text, user_id=current_user.id, video_id=int(video_id))
            db.session.add(new_comment)
            db.session.commit()
            flash("Comment added!", "success")
            return redirect(url_for('explore'))
    videos = Video.query.order_by(Video.timestamp.desc()).all()
    explore_page = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <title>Explore Videos</title>
      <style>
        body { font-family: Arial, sans-serif; background: #f2f2f2; padding: 20px; }
        .video-container { margin: 10px; display: inline-block; vertical-align: top; width: 340px; background: #fff; padding: 10px; border-radius: 5px; }
        video { width: 320px; height: 240px; background: #000; display: block; margin-bottom: 10px; }
        .actions button { margin-right: 5px; padding: 5px 10px; background: #111; color: #fff; border: none; border-radius: 3px; cursor: pointer; }
        .actions button:hover { background: #444; }
        .comment-section { margin-top: 10px; }
        .comment { background: #eee; padding: 5px; border-radius: 3px; margin-bottom: 5px; }
      </style>
    </head>
    <body>
      {%% include 'sidebar' %%}
      <div class="main-content" style="margin-left:220px; padding:20px;">
        <h2>Explore Videos</h2>
        {% for vid in videos %}
          <div class="video-container">
            <h3>{{ vid.title }}</h3>
            <p>Uploaded by: {{ vid.uploader.username }} on {{ vid.timestamp.strftime('%Y-%m-%d %H:%M') }}</p>
            <video controls>
              <source src="{{ url_for('uploaded_file', filename=vid.filename) }}" type="video/mp4">
              Your browser does not support the video tag.
            </video>
            <div class="actions">
              <a href="{{ url_for('toggle_like', video_id=vid.id) }}">
                <button>Like ({{ vid.liked_by|length }})</button>
              </a>
              <a href="{{ url_for('toggle_bookmark', video_id=vid.id) }}">
                <button>Bookmark ({{ vid.bookmarked_by|length }})</button>
              </a>
              <button onclick="alert('Share Link: {{ url_for('uploaded_file', filename=vid.filename, _external=True) }}')">Share</button>
            </div>
            <div class="comment-section">
              <h4>Comments:</h4>
              {% for c in vid.comments %}
                <div class="comment">
                  <strong>{{ c.author.username }}</strong>: {{ c.content }}<br>
                  <small>{{ c.timestamp.strftime('%Y-%m-%d %H:%M') }}</small>
                </div>
              {% endfor %}
              {% if current_user.is_authenticated %}
              <form method="POST" action="{{ url_for('explore') }}">
                <input type="hidden" name="video_id" value="{{ vid.id }}">
                <input type="text" name="comment" placeholder="Add a comment..." required style="width:80%;">
                <button type="submit">Comment</button>
              </form>
              {% endif %}
            </div>
          </div>
        {% endfor %}
        <br>
        <a href="{{ url_for('home') }}">Back to Home</a>
      </div>
    </body>
    </html>
    """
    explore_page = explore_page.replace("{%% include 'sidebar' %%}", sidebar_template)
    return render_template_string(explore_page, videos=videos)

# Endpoints for like and bookmark toggling
@app.route('/like/<int:video_id>')
@login_required
def toggle_like(video_id):
    video = Video.query.get_or_404(video_id)
    if current_user in video.liked_by:
        video.liked_by.remove(current_user)
    else:
        video.liked_by.append(current_user)
    db.session.commit()
    return redirect(request.referrer or url_for('explore'))

@app.route('/bookmark/<int:video_id>')
@login_required
def toggle_bookmark(video_id):
    video = Video.query.get_or_404(video_id)
    if current_user in video.bookmarked_by:
        video.bookmarked_by.remove(current_user)
    else:
        video.bookmarked_by.append(current_user)
    db.session.commit()
    return redirect(request.referrer or url_for('explore'))

# Profile route: update bio/profile picture and display user videos, livestreams, and followers.
@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
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
        .profile-container { max-width: 900px; margin: 0 auto; background: #fff; padding: 20px; border-radius: 5px; }
        .profile-header { display: flex; align-items: center; }
        .profile-header img { width: 120px; height: 120px; border-radius: 50%; margin-right: 20px; }
        .profile-info { flex: 1; }
        .section { margin-top: 30px; }
        .video-item { margin-bottom: 15px; }
        video { width: 320px; height: 240px; background: #000; }
        .follower-item { display: inline-block; text-align: center; margin: 5px; }
        .follower-item img { border-radius: 50%; }
      </style>
    </head>
    <body>
      {%% include 'sidebar' %%}
      <div class="profile-container" style="margin-left:220px;">
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
              <h4>{{ vid.title }}</h4>
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
            <div class="video-item">
              <h4>{{ live.title }}</h4>
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
              <img src="{{ url_for('uploaded_file', filename=follower.profile_picture) }}" alt="Follower" width="50" height="50"><br>
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
    profile_page = profile_page.replace("{%% include 'sidebar' %%}", sidebar_template)
    return render_template_string(profile_page, user_videos=user_videos, user_livestreams=user_livestreams, followers_list=followers_list)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Logged out successfully!", "info")
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)
