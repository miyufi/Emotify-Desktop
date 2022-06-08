from flask import Flask, render_template, url_for, redirect, session, request, Response
from flask_socketio import SocketIO, emit
import cv2
from flask_cors import CORS
from engineio.payload import Payload
from engineio.async_drivers import threading
import os
from flask_session import Session
import spotipy
import uuid
from spotipy.oauth2 import SpotifyClientCredentials
import random
from flaskwebgui import FlaskUI

from object_detection import *

MODEL = cv2.dnn.readNet(
    'models/yolov4.weights',
    'models/yolov4.cfg'
)

VIDEO = VideoStreaming()
if VIDEO.detect == False:
    VIDEO.detect = not VIDEO.detect

os.environ["SPOTIPY_CLIENT_ID"] = "INSERT CLIENT ID HERE"
os.environ["SPOTIPY_CLIENT_SECRET"] = "INSERT CLIENT SECRET HERE"
os.environ["SPOTIPY_REDIRECT_URI"] = "INSERT REDIRECT URI HERE"

Payload.max_decode_packets = 2048

app = Flask(__name__)
app.config['SECRET_KEY'] = "secret"
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = './.flask_session/'
Session(app)
socketio = SocketIO(app, manage_session=False,
                    cors_allowed_origins='*', async_mode="threading")

caches_folder = './.spotify_caches/'
if not os.path.exists(caches_folder):
    os.makedirs(caches_folder)


def session_cache_path():
    return caches_folder + session.get('uuid')


def change(emotion):
    emotion_dict = {
        "anger": ["rock", "pop", "chill"],
        "disgust": ["0JQ5DAqbMKFQIL0AXnG5AK", "toplists", "mood", "pop"],
        "fear": ["0JQ5DAqbMKFCuoRTxhYWow", "country"],
        "happy": ["mood", "party", "0JQ5DAqbMKFQIL0AXnG5AK", "toplists"],
        "neutral": ["0JQ5DAqbMKFQIL0AXnG5AK", "toplists"],
        "sad": ["opm", "0JQ5DAqbMKFAUsdyVjCQuL", "in_the_car", "mood", "chill"],
        "surprised": ["rock", "0JQ5DAqbMKFQIL0AXnG5AK", "toplists"],
    }
    emotion = emotion_dict.get(emotion)
    random.shuffle(emotion)
    return emotion[0]


def readable(category):
    category_dict = {
        "0JQ5DAqbMKFCuoRTxhYWow": "sleep",
        "0JQ5DAqbMKFQIL0AXnG5AK": "trending",
        "0JQ5DAqbMKFAUsdyVjCQuL": "romance",
        "chill": "chill",
        "jazz": "jazz",
        "country": "country",
        "mood": "mood",
        "party": "party",
        "toplists": "toplists",
        "opm": "opm",
        "in_the_car": "in_the_car",
        "rock": "rock",
        "pop": "pop",
    }
    return category_dict.get(category)


@app.route('/')
def index():
    if not session.get('uuid'):
        session['uuid'] = str(uuid.uuid4())

    cache_handler = spotipy.cache_handler.CacheFileHandler(
        cache_path=session_cache_path())
    auth_manager = spotipy.oauth2.SpotifyOAuth(scope='user-read-currently-playing playlist-modify-private',
                                               cache_handler=cache_handler,
                                               show_dialog=True)

    if request.args.get("code"):
        auth_manager.get_access_token(request.args.get("code"))
        return redirect('/')

    if not auth_manager.validate_token(cache_handler.get_cached_token()):
        auth_url = auth_manager.get_authorize_url()
        return render_template('signin.html', auth_url=auth_url)
    spotify = spotipy.Spotify(
        auth_manager=auth_manager, requests_timeout=10, retries=10)

    if session.get('emotion') is None:
        try:
            artist = spotify.artist(artist_id="0gxyHStUsqpMadRV0Di1Qt")
        except:
            return render_template('noaccess.html')

        return redirect('/detect')

    emo = session.get('emotion')
    category = change(str(session.get('emotion')))
    try:
        results = spotify.category_playlists(
            category_id=category, country="PH", limit="30")
    except:
        return render_template('noaccess.html')

    playlists = []
    for idx, playlist in enumerate(results['playlists']['items']):
        playlists.append((playlist['name'], playlist['id']))
    random.shuffle(playlists)
    try:
        dp = spotify.me()["images"][0]["url"]
    except:
        dp = "https://www.oseyo.co.uk/wp-content/uploads/2020/05/empty-profile-picture-png-2-2.png"
    return render_template('home.html', emo=emo, category=readable(category), name=spotify.me()["display_name"], dp=dp, playlists=playlists)


@app.route('/detect', methods=['POST', 'GET'])
def detect():
    cache_handler = spotipy.cache_handler.CacheFileHandler(
        cache_path=session_cache_path())
    auth_manager = spotipy.oauth2.SpotifyOAuth(scope='user-read-currently-playing playlist-modify-private',
                                               cache_handler=cache_handler,
                                               show_dialog=True)
    if not auth_manager.validate_token(cache_handler.get_cached_token()):
        return redirect('/')
    spotify = spotipy.Spotify(
        auth_manager=auth_manager, requests_timeout=10, retries=10)

    try:
        artist = spotify.artist(artist_id="0gxyHStUsqpMadRV0Di1Qt")
    except:
        return redirect('/')

    return render_template('detect.html')


@app.route('/sign_out')
def sign_out():
    try:
        os.remove(session_cache_path())
        session.clear()
    except OSError as e:
        print("Error: %s - %s." % (e.filename, e.strerror))
    return redirect('/')


@app.route('/video_feed')
def video_feed():
    return Response(
        VIDEO.show(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )


@socketio.on("timedRedirect")
def timedRedirect():
    con = True
    while con:
        try:
            if VIDEO.lblret != "No label":
                session['emotion'] = VIDEO.lblret
                con = False
                emit('redirect', {'url': url_for('index')})
        except:
            pass


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_server_error(e):
    return render_template('404.html'), 500


if __name__ == '__main__':
    # socketio.run(app)
    FlaskUI(app, socketio=socketio, start_server="flask-socketio",
            maximized=True, port=5000).run()
