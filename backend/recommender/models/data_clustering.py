import os
import joblib

from sklearn.cluster import KMeans

from app_logger import AppLogger

class DataClustering:
    def __init__(self, dataframe, model_name):
        self.dataframe = dataframe
        self.model_name = model_name
        self.clusters = []
        self.base_model_path = '././api/data/trained_models/'
        self.logger = AppLogger(__name__)

    def start_kmeans_clustering(self, num_clusters):
        os.environ['OMP_NUM_THREADS'] = '1' #Solução para (https://stackoverflow.com/questions/77727297/error-with-kmeans-could-not-find-the-number-of-physical-cores-in-windows-7)
        kmeans = KMeans(n_clusters=num_clusters, random_state=42)
        kmeans.fit(self.dataframe)
        self.clusters = kmeans.labels_
        return kmeans

    def save_cluster_model(self, model, path):
        self.logger.info(f"Saving clustered model in '{path}'...")
        joblib.dump(model, path)

    def execute(self, algorithm='kmeans', num_clusters=10):
        if str(algorithm.replace('-', '')).lower() == 'kmeans':
            model = self.start_kmeans_clustering(num_clusters)
        else:
            raise Exception(f"The name of algorithm received is not one of valid algorithms. Aborting...")
        self.save_cluster_model(model, f"{self.base_model_path}{self.model_name}.pkl")
