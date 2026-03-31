import os
import time
import pandas as pd
from io import StringIO

from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import connection, transaction
from dotenv import load_dotenv

from app_logger import AppLogger
from recommender.utils.read_dataset import ReadCSVDataset
from recommender.models.data_clustering import DataClustering
from recommender.models.predict_new_track import PredictNewTrack
from recommender.models.spotify_database_normalizer import SpotifyDatabaseNormalizer

from api.models import Track, ClusterMetadata


class Command(BaseCommand):
    def handle(self, *args, **options):
        # ============================
        # INÍCIO DO PROCESSO
        # ============================
        start_time = time.time()
        cluster_time = None
        metadata_time = None
        logger = AppLogger(__name__)

        logger.info("[INFO] Iniciando sistema...")

        load_dotenv()
        dataset_name = os.getenv("DATASET_NAME")
        dataset_retention = int(os.getenv("RETENTION"))
        algorithm = os.getenv("ALGORITHM")
        num_clusters = int(os.getenv("NUM_CLUSTERS"))
        apply_scale = os.getenv("APPLY_SCALE") == "True"

        if algorithm == "kmeans":
            model_name = (
                f"ALG_{algorithm}_RET_{dataset_retention}_"
                f"CLU_{num_clusters}_DS_{dataset_name.replace('.csv', '')}"
            )
        else:
            model_name = (
                f"ALG_{algorithm}_RET_{dataset_retention}_"
                f"DS_{dataset_name.replace('.csv', '')}"
            )

        model_path = os.path.join(
            settings.BASE_DIR, "api", "data", "trained_models", f"{model_name}.pkl"
        )

        logger.info("[INFO] Iniciando carregamento e normalização do dataset...")

        # ======================================================
        # 1) Lê dataset bruto
        # ======================================================
        dataset_reader = ReadCSVDataset(dataset_name)
        dataframe = dataset_reader.execute()

        if dataframe is None or dataframe.empty:
            logger.error(f"[ERRO] Dataset '{dataset_name}' não pôde ser carregado.")
            return

        # ======================================================
        # 2) Normalizador decide quais colunas serão consideradas
        # ======================================================
        normalizer = SpotifyDatabaseNormalizer(dataframe)
        normalized_dataframe = normalizer.execute(apply_scale, dataset_retention)

        # ======================================================
        # 3) Clusterização (se necessário)
        # ======================================================
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
            data_clustering.execute(algorithm, num_clusters, use_minibatch=use_minibatch)

            cluster_end = time.time()
            cluster_time = (cluster_end - cluster_start) / 60.0

            logger.info(f"[INFO] Clusterização concluída em {cluster_time:.2f} minutos.")

        # ======================================================
        # 4) Predição de cluster para cada faixa (vetorizada)
        # ======================================================
        logger.info("[INFO] Iniciando predição de clusters para todas as faixas...")

        predictor = PredictNewTrack(
            normalized_dataframe,
            model_name,
            already_scaled=True
        )
        predicted_dataframe = predictor.execute()
        predicted_dataframe.reset_index(drop=True, inplace=True)
        normalizer.metadata_dataframe.reset_index(drop=True, inplace=True)

        # ======================================================
        # 5) DataFrame final para a tabela Track
        # ======================================================
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

        # ======================================================
        # 6) UPSERT da tabela Track
        # ======================================================
        logger.info("[INFO] Atualizando tabela 'Track'...")

        existing_tables = connection.introspection.table_names()
        if Track._meta.db_table not in existing_tables:
            logger.error(
                f"[ERRO] A tabela '{Track._meta.db_table}' não existe. Rode as migrações antes do bootstrap."
            )
            return

        records = final_dataframe.to_dict("records")
        incoming_ids = [row["id"] for row in records]

        logger.info(f"[INFO] Total de registros finais: {len(records)}")
        logger.info(f"[INFO] Total de IDs recebidos: {len(incoming_ids)}")

        existing_tracks = Track.objects.in_bulk(incoming_ids)

        logger.info(f"[INFO] Tracks já existentes no banco: {len(existing_tracks)}")

        to_create = []
        to_update = []

        logger.info("[INFO] Separando registros entre criação e atualização...")

        for row in records:
            track_id = row["id"]
            predicted_cluster = row.get("cluster")

            existing = existing_tracks.get(track_id)

            if existing is None:
                to_create.append(
                    Track(
                        id=row["id"],
                        name=row["name"],
                        popularity=row.get("popularity", 0),
                        duration_ms=row.get("duration_ms", 0),
                        explicit=row.get("explicit", False),
                        artists=row.get("artists", ""),
                        id_artists=row.get("id_artists", ""),
                        release_date=row.get("release_date", ""),
                        danceability=row.get("danceability"),
                        energy=row.get("energy"),
                        key=row.get("key", 0),
                        loudness=row.get("loudness"),
                        mode=row.get("mode", 0),
                        speechiness=row.get("speechiness"),
                        acousticness=row.get("acousticness"),
                        instrumentalness=row.get("instrumentalness"),
                        liveness=row.get("liveness"),
                        valence=row.get("valence"),
                        tempo=row.get("tempo"),
                        time_signature=row.get("time_signature", 4),
                        cluster=predicted_cluster,
                    )
                )
            else:
                if existing.cluster != predicted_cluster:
                    existing.cluster = predicted_cluster
                    to_update.append(existing)

        logger.info(
            f"[INFO] Preparação concluída: {len(to_create)} para criar, {len(to_update)} para atualizar."
        )

        if to_create:
            logger.info(f"[INFO] Executando bulk_create de {len(to_create)} tracks...")
            Track.objects.bulk_create(to_create, batch_size=1000)

        if to_update:
            logger.info(f"[INFO] Executando bulk_update de {len(to_update)} tracks...")
            Track.objects.bulk_update(to_update, ["cluster"], batch_size=1000)

        transaction.set_autocommit(True)

        logger.info(
            f"[INFO] Upsert concluído: {len(to_create)} criadas, {len(to_update)} clusters atualizados."
        )

        # ======================================================
        # 7) CALCULAR MEDIANAS E DESVIO PADRÃO POR CLUSTER
        # ======================================================
        logger.info("[INFO] Calculando medianas e desvios por cluster...")

        metadata_insert_start = time.time()

        if connection.vendor == "postgresql":
            with connection.cursor() as cursor:
                cursor.execute('SET LOCAL statement_timeout = 600000;')
                cursor.execute('SET LOCAL lock_timeout = 15000;')
                cursor.execute(
                    f'TRUNCATE TABLE "{ClusterMetadata._meta.db_table}" RESTART IDENTITY CASCADE;'
                )
            logger.info("[INFO] Tabela 'ClusterMetadata' truncada com sucesso (Postgres).")
        else:
            ClusterMetadata.objects.all().delete()
            logger.info("[INFO] Tabela 'ClusterMetadata' limpa com sucesso (delete).")

        feature_columns = list(normalizer.reduced_dataframe.columns)

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

                median_val = '' if median_val is None else float(median_val)
                std_val = '' if std_val is None else float(std_val)

                out_rows.append((cluster_value, feature, median_val, std_val))

        table = ClusterMetadata._meta.db_table

        csv_buf = StringIO()
        for cval, feat, med, std in out_rows:
            csv_buf.write(f'{cval},{feat},{med},{std}\n')
        csv_buf.seek(0)

        with transaction.atomic():
            with connection.cursor() as cur:
                cur.execute('SET LOCAL synchronous_commit = off;')
                cur.execute('SET LOCAL statement_timeout = 600000;')
                cur.execute('SET LOCAL lock_timeout = 15000;')

                copy_sql = f'COPY "{table}" ("cluster","feature","median","std_deviation") FROM STDIN WITH (FORMAT CSV)'
                cur.copy_expert(copy_sql, csv_buf)

        metadata_insert_end = time.time()
        metadata_time = (metadata_insert_end - metadata_insert_start) / 60.0

        logger.info(f"[INFO] Metadados calculados e inseridos em {metadata_time:.2f} minutos.")

        # ============================
        # 8) TEMPO TOTAL DO PROCESSO
        # ============================
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