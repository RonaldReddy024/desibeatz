import os
from datetime import datetime
from flask import Flask, render_template_string, request, redirect, url_for, flash, send_from_directory, abort
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

# Configure upload folder
UPLOAD_FOLDER = os.path.join(basedir, 'static/uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Allowed file extensions
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'mov', 'avi'}

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login_route'

# Many-to-many association tables
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

# ----- Models -----
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), nullable=False)  # also used for profile URLs
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    bio = db.Column(db.Text, default='')
    profile_picture = db.Column(db.String(120), default='default_profile.png')
    videos = db.relationship('Video', backref='uploader', lazy=True)
    followers = db.relationship(
        'User', secondary=followers,
        primaryjoin=(followers.c.followed_id == id),
        secondaryjoin=(followers.c.follower_id == id),
        backref=db.backref('following', lazy='dynamic'), lazy='dynamic'
    )
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
    title = db.Column(db.String(255), nullable=False)
    # Save filename in lower-case to help ensure proper type matching
    filename = db.Column(db.String(120), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    is_livestream = db.Column(db.Boolean, default=False)
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

# ----- Serve uploaded files -----
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# ----- SIDEBAR (Displayed on all pages) -----
# Indian-inspired colour scheme with our logo
sidebar_template = """
<div class="sidebar">
  <div class="sidebar-header">
    <img src="{{ url_for('static', filename='images/desibeatz_logo.png') }}" alt="Logo" style="width:150px; display:block; margin:0 auto;">
  </div>
  <ul>
    <li><a href="{{ url_for('home') }}">For You</a></li>
    <li><a href="{{ url_for('explore') }}">Explore</a></li>
    <li><a href="{{ url_for('following') }}">Following</a></li>
    <li><a href="{{ url_for('upload') }}">Upload</a></li>
    <li><a href="{{ url_for('livestream') }}">LIVE</a></li>
    <li><a href="{{ url_for('profile') }}">Profile</a></li>
    <li><a href="#">More</a></li>
    {% if current_user.is_authenticated %}
      <li style="margin-top:40px;"><a href="{{ url_for('logout_route') }}">Logout</a></li>
    {% else %}
      <li style="margin-top:40px;"><a href="{{ url_for('login_route') }}">Log in</a></li>
    {% endif %}
  </ul>
</div>
<style>
  @import url('https://fonts.cdnfonts.com/css/proxima-nova-2');
  body {
    font-family: 'Proxima Nova', Arial, sans-serif;
    margin: 0;
    padding: 0;
    background-color: #000;
    color: #fff;
  }
  .sidebar {
    position: fixed;
    top: 0;
    left: 0;
    width: 220px;
    height: 100vh;
    background-color: #290012;
    padding-top: 20px;
    z-index: 999;
  }
  .sidebar .sidebar-header {
    text-align: center;
    margin-bottom: 20px;
  }
  .sidebar ul {
    list-style: none;
    padding: 0;
  }
  .sidebar ul li {
    margin: 10px 0;
  }
  .sidebar ul li a {
    color: #fff;
    text-decoration: none;
    padding: 10px 20px;
    display: block;
  }
  .sidebar ul li a:hover {
    background-color: #ff0066;
  }
</style>
"""

# ----- HOME (For You) Page -----
# Show all videos (including livestreams)
@app.route('/')
def home():
    videos = Video.query.order_by(Video.timestamp.desc()).all()
    home_html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <title>Desibeatz - For You</title>
      <style>
        body {
          background: url("{{ url_for('static', filename='background1.gif') }}") no-repeat center center fixed;
          background-size: cover;
          color: #fff;
        }
        .main-content {
          margin-left: 220px;
          padding: 20px;
        }
        .welcome-message {
          text-align: left;
          color: #fff;
          font-size: 2em;
          font-weight: 600;
          margin-bottom: 40px;
        }
        .video-feed {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 40px;
          margin-top: 30px;
        }
        .video-card {
          width: 400px;
        }
        .video-card video {
          width: 100%;
          height: auto;
          display: block;
          border: none;
          background: #000;
        }
        .video-info {
          margin-top: 5px;
          font-size: 0.9em;
        }
      </style>
    </head>
    <body>
      {%% include 'sidebar' %%}
      <div class="main-content">
        <div class="welcome-message">
          Welcome to Desibeatz<br>
          <span style="font-size:0.6em;">Your personalized video</span>
        </div>
        <div class="video-feed">
          {% for vid in videos %}
            <div class="video-card">
              <video controls>
                <source src="{{ url_for('uploaded_file', filename=vid.filename) }}" type="video/mp4">
                Your browser does not support the video tag.
              </video>
              <div class="video-info">
                <strong>{{ vid.title }}</strong><br>
                Uploaded by: {{ vid.uploader.username }} on {{ vid.timestamp.strftime('%Y-%m-%d %H:%M') }}
              </div>
            </div>
          {% endfor %}
        </div>
      </div>
    </body>
    </html>
    """
    home_html = home_html.replace("{%% include 'sidebar' %%}", sidebar_template)
    return render_template_string(home_html, videos=videos)

# ----- EXPLORE Page -----
# Show all videos (including livestreams)
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
    explore_html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <title>Explore Videos</title>
      <style>
        .main-content {
          margin-left: 220px;
          padding: 20px;
        }
        .video-container {
          margin: 20px;
          display: inline-block;
          vertical-align: top;
          width: 320px;
        }
        .video-container video {
          width: 100%;
          background: #000;
          border: none;
        }
        .actions button {
          margin-right: 5px;
          padding: 5px 10px;
          background: #111;
          color: #fff;
          border: none;
          border-radius: 3px;
          cursor: pointer;
        }
        .actions button:hover {
          background: #444;
        }
        .comment-section {
          margin-top: 10px;
        }
        .comment {
          background: #333;
          padding: 5px;
          border-radius: 3px;
          margin-bottom: 5px;
          color: #fff;
        }
      </style>
    </head>
    <body>
      {%% include 'sidebar' %%}
      <div class="main-content">
        <h2>Explore Videos</h2>
        {% for vid in videos %}
          <div class="video-container">
            <video controls>
              <source src="{{ url_for('uploaded_file', filename=vid.filename) }}" type="video/mp4">
              Your browser does not support the video tag.
            </video>
            <p style="margin:5px 0;"><strong>{{ vid.title }}</strong></p>
            <p style="font-size:0.85em;">Uploaded by: {{ vid.uploader.username }} on {{ vid.timestamp.strftime('%Y-%m-%d %H:%M') }}</p>
            <div class="actions">
              <a href="{{ url_for('toggle_like', video_id=vid.id) }}"><button>Like ({{ vid.liked_by|length }})</button></a>
              <a href="{{ url_for('toggle_bookmark', video_id=vid.id) }}"><button>Bookmark ({{ vid.bookmarked_by|length }})</button></a>
              <button onclick="alert('Share Link: {{ url_for('uploaded_file', filename=vid.filename, _external=True) }}')">Share</button>
            </div>
            <div class="comment-section">
              <h4 style="margin:10px 0 5px;">Comments:</h4>
              {% for c in vid.comments %}
                <div class="comment">
                  <strong>{{ c.author.username }}</strong>: {{ c.content }}<br>
                  <small>{{ c.timestamp.strftime('%Y-%m-%d %H:%M') }}</small>
                </div>
              {% endfor %}
              {% if current_user.is_authenticated %}
                <form method="POST" action="{{ url_for('explore') }}">
                  <input type="hidden" name="video_id" value="{{ vid.id }}">
                  <input type="text" name="comment" placeholder="Add a comment..." required style="width:70%;">
                  <button type="submit" style="padding:5px 10px;">Comment</button>
                </form>
              {% endif %}
            </div>
          </div>
        {% endfor %}
        <br>
        <a href="{{ url_for('home') }}" style="color:#fff; text-decoration:none;">Back to Home</a>
      </div>
    </body>
    </html>
    """
    explore_html = explore_html.replace("{%% include 'sidebar' %%}", sidebar_template)
    return render_template_string(explore_html, videos=videos)

# ----- FOLLOWING (Placeholder) Page -----
@app.route('/following')
@login_required
def following():
    following_html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <title>Following</title>
      <style>
        .main-content {
          margin-left: 220px;
          padding: 20px;
          color: #fff;
        }
      </style>
    </head>
    <body>
      {%% include 'sidebar' %%}
      <div class="main-content">
        <h2>Your Following Feed</h2>
        <p>This is a placeholder for following content.</p>
        <a href="{{ url_for('home') }}" style="color:#fff; text-decoration:none;">Back to Home</a>
      </div>
    </body>
    </html>
    """
    following_html = following_html.replace("{%% include 'sidebar' %%}", sidebar_template)
    return render_template_string(following_html)

# ----- UPLOAD (Protected: requires login) -----
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
        # Convert filename to lower-case
        filename = secure_filename(file.filename).lower()
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        new_video = Video(title=title, filename=filename, user_id=current_user.id, is_livestream=False)
        db.session.add(new_video)
        db.session.commit()
        flash("Video uploaded successfully!", "success")
        return redirect(url_for('profile'))
    upload_html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <title>Upload Video</title>
      <style>
        .main-content {
          margin-left: 220px;
          padding: 20px;
          color: #fff;
        }
        .upload-form {
          max-width: 400px;
          margin: 50px auto;
          background: #222;
          padding: 20px;
          border-radius: 5px;
        }
        input, textarea {
          width: 100%;
          padding: 10px;
          margin: 10px 0;
          color: #000;
        }
        button {
          padding: 10px;
          width: 100%;
          background: #ff0066;
          color: #fff;
          border: none;
          border-radius: 5px;
          cursor: pointer;
        }
        button:hover {
          background: #ff3399;
        }
      </style>
    </head>
    <body>
      {%% include 'sidebar' %%}
      <div class="main-content">
        <div class="upload-form">
          <h2 style="margin-bottom:20px;">Upload Your Video</h2>
          <form method="POST" enctype="multipart/form-data">
            <input type="text" name="title" placeholder="Video Title" required>
            <input type="file" name="video" required>
            <button type="submit">Upload</button>
          </form>
        </div>
      </div>
    </body>
    </html>
    """
    upload_html = upload_html.replace("{%% include 'sidebar' %%}", sidebar_template)
    return render_template_string(upload_html)

# ----- LIVESTREAM (Exact TikTok-style copy with modifications) -----
# Now the livestream page also shows livestream videos on home, explore and profile pages.
@app.route('/livestream', methods=['GET', 'POST'])
@login_required
def livestream():
    if request.method == 'POST':
        title = request.form.get('title')
        if not title:
            flash("Please provide a livestream title.", "danger")
            return redirect(url_for('livestream'))
        dummy_filename = "livestream_" + secure_filename(title) + ".mp4"
        new_video = Video(title=title, filename=dummy_filename, user_id=current_user.id, is_livestream=True)
        db.session.add(new_video)
        db.session.commit()
        flash("Livestream recorded successfully (simulation)!", "success")
        return redirect(url_for('profile'))
    livestream_html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <title>Live</title>
      <style>
        body {
          margin: 0;
          padding: 0;
          font-family: 'Proxima Nova', Arial, sans-serif;
          background: #fff;
          color: #000;
        }
        .main-container {
          margin-left: 220px; /* leave space for sidebar */
          display: flex;
          min-height: 100vh;
        }
        /* Center column with livestream video and controls */
        .live-center {
          flex: 1;
          padding: 20px;
          background: #fff;
        }
        .live-center h2 {
          text-align: left;
          margin-top: 0;
        }
        .live-form {
          margin-bottom: 20px;
          text-align: left;
        }
        .live-form input[type="text"] {
          padding: 10px;
          margin-bottom: 10px;
          width: 100%;
          max-width: 300px;
        }
        .live-buttons {
          display: flex;
          gap: 10px;
          margin-top: 10px;
        }
        .live-buttons button {
          padding: 10px 20px;
          background: #fe2c55;
          color: #fff;
          border: none;
          border-radius: 4px;
          cursor: pointer;
          font-weight: bold;
        }
        .live-buttons button:hover {
          background: #ff527c;
        }
        .live-video-container {
          width: 100%;
          max-width: 700px;
          margin: 0 auto;
          background: #000;
          position: relative;
        }
        .live-video-container video {
          width: 100%;
          height: auto;
          background: #000;
        }
        /* Right column with chat box and header */
        .live-right {
          width: 320px;
          background: #f8f8f8;
          border-left: 1px solid #ccc;
          padding: 20px;
          display: flex;
          flex-direction: column;
          justify-content: space-between;
        }
        .login-box {
          background: #fff;
          border: 1px solid #ccc;
          border-radius: 6px;
          padding: 20px;
          text-align: center;
          margin-bottom: 20px;
        }
        .login-box h3 {
          margin: 0 0 10px 0;
          font-size: 1.1em;
        }
        .login-button {
          padding: 10px 20px;
          background: #fe2c55;
          color: #fff;
          border: none;
          border-radius: 4px;
          cursor: pointer;
          font-weight: bold;
        }
        .login-button:hover {
          background: #ff527c;
        }
        .chat-header {
          font-weight: bold;
          margin-bottom: 10px;
          text-align: left;
        }
        .comment-feed {
          flex: 1;
          overflow-y: auto;
          border: 1px solid #ccc;
          border-radius: 6px;
          padding: 10px;
          background: #fff;
        }
        .comment-item {
          margin-bottom: 10px;
          font-size: 0.9em;
          line-height: 1.4em;
        }
        .right-footer {
          margin-top: 20px;
          text-align: center;
          font-size: 0.85em;
          color: #999;
        }
      </style>
    </head>
    <body>
      {%% include 'sidebar' %%}
      <div class="main-container">
        <!-- Center Column -->
        <div class="live-center">
          <h2>Live</h2>
          <div class="live-form">
            <form id="liveForm" method="POST" style="margin-bottom:0;">
              <input type="text" name="title" placeholder="Livestream Title" required>
              <div class="live-buttons">
                <button type="button" id="startBtn">Start Livestream Preview</button>
                <!-- The same button will toggle to "Stop Livestream" when active -->
              </div>
            </form>
          </div>
          <div class="live-video-container">
            <video id="liveVideo" autoplay muted></video>
          </div>
        </div>
        <!-- Right Column -->
        <div class="live-right">
          <div>
            <div class="login-box">
              <h3>Log in for full experience</h3>
              <p>Log in to follow creators, like videos, and view comments.</p>
              <button class="login-button" onclick="location.href='{{ url_for('login_route') }}'">Log in</button>
            </div>
            <div class="chat-header">Chat</div>
            <div class="comment-feed" id="chatFeed">
              <div class="comment-item"><strong>User1:</strong> This is so cool!</div>
              <div class="comment-item"><strong>User2:</strong> Wow, amazing stream</div>
              <div class="comment-item"><strong>User3:</strong> Hello from Mumbai!</div>
            </div>
          </div>
          <div class="right-footer">
            © 2023 Desibeatz
          </div>
        </div>
      </div>
      <script>
        const startBtn = document.getElementById('startBtn');
        const liveVideo = document.getElementById('liveVideo');
        let streaming = false;
        let stream;
        startBtn.addEventListener('click', async () => {
          if (!streaming) {
            if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
              try {
                stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
                liveVideo.srcObject = stream;
                streaming = true;
                startBtn.innerText = "Stop Livestream";
              } catch (error) {
                alert("Error accessing camera/microphone: " + error);
              }
            } else {
              alert("getUserMedia not supported in this browser.");
            }
          } else {
            // Stop the stream
            stream.getTracks().forEach(track => track.stop());
            liveVideo.srcObject = null;
            streaming = false;
            startBtn.innerText = "Start Livestream Preview";
          }
        });
      </script>
    </body>
    </html>
    """
    livestream_html = livestream_html.replace("{%% include 'sidebar' %%}", sidebar_template)
    return render_template_string(livestream_html)

# ----- LIKE & BOOKMARK -----
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

# ----- PROFILE (Editable TikTok-Style for Current User) -----
@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        bio = request.form.get('bio')
        current_user.bio = bio or ""
        if 'profile_picture' in request.files:
            file = request.files['profile_picture']
            if file and file.filename != '':
                filename = secure_filename(file.filename).lower()
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

    user_videos = Video.query.filter_by(user_id=current_user.id).order_by(Video.timestamp.desc()).all()
    following_count = 72
    followers_count = "58.3M"
    likes_count = "631.9M"
    profile_html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <title>{{ current_user.username }}'s Profile</title>
      <style>
        body {
          background: #f8f8f8;
          margin: 0;
          padding: 0;
          font-family: 'Proxima Nova', Arial, sans-serif;
        }
        .main-content {
          margin-left: 220px;
          min-height: 100vh;
          background: #fff;
          color: #000;
          padding: 20px;
          position: relative;
        }
        .profile-header {
          display: flex;
          align-items: center;
          margin-bottom: 20px;
          border-bottom: 1px solid #ccc;
          padding-bottom: 20px;
        }
        .avatar {
          width: 100px;
          height: 100px;
          border-radius: 50%;
          object-fit: cover;
          background: #000;
          margin-right: 20px;
        }
        .profile-info {
          flex: 1;
        }
        .display-name {
          font-size: 1.4em;
          font-weight: bold;
          margin: 0;
        }
        .username-handle {
          color: #666;
          font-size: 0.9em;
          margin-top: 5px;
        }
        .stats-row {
          display: flex;
          gap: 25px;
          margin-top: 10px;
        }
        .stat-item strong {
          display: block;
          font-size: 1.2em;
          color: #000;
        }
        .follow-button {
          background: #fe2c55;
          color: #fff;
          border: none;
          padding: 8px 20px;
          border-radius: 4px;
          font-weight: bold;
          cursor: pointer;
          margin-top: 10px;
        }
        .follow-button:hover {
          background: #ff527c;
        }
        .bio-text {
          margin-top: 10px;
          color: #333;
          font-size: 0.9em;
        }
        .edit-profile-form {
          margin-top: 10px;
        }
        .edit-profile-form label {
          font-size: 0.85em;
          color: #333;
        }
        .edit-profile-form textarea,
        .edit-profile-form input[type='file'] {
          display: block;
          margin-top: 6px;
          margin-bottom: 10px;
          padding: 6px;
          width: 220px;
        }
        .videos-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
          gap: 10px;
          margin-top: 20px;
        }
        .video-card {
          background: #f9f9f9;
          border: 1px solid #eee;
          border-radius: 4px;
          overflow: hidden;
          text-align: center;
          padding: 10px;
        }
        .video-card video {
          width: 100%;
          border: none;
          background: #000;
          margin-bottom: 8px;
        }
        .video-title {
          font-weight: bold;
          color: #333;
          margin-bottom: 5px;
          font-size: 0.9em;
          overflow: hidden;
          white-space: nowrap;
          text-overflow: ellipsis;
        }
        .video-timestamp {
          font-size: 0.75em;
          color: #999;
        }
        .upload-button {
          position: absolute;
          right: 20px;
          top: 20px;
          background: #fe2c55;
          color: #fff;
          border: none;
          padding: 8px 20px;
          border-radius: 4px;
          font-weight: bold;
          cursor: pointer;
        }
        .upload-button:hover {
          background: #ff527c;
        }
      </style>
    </head>
    <body>
      {%% include 'sidebar' %%}
      <div class="main-content">
        <a href="{{ url_for('upload') }}" class="upload-button">Upload</a>
        <div class="profile-header">
          <img class="avatar" src="{{ url_for('uploaded_file', filename=current_user.profile_picture) }}" alt="Profile Picture">
          <div class="profile-info">
            <h2 class="display-name">{{ current_user.username }}</h2>
            <div class="username-handle">@{{ current_user.username }}</div>
            <div class="stats-row">
              <div class="stat-item">
                <strong>{{ following_count }}</strong> Following
              </div>
              <div class="stat-item">
                <strong>{{ followers_count }}</strong> Followers
              </div>
              <div class="stat-item">
                <strong>{{ likes_count }}</strong> Likes
              </div>
            </div>
            <button class="follow-button" disabled>Edit Profile</button>
            <div class="bio-text">{{ current_user.bio }}</div>
            <form method="POST" enctype="multipart/form-data" class="edit-profile-form">
              <label>Update Bio:</label>
              <textarea name="bio" rows="2">{{ current_user.bio }}</textarea>
              <label>Change Profile Picture:</label>
              <input type="file" name="profile_picture">
              <button type="submit" style="background:#fe2c55; color:#fff; border:none; border-radius:4px; padding:5px 15px; cursor:pointer;">Save</button>
            </form>
          </div>
        </div>
        <div class="videos-grid">
          {% for vid in user_videos %}
            <div class="video-card">
              <video controls>
                <source src="{{ url_for('uploaded_file', filename=vid.filename) }}" type="video/mp4">
                Your browser does not support the video tag.
              </video>
              <p class="video-title">{{ vid.title }}</p>
              <p class="video-timestamp">{{ vid.timestamp.strftime('%Y-%m-%d %H:%M') }}</p>
            </div>
          {% else %}
            <p style="grid-column: 1 / -1; text-align: center; color: #666;">No videos uploaded yet.</p>
          {% endfor %}
        </div>
      </div>
    </body>
    </html>
    """
    profile_html = profile_html.replace("{%% include 'sidebar' %%}", sidebar_template)
    return render_template_string(
        profile_html,
        following_count=following_count,
        followers_count=followers_count,
        likes_count=likes_count,
        user_videos=user_videos
    )

