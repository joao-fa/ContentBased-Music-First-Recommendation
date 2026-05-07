import argparse
import base64
import csv
import json
import os
import time
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connections
from django.utils import timezone


EXPORT_DEFINITIONS = {
    "recommendation_evaluations": {
        "queryset": lambda using: apps.get_model("api", "RecommendationEvaluation")
        .objects.using(using)
        .order_by("id"),
        "fields": [
            ("id", "id"),
            ("batch_id", "batch_id"),
            ("session_uuid", "batch__session_uuid"),
            ("user_id", "user_id"),
            ("username", "user__username"),
            ("base_track_id", "base_track_id"),
            ("base_track_name", "batch__base_track_name"),
            ("base_track_artists", "batch__base_track_artists"),
            ("recommended_track_id", "recommended_track_id"),
            ("recommended_track_name", "recommended_track_name"),
            ("recommended_track_artists", "recommended_track_artists"),
            ("order_in_list", "order_in_list"),
            ("list_type", "list_type"),
            ("rating", "rating"),
            ("language_influenced_rating", "language_influenced_rating"),
            ("base_metric", "base_metric"),
            ("recommendation_cluster", "recommendation_cluster"),
            ("base_track_cluster_at_recommendation", "base_track_cluster_at_recommendation"),
            (
                "recommended_track_cluster_at_recommendation",
                "recommended_track_cluster_at_recommendation",
            ),
            ("base_track_feature_value", "base_track_feature_value"),
            ("recommended_track_feature_value", "recommended_track_feature_value"),
            ("was_preview_opened", "was_preview_opened"),
            ("spotify_opened", "spotify_opened"),
            ("strategy_version", "strategy_version"),
            ("dataset_version", "dataset_version"),
            ("cluster_algorithm", "cluster_algorithm"),
            ("client_started_at", "batch__client_started_at"),
            ("client_submitted_at", "batch__client_submitted_at"),
            ("duration_seconds", "batch__duration_seconds"),
            ("experiment_config", "batch__experiment_config"),
            ("created_at", "created_at"),
        ],
    },
    "recommendation_batches": {
        "queryset": lambda using: apps.get_model("api", "RecommendationBatch")
        .objects.using(using)
        .order_by("id"),
        "fields": [
            ("id", "id"),
            ("session_uuid", "session_uuid"),
            ("user_id", "user_id"),
            ("username", "user__username"),
            ("base_track_id", "base_track_id"),
            ("base_track_name", "base_track_name"),
            ("base_track_artists", "base_track_artists"),
            ("recommendation_cluster", "recommendation_cluster"),
            ("used_feature", "used_feature"),
            ("strategy_version", "strategy_version"),
            ("dataset_version", "dataset_version"),
            ("cluster_algorithm", "cluster_algorithm"),
            ("client_started_at", "client_started_at"),
            ("client_submitted_at", "client_submitted_at"),
            ("duration_seconds", "duration_seconds"),
            ("experiment_config", "experiment_config"),
            ("created_at", "created_at"),
        ],
    },
}

MODEL_EXPORTS = {
    "tracks": ("api", "Track"),
    "cluster_metadata": ("api", "ClusterMetadata"),
}

ALL_DATASETS = sorted([*EXPORT_DEFINITIONS.keys(), *MODEL_EXPORTS.keys()])
RECURRING_DATASETS = ["recommendation_evaluations", "recommendation_batches"]
STARTUP_DATASETS = ["tracks", "cluster_metadata"]
GOOGLE_DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive"]
FOLDER_MIME_TYPE = "application/vnd.google-apps.folder"
DEFAULT_RETENTION_BY_DATASET = {
    "recommendation_evaluations": 24,
    "recommendation_batches": 24,
    "tracks": 3,
    "cluster_metadata": 3,
}
TRUE_VALUES = {"1", "true", "yes", "y"}


def env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in TRUE_VALUES


def env_int(name, default):
    value = os.getenv(name)
    if value in {None, ""}:
        return default
    return int(value)


def env_csv(name, default):
    value = os.getenv(name)
    if not value:
        return list(default)
    return [item.strip() for item in value.split(",") if item.strip()]


def normalize_csv_value(value):
    if value is None:
        return ""
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return value


def sanitize_drive_query_value(value):
    return value.replace("\\", "\\\\").replace("'", "\\'")


