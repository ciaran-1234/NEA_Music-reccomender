from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QLabel, QPushButton, QSlider, QWidget)
from PyQt6 import QtCore, QtGui
from PyQt6.QtGui import QPixmap
import sys, os, time, requests
from datetime import datetime
from io import BytesIO
from PIL import Image
import imageio
import spotipy.util as util
from spotipy import Spotify
from lyricsgenius import Genius

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setupUI()
        self.setupSpotify()
        self.setupTimers()

    def setupUI(self):
        self.setWindowTitle("Spotify Music App")
        self.setWindowIcon(QtGui.QIcon('assets/spotify.png'))

        self.mainWidget = QWidget()
        self.layout = QVBoxLayout(self.mainWidget)

        self.welcomeLabel = QLabel("Welcome")
        self.albumArtLabel = QLabel()
        self.songNameLabel = QLabel("Song Name")
        self.artistNameLabel = QLabel("Artist Name")
        self.volumeSlider = QSlider(QtCore.Qt.Orientation.Horizontal)

        for widget in [self.welcomeLabel, self.albumArtLabel, self.songNameLabel, self.artistNameLabel, self.volumeSlider]:
            self.layout.addWidget(widget)

        self.setCentralWidget(self.mainWidget)
        self.volumeSlider.valueChanged.connect(self.setVolume)

    def setupSpotify(self):
        scope = ('user-read-private user-library-read user-read-playback-state '
                 'user-modify-playback-state user-top-read playlist-modify-private playlist-modify-public')
        token = util.prompt_for_user_token(
            scope=scope, client_id='c38a0cdcdb1b428f8851719d35783148', client_secret='574fa31975c54682b6d67eb570ebf4bd', redirect_uri='http/host:5000'
        )
        self.spotify = Spotify(auth=token)
        self.genius = Genius("ACCESS_TOKEN")
        self.updateWelcomeMessage()
        self.updateTrackInfo()

    def setupTimers(self):
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.updateTrackInfo)
        self.timer.start(2000)

    def updateWelcomeMessage(self):
        hour = datetime.now().hour
        period = ["morning", "afternoon", "evening", "night"][hour // 6 % 4]
        self.welcomeLabel.setText(f"Good {period}, check out the top songs of the day")

    def updateTrackInfo(self):
        track = self.spotify.currently_playing()
        if track:
            item = track.get("item", {})
            self.songNameLabel.setText(item.get("name", "Unknown Song"))
            self.artistNameLabel.setText(item.get("album", {}).get("artists", [{}])[0].get("name", "Unknown Artist"))

            album_url = item.get("album", {}).get("images", [{}])[0].get("url")
            if album_url:
                self.loadAlbumArt(album_url, item.get("name", "Unknown"))

    def loadAlbumArt(self, url, track_name):
        sanitized_name = ''.join(filter(str.isalnum, track_name))
        image_path = f'images/{sanitized_name}.png'
        if not os.path.exists(image_path):
            response = requests.get(url)
            img = Image.open(BytesIO(response.content))
            imageio.imwrite(image_path, img)
        self.albumArtLabel.setPixmap(QPixmap(image_path).scaled(200, 200))

    def setVolume(self, value):
        self.spotify.volume(value)

if __name__ == "__main__":
    app = QApplication(sys.argv)

    splash = QtGui.QSplashScreen(QPixmap('assets/spotify.png').scaled(200, 200))
    splash.show()
    time.sleep(1)
    splash.close()

    window = MainWindow()
    window.show()
    sys.exit(app.exec())
