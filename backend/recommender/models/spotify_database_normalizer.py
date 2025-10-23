import pandas as pd

from sklearn.preprocessing import StandardScaler

from app_logger import AppLogger
from recommender.utils.dataframe_clipping import DataframeClipping

class SpotifyDatabaseNormalizer:
    def __init__(self, dataframe):
        self.logger = AppLogger(__name__)
        self.dataframe = dataframe
        self.reduced_dataframe = None
        self.normalized_dataframe = None
        self.unecessary_columns = [
            'popularity',
        ] 
        self.non_numeric_columns = [
            'id',
            'artists',
            'id_artists',
            'release_date',
            'name',
            'explicit',
        ]
        self.metadata_dataframe = None

    def shuffle_dataframe(self):
        self.dataframe = self.dataframe.sample(frac=1, random_state=42).reset_index(drop=True) # 42 is arbitrary, but all runs with it will end with the same shuffle order

    def preserve_dataframe_percentage(self, dataset_retention):
        self.logger.info(f"Preserving {dataset_retention}% of base dataset...")
        dataframe_clipper = DataframeClipping(self.dataframe)
        self.dataframe = dataframe_clipper.preserve_dataframe_percentage(dataset_retention)

    def remove_unecessary_columns(self):
        self.logger.info("Removing unecessary columns...")
        self.dataframe = self.dataframe.drop(columns=self.unecessary_columns)

    def return_df_numeric_columns(self, columns):
        return [item for item in columns if item not in self.non_numeric_columns]

    def create_reduced_dataframe(self):
        self.logger.info("Creating reduced dataframe...")
        dataframe_columns = self.dataframe.columns.tolist()
        numeric_columns = self.return_df_numeric_columns(dataframe_columns)
        self.reduced_dataframe = self.dataframe[numeric_columns]
        self.metadata_dataframe = self.dataframe[self.non_numeric_columns].reset_index(drop=True)

    def apply_data_scaling(self):
        self.logger.info("Stracting dataframe features...")
        scaler = StandardScaler()
        dataframe_features = scaler.fit_transform(self.reduced_dataframe)
        self.normalized_dataframe = pd.DataFrame(dataframe_features)
        self.normalized_dataframe.columns = self.reduced_dataframe.columns

    def execute(self, apply_scale=True, dataset_retention=100):
        self.shuffle_dataframe()
        self.preserve_dataframe_percentage(dataset_retention)
        self.remove_unecessary_columns()
        self.create_reduced_dataframe()
        if apply_scale:
            self.apply_data_scaling()
        else:
            self.normalized_dataframe = self.reduced_dataframe
        return self.normalized_dataframe

# Columns relation:
# COLUM                                  EXAMPLE    USED FOR CLUSTERING
# 1. Unnamed: 0                                0            X - Sounds like index column, but we already have track_id
# 2. track_id             5SuOikwiRyPMVoIQDJUgSV            X
# 3. artists                         Gen Hoshino            X
# 4. album_name                           Comedy            X
# 5. track_name                           Comedy            X
# 6. popularity                               73            X - Not returned in Spotify feature search
# 7. duration_ms                          230666
# 8. explicit                              False            X
# 9. danceability                          0.676
# 10. energy                               0.461
# 11. key                                      1
# 12. loudness                            -6.746
# 13. mode                                     0
# 14. speechiness                          0.143
# 15. acousticness                        0.0322
# 16. instrumentalness                  0.000001
# 17. liveness                             0.358
# 18. valence                              0.715
# 19. tempo                               87.917
# 20. time_signature                           4
# 21. track_genre                       acoustic            X

