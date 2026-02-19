import os
import joblib
import pandas as pd

class PredictNewTrack:
    def __init__(self, dataframe, model_name, already_scaled=True):
        self.dataframe = dataframe
        self.already_scaled = already_scaled
        self.model_name = f"{model_name}.pkl"
        self.model_path = '././api/data/trained_models/'
        self.model_location = f'{self.model_path}{self.model_name}'

    def predict_kmeans_cluster_for_each_row(self, model, scaler=None, feature_columns=None):
        X = self.dataframe
        if feature_columns is not None:
            X = X[feature_columns].copy()
        if scaler is not None and not self.already_scaled:
            X = X.copy()
            X.loc[:, :] = scaler.transform(X.values)
        clusters = model.predict(X)
        self.dataframe = self.dataframe.copy()
        self.dataframe['cluster'] = clusters

    def execute(self):
        if os.path.exists(self.model_location):
            loaded = joblib.load(self.model_location)

            if isinstance(loaded, dict) and "model" in loaded:
                model = loaded["model"]
                scaler = loaded.get("scaler")
                feature_columns = loaded.get("feature_columns")
            else:
                model = loaded
                scaler = None
                feature_columns = None
            if self.model_name.startswith('ALG_kmeans'):
                self.predict_kmeans_cluster_for_each_row(
                    model,
                    scaler=scaler,
                    feature_columns=feature_columns
                )
            else:
                raise Exception(
                    f"Invalid model name {self.model_name}. "
                    f"Valid options should start with 'ALG_kmeans[...]'"
                )
            return self.dataframe
        else:
            raise Exception(
                f"File {self.model_location} does not exist"
            )
