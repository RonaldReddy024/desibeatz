import os
import re
from datetime import datetime
from flask import (
    Flask, render_template_string, request, redirect,
    url_for, flash, send_from_directory, abort, Response
)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin, login_user, logout_user,
    login_required, current_user
)
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
    username = db.Column(db.String(20), nullable=False)
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

# ----- Helper for video MIME -----
def _get_mime_type(filename):
    ext = filename.rsplit('.', 1)[-1].lower()
    return {
        'mp4': 'video/mp4',
        'mov': 'video/quicktime',
        'avi': 'video/x-msvideo'
    }.get(ext, 'application/octet-stream')

# ====== UPDATED: Serve uploaded files (with HTTP Range support) ======
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.isfile(file_path):
        abort(404)

    range_header = request.headers.get('Range', None)
    if not range_header:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    size = os.path.getsize(file_path)
    m = re.match(r'bytes=(\d+)-(\d*)', range_header)
    if not m:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    byte1 = int(m.group(1))
    byte2 = int(m.group(2)) if m.group(2) else size - 1
    length = byte2 - byte1 + 1

    with open(file_path, 'rb') as f:
        f.seek(byte1)
        data = f.read(length)

    resp = Response(
        data,
        206,
        mimetype=_get_mime_type(filename),
        direct_passthrough=True
    )
    resp.headers.add('Content-Range', f'bytes {byte1}-{byte2}/{size}')
    resp.headers.add('Accept-Ranges', 'bytes')
    resp.headers.add('Content-Length', str(length))
    return resp

# ----- SIDEBAR (Displayed on all pages) -----
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
    margin: 0; padding: 0;
    background-color: #000;
    color: #fff;
  }
  .sidebar {
    position: fixed;
    top: 0; left: 0;
    width: 220px; height: 100vh;
    background-color: #000;
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

# ----- HOME (For You) Page -----
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
          background: transparent;
          color: #fff;
          padding: 20px;
          border-radius: 10px;
          margin: 40px 0;
          width: 60%;
          font-size: 2em;
          font-weight: 600;
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
              {% set ext = vid.filename.rsplit('.', 1)[1].lower() %}
              {% if ext == 'mp4' %}
                {% set mime = 'video/mp4' %}
              {% elif ext == 'mov' %}
                {% set mime = 'video/quicktime' %}
              {% elif ext == 'avi' %}
                {% set mime = 'video/x-msvideo' %}
              {% else %}
                {% set mime = 'video/mp4' %}
              {% endif %}
              <video controls>
                <source src="{{ url_for('uploaded_file', filename=vid.filename) }}" type="{{ mime }}">
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
            {% set ext = vid.filename.rsplit('.', 1)[1].lower() %}
            {% if ext == 'mp4' %}
              {% set mime = 'video/mp4' %}
            {% elif ext == 'mov' %}
              {% set mime = 'video/quicktime' %}
            {% elif ext == 'avi' %}
              {% set mime = 'video/x-msvideo' %}
            {% else %}
              {% set mime = 'video/mp4' %}
            {% endif %}
            <video controls>
              <source src="{{ url_for('uploaded_file', filename=vid.filename) }}" type="{{ mime }}">
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

# ... All remaining routes (following, livestream, toggle_like, toggle_bookmark, profile, public_profile, login_route, signup_route, logout_route) remain **exactly** as in your original file ...

if __name__ == '__main__':
    app.run(debug=True)
