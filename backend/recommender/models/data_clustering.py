import os
import joblib

from sklearn.cluster import KMeans

from app_logger import AppLogger

try:
    from sklearn.cluster import MiniBatchKMeans
except Exception:
    MiniBatchKMeans = None

class DataClustering:
    def __init__(self, dataframe, model_name, scaler=None, feature_columns=None):
        self.dataframe = dataframe
        self.model_name = model_name
        self.clusters = []
        self.base_model_path = '././api/data/trained_models/'
        self.logger = AppLogger(__name__)
        self.scaler = scaler
        self.feature_columns = feature_columns
        
    def start_kmeans_clustering(self, num_clusters, use_minibatch=False):
        os.environ['OMP_NUM_THREADS'] = '1' #Solução para (https://stackoverflow.com/questions/77727297/error-with-kmeans-could-not-find-the-number-of-physical-cores-in-windows-7)

        if use_minibatch:
            if MiniBatchKMeans is None:
                raise Exception("MiniBatchKMeans not available in this sklearn version.")
            kmeans = MiniBatchKMeans(
                n_clusters=num_clusters,
                random_state=42,
                n_init="auto",
                max_iter=300,
                batch_size=4096,
                reassignment_ratio=0.01,
            )
        else:
            kmeans = KMeans(
                n_clusters=num_clusters,
                random_state=42,
                n_init="auto",
                max_iter=300,
            )

        kmeans.fit(self.dataframe)
        self.clusters = kmeans.labels_

        try:
            self.logger.info(f"Clustering trained: inertia={kmeans.inertia_}, n_iter={kmeans.n_iter_}")
        except Exception:
            pass

        return kmeans

    def save_cluster_model(self, model, path):
        self.logger.info(f"Saving clustered model in '{path}'...")
        bundle = {
            "model": model,
            "scaler": self.scaler,
            "feature_columns": self.feature_columns,
        }
        joblib.dump(bundle, path)

    def execute(self, algorithm='kmeans', num_clusters=10, use_minibatch=False):
        if str(algorithm.replace('-', '')).lower() == 'kmeans':
            model = self.start_kmeans_clustering(num_clusters, use_minibatch=use_minibatch)
        else:
            raise Exception("The name of algorithm received is not one of valid algorithms. Aborting...")
        self.save_cluster_model(model, f"{self.base_model_path}{self.model_name}.pkl")