class Command(BaseCommand):
    help = (
        "Exporta snapshots do banco para CSV e, opcionalmente, envia os arquivos "
        "para subpastas no Google Drive com política de retenção."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--profile",
            choices=["recurring", "startup", "all"],
            default=os.getenv("EXPORT_DATABASE_PROFILE", "recurring"),
            help=(
                "Perfil de exportação. 'recurring' é indicado para cron horário; "
                "'startup' exporta músicas e metadados de clusters na inicialização."
            ),
        )
        parser.add_argument(
            "--dataset",
            action="append",
            choices=ALL_DATASETS,
            help=(
                "Dataset específico a exportar. Pode ser informado mais de uma vez; "
                "quando usado, sobrescreve o --profile."
            ),
        )
        parser.add_argument(
            "--filename",
            default=os.getenv("EXPORT_DATABASE_FILENAME"),
            help=(
                "Nome do arquivo CSV. Só deve ser usado ao exportar um único dataset; "
                "por padrão, usa dataset + timestamp UTC."
            ),
        )
        parser.add_argument(
            "--output-dir",
            default=os.getenv(
                "EXPORT_DATABASE_OUTPUT_DIR",
                str(settings.BASE_DIR / "exports"),
            ),
            help="Diretório local temporário onde os CSVs serão gerados.",
        )
        parser.add_argument(
            "--chunk-size",
            type=int,
            default=env_int("EXPORT_DATABASE_CHUNK_SIZE", 1000),
            help="Quantidade de linhas lidas por lote do banco.",
        )
        parser.add_argument(
            "--database",
            default=os.getenv("EXPORT_DATABASE_DB_ALIAS", "default"),
            help=(
                "Alias de banco usado para leitura. Pode apontar para uma réplica "
                "configurada no Django para reduzir impacto no banco primário."
            ),
        )
        parser.add_argument(
            "--sleep-between-chunks",
            type=float,
            default=float(os.getenv("EXPORT_DATABASE_SLEEP_BETWEEN_CHUNKS", "0.05")),
            help="Pausa em segundos entre lotes para aliviar aplicação e banco.",
        )
        parser.add_argument(
            "--skip-upload",
            action="store_true",
            default=env_bool("EXPORT_DATABASE_SKIP_UPLOAD", False),
            help="Gera apenas os CSVs locais, sem enviar para o Google Drive.",
        )
        parser.add_argument(
            "--keep-local",
            action=argparse.BooleanOptionalAction,
            default=env_bool("EXPORT_DATABASE_KEEP_LOCAL", False),
            help=(
                "Mantém os arquivos CSV locais depois do upload. "
                "Use --keep-local para manter ou --no-keep-local para remover."
            ),
        )
        parser.add_argument(
            "--retention",
            type=int,
            help="Quantidade máxima de arquivos mantidos no Drive para todos os datasets.",
        )
        parser.add_argument(
            "--skip-lock",
            action="store_true",
            default=env_bool("EXPORT_DATABASE_SKIP_LOCK", False),
            help=(
                "Não usa advisory lock para evitar execuções concorrentes. "
                "Não recomendado para cron."
            ),
        )
        parser.add_argument(
            "--skip-retention",
            action="store_true",
            default=env_bool("EXPORT_DATABASE_SKIP_RETENTION", False),
            help="Não remove arquivos antigos após o upload.",
        )

    def handle(self, *args, **options):
        self.validate_options(options)

        if not options["skip_lock"] and not self.acquire_export_lock(options["database"]):
            self.stdout.write(
                self.style.WARNING(
                    "Outro snapshot já está em execução; esta execução será ignorada."
                )
            )
            return

        try:
            self.export_selected_datasets(options)
        finally:
            if not options["skip_lock"]:
                self.release_export_lock(options["database"])

    def export_selected_datasets(self, options):
        datasets = self.resolve_datasets(options["profile"], options["dataset"])
        timestamp = timezone.now().strftime("%Y%m%dT%H%M%SZ")
        drive_client = None

        if not options["skip_upload"]:
            drive_client = GoogleDriveClient()

        for dataset in datasets:
            output_path = self.build_output_path(
                dataset,
                timestamp,
                options["filename"],
                options["output_dir"],
            )
            row_count = self.export_csv(
                dataset=dataset,
                output_path=output_path,
                chunk_size=options["chunk_size"],
                database_alias=options["database"],
                sleep_between_chunks=options["sleep_between_chunks"],
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"[{dataset}] CSV gerado em: {output_path} ({row_count} linhas)"
                )
            )

            if options["skip_upload"]:
                self.stdout.write(
                    self.style.WARNING(f"[{dataset}] Upload ignorado por configuração.")
                )
                continue

            dataset_folder_id = drive_client.ensure_dataset_folder(dataset)
            file_id = drive_client.upload_csv(output_path, dataset_folder_id)
            self.stdout.write(
                self.style.SUCCESS(
                    f"[{dataset}] Upload concluído no Google Drive. file_id={file_id}"
                )
            )

            if not options["skip_retention"]:
                retention_limit = self.get_retention_limit(dataset, options["retention"])
                deleted_count = drive_client.enforce_retention(
                    dataset_folder_id,
                    retention_limit,
                )
                self.stdout.write(
                    self.style.SUCCESS(
                        f"[{dataset}] Retenção aplicada: limite={retention_limit}, "
                        f"removidos={deleted_count}"
                    )
                )

            if not options["keep_local"]:
                output_path.unlink(missing_ok=True)


    def acquire_export_lock(self, database_alias):
        connection = connections[database_alias]

        if connection.vendor != "postgresql":
            return True

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT pg_try_advisory_lock( hashtext(%s) );",
                ["export_database_to_drive_v1"],
            )
            return bool(cursor.fetchone()[0])

    def release_export_lock(self, database_alias):
        connection = connections[database_alias]

        if connection.vendor != "postgresql":
            return

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT pg_advisory_unlock( hashtext(%s) );",
                ["export_database_to_drive_v1"],
            )

    def validate_options(self, options):
        if options["chunk_size"] < 1:
            raise CommandError("--chunk-size deve ser maior que zero.")

        if options["sleep_between_chunks"] < 0:
            raise CommandError("--sleep-between-chunks não pode ser negativo.")

        if options["filename"] and options["dataset"] and len(options["dataset"]) > 1:
            raise CommandError("--filename só pode ser usado com um único --dataset.")

        if options["filename"] and not options["dataset"]:
            raise CommandError("--filename exige o uso de --dataset para evitar colisões.")

        if options["retention"] is not None and options["retention"] < 1:
            raise CommandError("--retention deve ser maior que zero.")

        if options["database"] not in settings.DATABASES:
            raise CommandError(f"Alias de banco não configurado: {options['database']}")

    def resolve_datasets(self, profile, selected_datasets):
        datasets = selected_datasets or self.get_profile_datasets(profile)
        invalid_datasets = sorted(set(datasets) - set(ALL_DATASETS))

        if invalid_datasets:
            raise CommandError(f"Datasets inválidos: {', '.join(invalid_datasets)}")

        return list(dict.fromkeys(datasets))

    def get_profile_datasets(self, profile):
        if profile == "recurring":
            return env_csv("EXPORT_DATABASE_RECURRING_DATASETS", RECURRING_DATASETS)
        if profile == "startup":
            return env_csv("EXPORT_DATABASE_STARTUP_DATASETS", STARTUP_DATASETS)
        return env_csv("EXPORT_DATABASE_ALL_DATASETS", ALL_DATASETS)

    def build_output_path(self, dataset, timestamp, filename, output_dir):
        safe_filename = filename or f"{dataset}_{timestamp}.csv"

        if not safe_filename.endswith(".csv"):
            safe_filename = f"{safe_filename}.csv"

        output_path = Path(output_dir) / dataset / safe_filename
        output_path.parent.mkdir(parents=True, exist_ok=True)
        return output_path

    def export_csv(
        self,
        dataset,
        output_path,
        chunk_size,
        database_alias,
        sleep_between_chunks,
    ):
        queryset, columns = self.get_export_queryset_and_columns(dataset, database_alias)
        values_fields = [field for _, field in columns]
        headers = [header for header, _ in columns]
        row_count = 0

        with output_path.open("w", newline="", encoding="utf-8") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(headers)

            rows = queryset.values(*values_fields).iterator(chunk_size=chunk_size)
            for row in rows:
                writer.writerow(
                    [normalize_csv_value(row[field]) for field in values_fields]
                )
                row_count += 1

                if row_count % chunk_size == 0 and sleep_between_chunks > 0:
                    time.sleep(sleep_between_chunks)

        return row_count

    def get_export_queryset_and_columns(self, dataset, database_alias):
        if dataset in EXPORT_DEFINITIONS:
            definition = EXPORT_DEFINITIONS[dataset]
            return definition["queryset"](database_alias), definition["fields"]

        app_label, model_name = MODEL_EXPORTS[dataset]
        model = apps.get_model(app_label, model_name)
        fields = [(field.name, field.name) for field in model._meta.fields]
        return model.objects.using(database_alias).order_by(model._meta.pk.name), fields

    def get_retention_limit(self, dataset, override):
        if override is not None:
            return override

        env_name = f"EXPORT_DATABASE_RETENTION_{dataset.upper()}"
        return env_int(env_name, DEFAULT_RETENTION_BY_DATASET[dataset])


