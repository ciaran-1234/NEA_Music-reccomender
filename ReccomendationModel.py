import pandas as pd
import numpy as np
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import MinMaxScaler
import spotipy
import spotipy.util as util
import itertools

class RecommendationModel():
    def __init__(self, data_file='data.csv', genre_file='data_w_genres.csv', client_id='c38a0cdcdb1b428f8851719d35783148', client_secret='574fa31975c54682b6d67eb570ebf4bd', redirect_uri='http/host:5000'):
        # Load Data
        self.spotify_df = pd.read_csv(data_file)
        self.data_w_genre = pd.read_csv(genre_file)
        
        # Preprocess Data
        self._process_artists_and_genres()
        self._feature_engineering()
        
        # Spotify Authentication
        self.sp = self._authenticate_spotify(client_id, client_secret, redirect_uri)

    def _process_artists_and_genres(self):
        """Clean and merge artist and genre data."""
        self.data_w_genre['genres_upd'] = self.data_w_genre['genres'].apply(lambda x: re.findall(r"'([^']*)'", x))
        self.spotify_df['artists_upd'] = self.spotify_df['artists'].apply(lambda x: re.findall(r'"(.*?)"', x) or re.findall(r"'([^']*)'", x))
        self.spotify_df['artists_song'] = self.spotify_df.apply(lambda row: row['artists_upd'][0] + row['name'], axis=1)
        self.spotify_df.sort_values(['artists_song', 'release_date'], ascending=False, inplace=True)
        self.spotify_df.drop_duplicates('artists_song', inplace=True)

        # Merge with genre data
        artists_exploded = self.spotify_df[['artists_upd', 'id']].explode('artists_upd')
        artists_exploded_enriched = artists_exploded.merge(self.data_w_genre, how='left', left_on='artists_upd', right_on='artists')
        artists_genres = artists_exploded_enriched.groupby('id')['genres_upd'].apply(list).reset_index()
        artists_genres['consolidates_genre_lists'] = artists_genres['genres_upd'].apply(lambda x: list(set(itertools.chain.from_iterable(x))))
        self.spotify_df = self.spotify_df.merge(artists_genres[['id', 'consolidates_genre_lists']], on='id', how='left')
        
    def _feature_engineering(self):
        """Create features like one-hot encoding, TF-IDF, and scaling."""
        self.spotify_df['year'] = self.spotify_df['release_date'].apply(lambda x: x.split('-')[0])
        self.spotify_df['popularity_red'] = self.spotify_df['popularity'] // 5
        self.spotify_df['genre'] = self.spotify_df['consolidates_genre_lists'].apply(lambda d: d if isinstance(d, list) else [])
        
        # TF-IDF for genres
        tfidf = TfidfVectorizer()
        tfidf_matrix = tfidf.fit_transform(self.spotify_df['consolidates_genre_lists'].apply(lambda x: " ".join(x)))
        genre_df = pd.DataFrame(tfidf_matrix.toarray(), columns=['genre_' + f for f in tfidf.get_feature_names()])
        
        # One-hot encoding
        self.spotify_df['year_ohe'] = pd.get_dummies(self.spotify_df['year'])
        self.spotify_df['popularity_ohe'] = pd.get_dummies(self.spotify_df['popularity_red'])

        # Scaling numerical columns
        float_cols = self.spotify_df.select_dtypes(include=[np.float64]).columns
        scaler = MinMaxScaler()
        self.spotify_df[float_cols] = scaler.fit_transform(self.spotify_df[float_cols])

    def _authenticate_spotify(self, client_id, client_secret, redirect_uri):
        """Authenticate and return Spotify API client."""
        scope = 'user-library-read user-top-read playlist-modify-private'
        token = util.prompt_for_user_token(scope=scope, client_id=client_id, client_secret=client_secret, redirect_uri=redirect_uri)
        return spotipy.Spotify(auth=token)

    def create_playlist_vector(self, playlist_id):
        """Generate a weighted feature vector for a user's playlist."""
        playlist = self._get_playlist_tracks(playlist_id)
        playlist_feature_set = self.spotify_df[self.spotify_df['id'].isin(playlist['id'])]
        
        # Apply weight based on recency of song in playlist
        most_recent_date = playlist_feature_set['date_added'].max()
        playlist_feature_set['weight'] = playlist_feature_set['date_added'].apply(lambda x: (1.09 ** ((most_recent_date - x).days // 30)))
        
        return playlist_feature_set.drop(columns=['id', 'date_added']).mul(playlist_feature_set['weight'], axis=0).sum(axis=0)

    def _get_playlist_tracks(self, playlist_id):
        """Fetch the track list from a Spotify playlist."""
        playlist_data = self.sp.playlist_tracks(playlist_id)
        playlist = pd.DataFrame([{
            'artist': item['track']['artists'][0]['name'],
            'name': item['track']['name'],
            'id': item['track']['id'],
            'date_added': item['added_at']
        } for item in playlist_data['items']])
        playlist['date_added'] = pd.to_datetime(playlist['date_added'])
        return playlist

    def recommend(self, playlist_id, top_n=10):
        """Generate top N song recommendations based on the playlist."""
        playlist_vector = self.create_playlist_vector(playlist_id)
        all_songs = self.spotify_df.drop(columns=['id', 'date_added'])
        all_songs['similarity'] = cosine_similarity(all_songs, playlist_vector.values.reshape(1, -1))[:, 0]
        
        recommended_songs = self.spotify_df.loc[all_songs['similarity'].nlargest(top_n).index]
        recommended_songs['url'] = recommended_songs['id'].apply(lambda x: self.sp.track(x)['album']['images'][1]['url'])
        
        return recommended_songs[['name', 'artist', 'url']]

