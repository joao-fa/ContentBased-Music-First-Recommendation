import os
import joblib

class PredictNewTrack:
    def __init__(self, dataframe, model_name):
        self.dataframe = dataframe
        self.model_name = f"{model_name}.pkl"
        self.model_path = '././api/data/trained_models/'
        self.model_location = f'{self.model_path}{self.model_name}'

    def predict_kmeans_cluster_for_each_row(self, model):
        row_clusters = []
        for i in range(len(self.dataframe)):
            row = self.dataframe.iloc[[i]]
            cluster = model.predict(row)[0]
            row_clusters.append(cluster)
        self.dataframe['cluster'] = row_clusters

    def execute(self):
        if os.path.exists(self.model_location):
            loaded_model = joblib.load(self.model_location)
            if self.model_name.startswith('kmeans'):
                self.predict_kmeans_cluster_for_each_row(loaded_model)
            else:
                raise Exception(f"Invalid model name {self.model_name}. Valid options should start with 'kmeans[...]'")
            return self.dataframe
        else:
            raise Exception(f"File {self.model_location} does not exist, please submit a valid file location!")
