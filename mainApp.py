from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QPushButton, QLabel, QSlider, QWidget
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import QTimer
from spotipy import Spotify
from spotipy.util import prompt_for_user_token
from lyricsgenius import Genius
import requests
from PIL import Image
from io import BytesIO
import os
import sys


class SpotifyApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Simplified Spotify App")
        self.setGeometry(200, 200, 800, 600)

        # Spotify and Genius API setup
        scope = 'user-read-playback-state user-modify-playback-state'
        self.sp = Spotify(auth=prompt_for_user_token(scope, client_id='c38a0cdcdb1b428f8851719d35783148',
                                                     client_secret='574fa31975c54682b6d67eb570ebf4bd',
                                                     redirect_uri='google.com'))
        self.genius = Genius("lc1tyYU4BpQVBkxep1RHyJdJRwOnHR1ui_cBc_PusWH1fhqeey194LrMmdSXKau5")
        self.current_track_id = None

        # UI Setup
        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        self.layout = QVBoxLayout(self.main_widget)

        self.track_label = QLabel("Track: N/A")
        self.artist_label = QLabel("Artist: N/A")
        self.album_art_label = QLabel()
        self.album_art_label.setFixedSize(200, 200)
        self.lyrics_label = QLabel("Lyrics will appear here.")
        self.lyrics_label.setWordWrap(True)

        self.play_button = QPushButton("Play/Pause")
        self.next_button = QPushButton("Next")
        self.prev_button = QPushButton("Previous")
        self.volume_slider = QSlider()
        self.volume_slider.setOrientation(QtCore.Qt.Orientation.Horizontal)

        self.layout.addWidget(self.track_label)
        self.layout.addWidget(self.artist_label)
        self.layout.addWidget(self.album_art_label)
        self.layout.addWidget(self.lyrics_label)
        self.layout.addWidget(self.play_button)
        self.layout.addWidget(self.next_button)
        self.layout.addWidget(self.prev_button)
        self.layout.addWidget(self.volume_slider)

        # Connect buttons
        self.play_button.clicked.connect(self.toggle_playback)
        self.next_button.clicked.connect(self.next_track)
        self.prev_button.clicked.connect(self.previous_track)
        self.volume_slider.valueChanged.connect(self.change_volume)

        # Timer to update track info
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_current_track)
        self.timer.start(2000)

    def update_current_track(self):
        current_playback = self.sp.currently_playing()
        if current_playback:
            track_id = current_playback['item']['id']
            if track_id != self.current_track_id:
                self.current_track_id = track_id
                self.track_label.setText(f"Track: {current_playback['item']['name']}")
                self.artist_label.setText(f"Artist: {current_playback['item']['artists'][0]['name']}")
                self.update_album_art(current_playback['item']['album']['images'][0]['url'])
                self.fetch_lyrics(current_playback['item']['name'], current_playback['item']['artists'][0]['name'])

    def update_album_art(self, url):
        response = requests.get(url)
        img = Image.open(BytesIO(response.content))
        img_path = "album_art.png"
        img.save(img_path)
        pixmap = QPixmap(img_path)
        self.album_art_label.setPixmap(pixmap.scaled(200, 200))

    def fetch_lyrics(self, track_name, artist_name):
        try:
            song = self.genius.search_song(title=track_name, artist=artist_name)
            self.lyrics_label.setText(song.lyrics if song else "Lyrics not found.")
        except:
            self.lyrics_label.setText("Lyrics not available.")

    def toggle_playback(self):
        current_playback = self.sp.currently_playing()
        if current_playback and current_playback['is_playing']:
            self.sp.pause_playback()
        else:
            self.sp.start_playback()

    def next_track(self):
        self.sp.next_track()

    def previous_track(self):
        self.sp.previous_track()

    def change_volume(self, value):
        self.sp.volume(value)


# Main Driver Code
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SpotifyApp()
    window.show()
    sys.exit(app.exec())
