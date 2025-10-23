import os
import pandas as pd
from django.core.management.base import BaseCommand
from django.conf import settings
from dotenv import load_dotenv

from recommender.utils.read_dataset import ReadCSVDataset
from recommender.models.data_clustering import DataClustering
from recommender.models.predict_new_track import PredictNewTrack
from recommender.models.spotify_database_normalizer import SpotifyDatabaseNormalizer

from api.models import Track

class Command(BaseCommand):
    def handle(self, *args, **options):
        load_dotenv()
        dataset_name = os.getenv("DATASET_NAME")
        dataset_retention = int(os.getenv("RETENTION"))
        algorithm = os.getenv("ALGORITHM")
        num_clusters = int(os.getenv("NUM_CLUSTERS"))
        apply_scale = os.getenv("APPLY_SCALE") == 'True'
        model_name = f"{os.getenv("ALGORITHM")}_retention_{os.getenv("RETENTION")}_ds_name_{os.getenv("DATASET_NAME").replace(".csv","")}"
        model_path = os.path.join(
            settings.BASE_DIR, "api", "data", "trained_models", f"{model_name}.pkl"
        )

        self.stdout.write(self.style.SUCCESS("[INFO] Iniciando carregamento e predição..."))

        dataset_reader = ReadCSVDataset(dataset_name)
        dataframe = dataset_reader.execute()

        normalizer = SpotifyDatabaseNormalizer(dataframe)
        normalized_dataframe = normalizer.execute(
            apply_scale, dataset_retention
        )

        if os.path.exists(model_path):
            self.stdout.write(self.style.SUCCESS(f"[INFO] Modelo existente encontrado em '{model_path}', pulando clusterização..."))
        else:
            self.stdout.write(self.style.SUCCESS(f"[INFO] Modelo não encontrado, iniciando clusterização..."))
            data_clustering = DataClustering(normalized_dataframe, model_name)
            data_clustering.execute(algorithm, num_clusters)

        predictor = PredictNewTrack(normalized_dataframe, model_name)
        predicted_dataframe = predictor.execute()
        predicted_dataframe.reset_index(drop=True, inplace=True)
        normalizer.metadata_dataframe.reset_index(drop=True, inplace=True)

        final_dataframe = pd.concat(
            [normalizer.metadata_dataframe, predicted_dataframe],
            axis=1
        )

        if Track.objects.exists():
            self.stdout.write(self.style.WARNING("[INFO] Tabela 'Track' já populada — limpando antes da nova inserção..."))
            Track.objects.all().delete()
            self.stdout.write(self.style.SUCCESS("[INFO] Tabela 'Track' limpa com sucesso."))

        self.stdout.write(self.style.SUCCESS("[INFO] Salvando faixas no banco com cluster predito..."))
        bulk_tracks = []
        for _, row in final_dataframe.iterrows():
            bulk_tracks.append(Track(
                id=row["id"],
                name=row["name"],
                popularity=row.get("popularity"),
                duration_ms=row.get("duration_ms"),
                explicit=row.get("explicit", False),
                artists=row.get("artists", ""),
                id_artists=row.get("id_artists", ""),
                release_date=row.get("release_date", ""),
                danceability=row.get("danceability"),
                energy=row.get("energy"),
                key=row.get("key"),
                loudness=row.get("loudness"),
                mode=row.get("mode"),
                speechiness=row.get("speechiness"),
                acousticness=row.get("acousticness"),
                instrumentalness=row.get("instrumentalness"),
                liveness=row.get("liveness"),
                valence=row.get("valence"),
                tempo=row.get("tempo"),
                time_signature=row.get("time_signature"),
            ))

        Track.objects.bulk_create(bulk_tracks, ignore_conflicts=True)
        self.stdout.write(self.style.SUCCESS(f"[INFO] {len(bulk_tracks)} faixas salvas com sucesso!"))