# ----- PUBLIC PROFILE (by username) -----
@app.route('/<username>')
def public_profile(username):
    reserved = {'for you', 'explore', 'following', 'upload', 'livestream', 'profile', 'login', 'signup', 'logout', 'uploads'}
    if username.lower() in reserved:
        abort(404)
    user = User.query.filter_by(username=username).first()
    if not user:
        abort(404)
    is_own_profile = (current_user.is_authenticated and current_user.id == user.id)
    public_profile_html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <title>{{ user.username }}'s Profile</title>
      <style>
        body {
          background: #f8f8f8;
          margin: 0;
          padding: 0;
          font-family: 'Proxima Nova', Arial, sans-serif;
        }
        .main-content {
          margin-left: 220px;
          min-height: 100vh;
          background: #fff;
          color: #000;
          padding: 20px;
        }
        .profile-header {
          display: flex;
          align-items: flex-start;
          border-bottom: 1px solid #ccc;
          padding-bottom: 20px;
          margin-bottom: 20px;
        }
        .avatar {
          width: 100px;
          height: 100px;
          border-radius: 50%;
          object-fit: cover;
          background: #000;
          margin-right: 20px;
        }
        .profile-info {
          flex: 1;
        }
        .display-name {
          font-size: 1.4em;
          margin: 0;
          font-weight: bold;
        }
        .username-handle {
          margin-top: 4px;
          color: #666;
          font-size: 0.9em;
        }
        .stats-row {
          display: flex;
          gap: 25px;
          margin-top: 10px;
        }
        .stat-item strong {
          display: block;
          font-size: 1.2em;
          color: #000;
        }
        .follow-button {
          background: #fe2c55;
          color: #fff;
          border: none;
          padding: 8px 20px;
          border-radius: 4px;
          font-weight: bold;
          cursor: pointer;
          margin-top: 10px;
        }
        .follow-button:hover {
          background: #ff527c;
        }
        .bio-text {
          margin-top: 10px;
          color: #333;
          font-size: 0.9em;
        }
        .videos-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
          gap: 10px;
          margin-top: 20px;
        }
        .video-card {
          background: #f9f9f9;
          border: 1px solid #eee;
          border-radius: 4px;
          overflow: hidden;
          text-align: center;
          padding: 10px;
        }
        .video-card video {
          width: 100%;
          border: none;
          background: #000;
          margin-bottom: 8px;
        }
        .video-title {
          font-weight: bold;
          color: #333;
          margin-bottom: 5px;
          font-size: 0.9em;
          overflow: hidden;
          white-space: nowrap;
          text-overflow: ellipsis;
        }
        .video-timestamp {
          font-size: 0.75em;
          color: #999;
        }
      </style>
    </head>
    <body>
      {%% include 'sidebar' %%}
      <div class="main-content">
        <div class="profile-header">
          <img class="avatar" src="{{ url_for('uploaded_file', filename=user.profile_picture) }}" alt="Avatar">
          <div class="profile-info">
            <h1 class="display-name">{{ user.username }}</h1>
            <div class="username-handle">@{{ user.username }}</div>
            <div class="stats-row">
              <div class="stat-item">
                <strong>72</strong> Following
              </div>
              <div class="stat-item">
                <strong>58.3M</strong> Followers
              </div>
              <div class="stat-item">
                <strong>631.9M</strong> Likes
              </div>
            </div>
            {% if not is_own_profile %}
              <button class="follow-button">Follow</button>
            {% else %}
              <button class="follow-button" disabled>Edit Profile</button>
            {% endif %}
            <div class="bio-text">{{ user.bio }}</div>
          </div>
        </div>
        <div class="videos-grid">
          {% for vid in user.videos %}
            <div class="video-card">
              <video controls>
                <source src="{{ url_for('uploaded_file', filename=vid.filename) }}" type="video/mp4">
                Your browser does not support the video tag.
              </video>
              <p class="video-title">{{ vid.title }}</p>
              <p class="video-timestamp">{{ vid.timestamp.strftime('%Y-%m-%d %H:%M') }}</p>
            </div>
          {% else %}
            <p style="grid-column: 1 / -1; text-align: center; color: #666;">No videos uploaded yet.</p>
          {% endfor %}
        </div>
      </div>
    </body>
    </html>
    """
    public_profile_html = public_profile_html.replace("{%% include 'sidebar' %%}", sidebar_template)
    return render_template_string(public_profile_html, user=user, is_own_profile=is_own_profile)

# ----- LOGIN -----
@app.route('/login', methods=['GET', 'POST'])
def login_route():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        if not email or not password:
            flash("All fields are required.", "danger")
            return redirect(url_for('login_route'))
        user = User.query.filter_by(email=email).first()
        if user and user.verify_password(password):
            login_user(user)
            flash("Login successful!", "success")
            return redirect(url_for('home'))
        else:
            flash("Invalid email or password.", "danger")
            return redirect(url_for('login_route'))
    login_form = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <title>Login</title>
      <style>
        .main-content {
          margin-left: 220px;
          padding: 20px;
          color: #fff;
        }
        .login-form {
          max-width: 400px;
          margin: 50px auto;
          background: #111;
          padding: 20px;
          border-radius: 5px;
        }
        input {
          width: 100%;
          padding: 10px;
          margin: 10px 0;
          color: #000;
        }
        button {
          padding: 10px;
          width: 100%;
          background: #ff0066;
          color: #fff;
          border: none;
          border-radius: 5px;
        }
        button:hover {
          background: #ff3399;
        }
      </style>
    </head>
    <body>
      {%% include 'sidebar' %%}
      <div class="main-content">
        <div class="login-form">
          <h2 style="margin-top:0;">Login</h2>
          <form method="POST">
            <input type="text" name="email" placeholder="Email" required>
            <input type="password" name="password" placeholder="Password" required>
            <button type="submit">Login</button>
          </form>
          <p>Don't have an account? <a href="{{ url_for('signup_route') }}" style="color:#ff0066;">Sign Up</a></p>
        </div>
      </div>
    </body>
    </html>
    """
    login_form = login_form.replace("{%% include 'sidebar' %%}", sidebar_template)
    return render_template_string(login_form)

