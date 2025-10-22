import os
import pandas as pd
from django.core.management.base import BaseCommand
from api.models import Track
from django.conf import settings

class Command(BaseCommand):
    def handle(self, *args, **options):
        csv_path = os.path.join(settings.BASE_DIR, 'api', 'data', 'datasets', 'spotify_dataset_1921_2020_600k_tracks.csv')

        if not os.path.exists(csv_path):
            self.stdout.write(self.style.ERROR(f"[INFO] Dataset não encontrado: {csv_path}"))
            return

        if Track.objects.exists():
            self.stdout.write(self.style.WARNING("[INFO] Dados já existem no banco. Nenhuma importação realizada."))
            return

        self.stdout.write(self.style.WARNING("[INFO] Iniciando importação otimizada..."))

        chunksize = 10000
        total_inserted = 0

        for i, chunk in enumerate(pd.read_csv(csv_path, chunksize=chunksize)):
            tracks = [
                Track(
                    id=row['id'],
                    name=row['name'],
                    popularity=row['popularity'],
                    duration_ms=row['duration_ms'],
                    explicit=bool(row['explicit']),
                    artists=row['artists'],
                    id_artists=row['id_artists'],
                    release_date=row['release_date'],
                    danceability=row['danceability'],
                    energy=row['energy'],
                    key=row['key'],
                    loudness=row['loudness'],
                    mode=row['mode'],
                    speechiness=row['speechiness'],
                    acousticness=row['acousticness'],
                    instrumentalness=row['instrumentalness'],
                    liveness=row['liveness'],
                    valence=row['valence'],
                    tempo=row['tempo'],
                    time_signature=row['time_signature']
                )
                for _, row in chunk.iterrows()
            ]

            Track.objects.bulk_create(tracks, batch_size=chunksize)
            total_inserted += len(tracks)
            self.stdout.write(f"[INFO] Lote {i+1} inserido ({total_inserted} registros no total)")

        self.stdout.write(self.style.SUCCESS(f"[INFO] Importação completa com {total_inserted} registros inseridos!"))