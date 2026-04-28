import gc
import os
import time
from io import StringIO
from pathlib import Path

import pandas as pd
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection, transaction
from dotenv import load_dotenv

from app_logger import AppLogger
from recommender.models.data_clustering import DataClustering
from recommender.models.predict_new_track import PredictNewTrack
from recommender.models.spotify_database_normalizer import SpotifyDatabaseNormalizer

from api.models import Track, ClusterMetadata

TRACK_COLUMNS = [
    "id", "name", "popularity", "duration_ms", "explicit", "artists",
    "id_artists", "release_date", "danceability", "energy", "key",
    "loudness", "mode", "speechiness", "acousticness",
    "instrumentalness", "liveness", "valence", "tempo", "time_signature",
]

READ_DTYPES = {
    "id": "string",
    "name": "string",
    "popularity": "Int64",
    "duration_ms": "Int64",
    "explicit": "string",
    "artists": "string",
    "id_artists": "string",
    "release_date": "string",
    "danceability": "float64",
    "energy": "float64",
    "key": "Int64",
    "loudness": "float64",
    "mode": "Int64",
    "speechiness": "float64",
    "acousticness": "float64",
    "instrumentalness": "float64",
    "liveness": "float64",
    "valence": "float64",
    "tempo": "float64",
    "time_signature": "Int64",
}

STRING_COLUMNS = ["id", "name", "explicit", "artists", "id_artists", "release_date"]


def sanitize_scalar(value, default=None):
    if pd.isna(value):
        return default
    return value