# ----- SIGNUP -----
@app.route('/signup', methods=['GET', 'POST'])
def signup_route():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        if not username or not email or not password:
            flash("All fields are required.", "danger")
            return redirect(url_for('signup_route'))
        if User.query.filter_by(email=email).first():
            flash("Email already exists.", "warning")
            return redirect(url_for('signup_route'))
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
        .main-content {
          margin-left: 220px;
          padding: 20px;
          color: #fff;
        }
        .signup-form {
          max-width: 400px;
          margin: 50px auto;
          background: #111;
          padding: 20px;
          border-radius: 5px;
        }
        input {
          width: 100%;
          padding: 10px;
          margin: 10px 0;
          color: #000;
        }
        button {
          padding: 10px;
          width: 100%;
          background: #ff0066;
          color: #fff;
          border: none;
          border-radius: 5px;
        }
        button:hover {
          background: #ff3399;
        }
      </style>
    </head>
    <body>
      {%% include 'sidebar' %%}
      <div class="main-content">
        <div class="signup-form">
          <h2 style="margin-top:0;">Sign Up</h2>
          <form method="POST">
            <input type="text" name="username" placeholder="Username" required>
            <input type="text" name="email" placeholder="Email" required>
            <input type="password" name="password" placeholder="Password" required>
            <button type="submit">Sign Up</button>
          </form>
          <p>Already have an account? <a href="{{ url_for('login_route') }}" style="color:#ff0066;">Login</a></p>
        </div>
      </div>
    </body>
    </html>
    """
    signup_form = signup_form.replace("{%% include 'sidebar' %%}", sidebar_template)
    return render_template_string(signup_form)

# ----- LOGOUT -----
@app.route('/logout')
@login_required
def logout_route():
    logout_user()
    flash("Logged out successfully!", "info")
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)
