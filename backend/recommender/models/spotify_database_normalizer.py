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
            'key',
            'mode',
            'time_signature',
            'duration_ms'
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
        self.scaler = None

    def shuffle_dataframe(self):
        self.dataframe = self.dataframe.sample(frac=1, random_state=42).reset_index(drop=True) # 42 is arbitrary, but all runs with it will end with the same shuffle order

    def preserve_dataframe_percentage(self, dataset_retention):
        self.logger.info(f"Preserving {dataset_retention}% of base dataset...")
        dataframe_clipper = DataframeClipping(self.dataframe)
        self.dataframe = dataframe_clipper.preserve_dataframe_percentage(dataset_retention)

    def remove_unecessary_columns(self):
        self.logger.info(
            "Marking unecessary columns to be excluded from clustering (but preserved for persistence)..."
        )

    def return_df_numeric_columns(self, columns):
        return [
            item for item in columns
            if item not in self.non_numeric_columns and item not in self.unecessary_columns
        ]

    def create_reduced_dataframe(self):
        self.logger.info("Creating reduced dataframe...")
        dataframe_columns = self.dataframe.columns.tolist()
        numeric_columns = self.return_df_numeric_columns(dataframe_columns)
        self.reduced_dataframe = self.dataframe[numeric_columns]
        preserved_columns = self.non_numeric_columns + self.unecessary_columns
        self.metadata_dataframe = self.dataframe[preserved_columns].reset_index(drop=True)

    def apply_data_scaling(self):
        self.logger.info("Stracting dataframe features...")
        self.scaler = StandardScaler()
        dataframe_features = self.scaler.fit_transform(self.reduced_dataframe)
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
        normalized_columns = self.normalized_dataframe.columns.tolist()
        self.logger.info("Remaining columns after removal:\n"f"{normalized_columns}")
        return self.normalized_dataframe