class GoogleDriveClient:
    def __init__(self):
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        self.root_folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
        credentials = self.get_google_drive_credentials(service_account)
        self.service = build("drive", "v3", credentials=credentials)

    def ensure_dataset_folder(self, dataset):
        folder_id = self.find_folder(dataset)

        if folder_id:
            return folder_id

        metadata = {"name": dataset, "mimeType": FOLDER_MIME_TYPE}
        if self.root_folder_id:
            metadata["parents"] = [self.root_folder_id]

        created_folder = (
            self.service.files()
            .create(body=metadata, fields="id", supportsAllDrives=True)
            .execute()
        )
        return created_folder["id"]

    def find_folder(self, name):
        escaped_name = sanitize_drive_query_value(name)
        query_parts = [
            f"name = '{escaped_name}'",
            f"mimeType = '{FOLDER_MIME_TYPE}'",
            "trashed = false",
        ]

        if self.root_folder_id:
            query_parts.append(f"'{self.root_folder_id}' in parents")

        response = (
            self.service.files()
            .list(
                q=" and ".join(query_parts),
                fields="files(id, name)",
                pageSize=1,
                includeItemsFromAllDrives=True,
                supportsAllDrives=True,
            )
            .execute()
        )
        files = response.get("files", [])
        return files[0]["id"] if files else None

    def upload_csv(self, output_path, folder_id):
        from googleapiclient.http import MediaFileUpload

        media = MediaFileUpload(str(output_path), mimetype="text/csv", resumable=True)
        metadata = {"name": output_path.name, "mimeType": "text/csv"}

        if folder_id:
            metadata["parents"] = [folder_id]

        created_file = (
            self.service.files()
            .create(
                body=metadata,
                media_body=media,
                fields="id",
                supportsAllDrives=True,
            )
            .execute()
        )
        return created_file["id"]

    def enforce_retention(self, folder_id, retention_limit):
        files = self.list_csv_files(folder_id)
        expired_files = files[retention_limit:]

        for expired_file in expired_files:
            self.service.files().delete(
                fileId=expired_file["id"],
                supportsAllDrives=True,
            ).execute()

        return len(expired_files)

    def list_csv_files(self, folder_id):
        query_parts = ["mimeType = 'text/csv'", "trashed = false"]

        if folder_id:
            query_parts.append(f"'{folder_id}' in parents")

        files = []
        page_token = None

        while True:
            response = (
                self.service.files()
                .list(
                    q=" and ".join(query_parts),
                    fields="nextPageToken, files(id, name, createdTime)",
                    orderBy="createdTime desc",
                    pageSize=1000,
                    pageToken=page_token,
                    includeItemsFromAllDrives=True,
                    supportsAllDrives=True,
                )
                .execute()
            )
            files.extend(response.get("files", []))
            page_token = response.get("nextPageToken")

            if not page_token:
                return files

    def get_google_drive_credentials(self, service_account):
        encoded_json = os.getenv("GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON_BASE64")
        raw_json = os.getenv("GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON")
        credentials_file = os.getenv("GOOGLE_DRIVE_SERVICE_ACCOUNT_FILE")

        if encoded_json:
            service_account_info = json.loads(
                base64.b64decode(encoded_json).decode("utf-8")
            )
            return service_account.Credentials.from_service_account_info(
                service_account_info,
                scopes=GOOGLE_DRIVE_SCOPES,
            )

        if raw_json:
            return service_account.Credentials.from_service_account_info(
                json.loads(raw_json),
                scopes=GOOGLE_DRIVE_SCOPES,
            )

        if credentials_file:
            return service_account.Credentials.from_service_account_file(
                credentials_file,
                scopes=GOOGLE_DRIVE_SCOPES,
            )

        raise CommandError(
            "Configure GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON_BASE64, "
            "GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON ou GOOGLE_DRIVE_SERVICE_ACCOUNT_FILE "
            "para habilitar o upload no Google Drive."
        )