class Command(BaseCommand):
    def handle(self, *args, **options):
        start_time = time.time()
        cluster_time = None
        metadata_time = None
        logger = AppLogger(__name__)

        logger.info("[INFO] Iniciando sistema...")

        load_dotenv()
        dataset_name = os.getenv("DATASET_NAME", "").strip()
        dataset_retention = int(os.getenv("RETENTION"))
        algorithm = os.getenv("ALGORITHM")
        num_clusters = int(os.getenv("NUM_CLUSTERS"))
        apply_scale = os.getenv("APPLY_SCALE") == "True"

        dataset_label = dataset_name if dataset_name else "final_datasets"

        if algorithm == "kmeans":
            model_name = (
                f"ALG_{algorithm}_RET_{dataset_retention}_"
                f"CLU_{num_clusters}_DS_{dataset_label.replace('.csv', '')}"
            )
        else:
            model_name = (
                f"ALG_{algorithm}_RET_{dataset_retention}_"
                f"DS_{dataset_label.replace('.csv', '')}"
            )

        model_path = os.path.join(
            settings.BASE_DIR, "api", "data", "trained_models", f"{model_name}.pkl"
        )

        logger.info("[INFO] Iniciando carregamento e normalização do dataset...")

        dataset_dir = Path(settings.BASE_DIR) / "api" / "data" / "datasets" / "final_datasets"
        if dataset_name:
            dataset_names = [name.strip() for name in dataset_name.split(",") if name.strip()]
            dataset_paths = [dataset_dir / name for name in dataset_names]
        else:
            dataset_paths = sorted(dataset_dir.glob("*.csv"))

        if not dataset_paths:
            logger.error(f"[ERRO] Nenhum dataset encontrado em '{dataset_dir}'.")
            return

        missing_paths = [str(path) for path in dataset_paths if not path.exists()]
        if missing_paths:
            logger.error(f"[ERRO] Os seguintes datasets não foram encontrados: {missing_paths}")
            return

        dataframes = []
        for dataset_path in dataset_paths:
            logger.info(f"[INFO] Lendo dataset: {dataset_path.name}")
            dataframe_part = pd.read_csv(
                dataset_path,
                usecols=lambda col: col in TRACK_COLUMNS,
                dtype=READ_DTYPES,
                keep_default_na=True,
                low_memory=True,
            )
            for string_col in STRING_COLUMNS:
                if string_col in dataframe_part.columns:
                    dataframe_part[string_col] = dataframe_part[string_col].fillna("")
            dataframes.append(dataframe_part)

        dataframe = pd.concat(dataframes, ignore_index=True, copy=False)
        del dataframes
        gc.collect()

        if dataframe is None or dataframe.empty:
            logger.error("[ERRO] Os datasets finais não puderam ser carregados.")
            return

        normalizer = SpotifyDatabaseNormalizer(dataframe)
        normalized_dataframe = normalizer.execute(apply_scale, dataset_retention)

        feature_columns = list(normalizer.reduced_dataframe.columns)
        del dataframe
        gc.collect()

        if os.path.exists(model_path):
            logger.info(
                f"[INFO] Modelo existente encontrado em '{model_path}', pulando clusterização..."
            )
        else:
            logger.info("[INFO] Modelo não encontrado, iniciando clusterização...")
            cluster_start = time.time()

            data_clustering = DataClustering(
                normalized_dataframe,
                model_name,
                scaler=getattr(normalizer, "scaler", None),
                feature_columns=list(normalizer.reduced_dataframe.columns),
            )
            use_minibatch = os.getenv("USE_MINIBATCH", "False") == "True"
            data_clustering.execute(
                algorithm,
                num_clusters,
                use_minibatch=use_minibatch,
            )

            cluster_end = time.time()
            cluster_time = (cluster_end - cluster_start) / 60.0
            logger.info(f"[INFO] Clusterização concluída em {cluster_time:.2f} minutos.")

        logger.info("[INFO] Iniciando predição de clusters para todas as faixas...")

        predictor = PredictNewTrack(
            normalized_dataframe,
            model_name,
            already_scaled=True,
        )
        predicted_dataframe = predictor.execute()
        predicted_dataframe.reset_index(drop=True, inplace=True)
        normalizer.metadata_dataframe.reset_index(drop=True, inplace=True)
        del normalized_dataframe
        gc.collect()

        final_dataframe = pd.concat(
            [normalizer.metadata_dataframe, predicted_dataframe],
            axis=1,
        )

        expected = ["popularity", "duration_ms", "key", "mode", "time_signature"]
        missing = [c for c in expected if c not in final_dataframe.columns]
        if missing:
            logger.warning(
                f"[WARN] Colunas originais ausentes no final_dataframe: {missing}"
            )

        for string_col in STRING_COLUMNS:
            if string_col in final_dataframe.columns:
                final_dataframe[string_col] = final_dataframe[string_col].fillna("")

        del predicted_dataframe
        del normalizer.metadata_dataframe
        gc.collect()

        logger.info("[INFO] Atualizando tabela 'Track'...")

        existing_tables = connection.introspection.table_names()
        if Track._meta.db_table not in existing_tables:
            logger.error(
                f"[ERRO] A tabela '{Track._meta.db_table}' não existe. Rode as migrações antes do bootstrap."
            )
            return

        total_rows = len(final_dataframe)
        logger.info(f"[INFO] Total de registros finais: {total_rows}")

        chunk_size = 5000
        total_created = 0
        total_updated = 0

        for start in range(0, total_rows, chunk_size):
            end = min(start + chunk_size, total_rows)

            chunk_df = final_dataframe.iloc[start:end].copy()
            incoming_ids = chunk_df["id"].tolist()

            logger.info(
                f"[INFO] Processando chunk {start}:{end} com {len(incoming_ids)} IDs..."
            )

            existing_tracks = Track.objects.in_bulk(incoming_ids)
            logger.info(
                f"[INFO] Tracks já existentes neste chunk: {len(existing_tracks)}"
            )

            to_create = []
            to_update = []
            chunk_records = chunk_df.to_dict("records")

            for row in chunk_records:
                track_id = sanitize_scalar(row.get("id"), "")
                if not track_id:
                    continue

                predicted_cluster = sanitize_scalar(row.get("cluster"))
                existing = existing_tracks.get(track_id)

                if existing is None:
                    to_create.append(
                        Track(
                            id=track_id,
                            name=sanitize_scalar(row.get("name"), ""),
                            popularity=sanitize_scalar(row.get("popularity"), 0),
                            duration_ms=sanitize_scalar(row.get("duration_ms"), 0),
                            explicit=str(sanitize_scalar(row.get("explicit"), "False")).lower() == "true",
                            artists=sanitize_scalar(row.get("artists"), ""),
                            id_artists=sanitize_scalar(row.get("id_artists"), ""),
                            release_date=sanitize_scalar(row.get("release_date"), ""),
                            danceability=sanitize_scalar(row.get("danceability")),
                            energy=sanitize_scalar(row.get("energy")),
                            key=sanitize_scalar(row.get("key"), 0),
                            loudness=sanitize_scalar(row.get("loudness")),
                            mode=sanitize_scalar(row.get("mode"), 0),
                            speechiness=sanitize_scalar(row.get("speechiness")),
                            acousticness=sanitize_scalar(row.get("acousticness")),
                            instrumentalness=sanitize_scalar(row.get("instrumentalness")),
                            liveness=sanitize_scalar(row.get("liveness")),
                            valence=sanitize_scalar(row.get("valence")),
                            tempo=sanitize_scalar(row.get("tempo")),
                            time_signature=sanitize_scalar(row.get("time_signature"), 4),
                            cluster=predicted_cluster,
                        )
                    )
                else:
                    if existing.cluster != predicted_cluster:
                        existing.cluster = predicted_cluster
                        to_update.append(existing)

            if to_create:
                Track.objects.bulk_create(to_create, batch_size=1000)
                total_created += len(to_create)

            if to_update:
                Track.objects.bulk_update(to_update, ["cluster"], batch_size=1000)
                total_updated += len(to_update)

            del chunk_df
            del incoming_ids
            del existing_tracks
            del to_create
            del to_update
            del chunk_records
            gc.collect()

        transaction.set_autocommit(True)

        logger.info(
            f"[INFO] Upsert concluído: {total_created} criadas, {total_updated} clusters atualizados."
        )

        del final_dataframe
        del normalizer
        gc.collect()

        logger.info("[INFO] Calculando medianas e desvios por cluster...")
        metadata_insert_start = time.time()

        if connection.vendor == "postgresql":
            with connection.cursor() as cursor:
                cursor.execute('SET LOCAL statement_timeout = 600000;')
                cursor.execute('SET LOCAL lock_timeout = 15000;')
                cursor.execute(
                    f'TRUNCATE TABLE "{ClusterMetadata._meta.db_table}" RESTART IDENTITY CASCADE;'
                )

            select_parts = []
            for col in feature_columns:
                col_quoted = f'"{col}"'
                select_parts.append(
                    f'percentile_cont(0.5) WITHIN GROUP (ORDER BY {col_quoted}) AS median_{col}'
                )
                select_parts.append(
                    f'stddev_samp({col_quoted}) AS std_{col}'
                )

            select_stats = ",\n               ".join(select_parts)
            track_table = Track._meta.db_table

            sql = f'''
                SELECT "cluster",
                    {select_stats}
                FROM "{track_table}"
                GROUP BY "cluster"
                ORDER BY "cluster";
            '''

            with connection.cursor() as cursor:
                cursor.execute('SET LOCAL statement_timeout = 600000;')
                cursor.execute(sql)
                colnames = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()

            out_rows = []
            for row in rows:
                cluster_value = int(row[0])
                row_map = dict(zip(colnames, row))

                for feature in feature_columns:
                    median_val = row_map.get(f"median_{feature}")
                    std_val = row_map.get(f"std_{feature}")

                    median_val = None if median_val is None else float(median_val)
                    std_val = None if std_val is None else float(std_val)

                    out_rows.append((cluster_value, feature, median_val, std_val))

            table = ClusterMetadata._meta.db_table
            csv_buf = StringIO()

            for cval, feat, med, std in out_rows:
                med = "" if med is None else med
                std = "" if std is None else std
                csv_buf.write(f"{cval},{feat},{med},{std}\n")

            csv_buf.seek(0)

            with transaction.atomic():
                with connection.cursor() as cur:
                    cur.execute('SET LOCAL synchronous_commit = off;')
                    cur.execute('SET LOCAL statement_timeout = 600000;')
                    cur.execute('SET LOCAL lock_timeout = 15000;')
                    copy_sql = (
                        f'COPY "{table}" ("cluster","feature","median","std_deviation") '
                        f'FROM STDIN WITH (FORMAT CSV)'
                    )
                    cur.copy_expert(copy_sql, csv_buf)

        else:
            ClusterMetadata.objects.all().delete()

            metadata_objects = []

            for cluster_value in (
                Track.objects
                .exclude(cluster__isnull=True)
                .values_list("cluster", flat=True)
                .distinct()
                .order_by("cluster")
            ):
                cluster_qs = Track.objects.filter(cluster=cluster_value)

                for feature in feature_columns:
                    values = list(
                        cluster_qs
                        .exclude(**{f"{feature}__isnull": True})
                        .values_list(feature, flat=True)
                    )

                    if not values:
                        median_val = None
                        std_val = None
                    else:
                        series = pd.Series(values)
                        median_val = float(series.median())
                        std_val = float(series.std()) if len(series) > 1 else None

                    metadata_objects.append(
                        ClusterMetadata(
                            cluster=cluster_value,
                            feature=feature,
                            median=median_val,
                            std_deviation=std_val,
                        )
                    )

            ClusterMetadata.objects.bulk_create(metadata_objects, batch_size=1000)
        metadata_insert_end = time.time()
        metadata_time = (metadata_insert_end - metadata_insert_start) / 60.0

        end_time = time.time()
        total_minutes = (end_time - start_time) / 60.0

        logger.info("========== RESUMO DE TEMPO ==========")
        logger.info(f"[INFO] Tempo total do pipeline: {total_minutes:.2f} minutos.")
        if cluster_time is not None:
            logger.info(f"[INFO] Tempo de clusterização: {cluster_time:.2f} minutos.")
        else:
            logger.info("[INFO] Tempo de clusterização: pulado (modelo já existia).")
        logger.info(f"[INFO] Tempo de cálculo de metadados: {metadata_time:.2f} minutos.")
        logger.info("=====================================")
