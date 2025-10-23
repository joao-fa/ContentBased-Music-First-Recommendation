import os
import pandas as pd
from django.conf import settings
from app_logger import AppLogger

class ReadCSVDataset:
    def __init__(self, dataset_name):
        self.dataset_name = dataset_name
        self.logger = AppLogger(__name__)

    def execute(self):
        try:
            if os.path.isabs(self.dataset_name):
                csv_path = self.dataset_name
            else:
                csv_path = os.path.join(settings.BASE_DIR, "api", "data", "datasets", self.dataset_name)

            self.logger.info(f"Lendo o dataset... (localizado em: {csv_path})")

            dataframe = pd.read_csv(csv_path)
            return dataframe

        except Exception as e:
            self.logger.info(f"Erro ao carregar CSV: {e}")
            return None