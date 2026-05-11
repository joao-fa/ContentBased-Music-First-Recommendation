import os
from pathlib import Path

import pandas as pd
from django.conf import settings

from app_logger import AppLogger


class ReadCSVDataset:
    DEFAULT_DATASETS_DIR = Path("api") / "data" / "datasets" / "final_datasets"

    def __init__(self, dataset_name=None, datasets_dir=None):
        self.dataset_name = dataset_name
        self.datasets_dir = datasets_dir
        self.logger = AppLogger(__name__)

    @classmethod
    def resolve_datasets_dir(cls, datasets_dir=None):
        if datasets_dir:
            path = Path(datasets_dir)

            if not path.is_absolute():
                path = Path(settings.BASE_DIR) / path

            return path

        return Path(settings.BASE_DIR) / cls.DEFAULT_DATASETS_DIR

    @classmethod
    def list_available_datasets(cls, datasets_dir=None):
        directory = cls.resolve_datasets_dir(datasets_dir)

        if not directory.exists():
            return []

        return sorted(
            [
                path.name
                for path in directory.iterdir()
                if path.is_file() and path.suffix.lower() == ".csv"
            ]
        )

    def resolve_csv_path(self):
        if not self.dataset_name:
            raise ValueError("Nenhum dataset informado para leitura.")

        dataset_path = Path(self.dataset_name)

        if dataset_path.is_absolute():
            return dataset_path

        if dataset_path.exists():
            return dataset_path.resolve()

        datasets_dir = self.resolve_datasets_dir(self.datasets_dir)
        candidate_path = datasets_dir / self.dataset_name

        if candidate_path.exists():
            return candidate_path

        raise FileNotFoundError(
            f"Dataset não encontrado. Caminho esperado: {candidate_path}"
        )

    def execute(self):
        try:
            csv_path = self.resolve_csv_path()

            self.logger.info(f"Lendo o dataset... (localizado em: {csv_path})")

            dataframe = pd.read_csv(csv_path)
            return dataframe

        except Exception as e:
            self.logger.info(f"Erro ao carregar CSV: {e}")
            return None