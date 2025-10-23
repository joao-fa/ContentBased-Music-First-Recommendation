import requests
import base64

from app_logger import AppLogger

class SpotifySearcher:
    def __init__(self, submitted_track):
        self.logger = AppLogger(__name__)
        self.submitted_track = submitted_track
        self.search_url = "https://api.spotify.com/v1/search"
        self.get_token_url = "https://accounts.spotify.com/api/token"
        self.get_track_features_url = "https://api.spotify.com/v1/audio-features/"
        self.client_id = "82bd422aa5f44b9d830543cdf6a2ea55"
        self.client_secret = "0e9c9414e73c4a67a0f4be057e22f165"
        self.client_credentials = f"{self.client_id}:{self.client_secret}"

    def get_token(self):
        self.logger.info("Getting Spotify APP Token...")
        base64_auth = base64.b64encode(self.client_credentials.encode()).decode()
        auth_options = {
            'headers': {
                'Authorization': 'Basic ' + base64_auth
            },
            'data': {
                'grant_type': 'client_credentials'
            }
        }
        try:
            search_response = requests.post(self.get_token_url, headers=auth_options['headers'], data=auth_options['data'])
            if search_response.status_code == 200:
                response_data = search_response.json()
                token = {}
                token['access_token'] = response_data['access_token']
                token['token_type'] = response_data['token_type']
                token['token_duration'] = response_data['expires_in']
                self.logger.info(token)
                return token
            raise Exception(f"ERROR | status_code: {search_response.status_code}, response_text: {search_response.text}")
        except Exception as e:
            raise Exception(f"Found the following error searching for token: {e}")

    def build_token_config(self):
        search_headers = {
            "Content-Type": "application/x-www-form-urlencoded",
        }
        app_credentials = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        return search_headers, app_credentials

    def search_track(self, token):
        self.logger.info(f"Searching for {self.submitted_track} on Spotify...")
        search_headers, search_params = self.build_search_config(token)
        try:
            search_response = requests.get(self.search_url, headers=search_headers, params=search_params)
            if search_response.status_code == 200:
                request_result = search_response.json()
                if "tracks" in request_result and "items" in request_result["tracks"] and request_result["tracks"]["items"]:
                    track = request_result["tracks"]["items"][0]
                    track_returned = {
                        "track": track,
                        "track_name": track["name"],
                        "track_artists": track["artists"][0]["name"],
                        "track_url": track["external_urls"]["spotify"],
                        "track_id": track["id"]
                    }
                    return track_returned
                else:
                    self.logger.info("No track matches the submitted string.")
                    return None
            elif search_response.status_code == 401:
                raise Exception("Invalid or expired token. Please authenticate again.")
            else:
                raise Exception(f"ERROR | status_code: {search_response.status_code}, response_text: {search_response.text}")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Network error while searching for '{self.submitted_track}': {e}") from e
        except KeyError as e:
            raise Exception(f"Unexpected response structure from Spotify API: {e}") from e

    def build_search_config(self, token, limit=1):
        search_headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        search_params = {
            "q": self.submitted_track,
            "type": "track",
            "limit": 1
        }
        return search_headers, search_params

    def get_track_features(self, token, track_id):
        self.logger.info(f"Fetching audio features for track ID {track_id} on Spotify...")
        url = f"{self.get_track_features_url}{track_id}"
        headers = self.build_search_features_config(token)
        
        try:
            response = requests.get(url, headers=headers)
            self.logger.info(f"Response status: {response.status_code}")
            self.logger.info(f"Response text: {response.text}")
            
            if response.status_code == 200:
                features = response.json()
                if features:
                    track_features = {
                        "track_id": features.get("id"),
                        "duration_ms": features.get("duration_ms"),
                        "danceability": features.get("danceability"),
                        "energy": features.get("energy"),
                        "key": features.get("key"),
                        "loudness": features.get("loudness"),
                        "mode": features.get("mode"),
                        "speechiness": features.get("speechiness"),
                        "acousticness": features.get("acousticness"),
                        "instrumentalness": features.get("instrumentalness"),
                        "liveness": features.get("liveness"),
                        "valence": features.get("valence"),
                        "tempo": features.get("tempo"),
                        "time_signature": features.get("time_signature")
                    }
                    return track_features
                else:
                    raise Exception(f"Invalid response structure: {response.json()}")
            elif response.status_code == 401:
                raise Exception("Invalid or expired token. Please authenticate again.")
            elif response.status_code == 403:
                raise Exception("Forbidden access. Ensure the token has proper permissions.")
            else:
                raise Exception(f"ERROR | status_code: {response.status_code}, response_text: {response.text}")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Network error while fetching audio features: {e}") from e

    def build_search_features_config(self, token):
        if not token or not isinstance(token, str):
            raise ValueError("A valid token must be provided.")
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

    def execute_track_finder(self, spotify_token):
        return self.search_track(spotify_token)
    
    def execute_track_features_finder(self, spotify_token, track_id):
        return self.get_track_features(spotify_token, track_id)