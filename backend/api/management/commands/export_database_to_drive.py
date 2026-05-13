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
            ("primary_metric", "primary_metric"),
            ("secondary_metric", "secondary_metric"),
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


class Command(BaseCommand):
    help = "Exporta snapshots do banco para arquivos CSV locais."

    def add_arguments(self, parser):
        parser.add_argument(
            "--profile",
            choices=["recurring", "startup", "all"],
            default=os.getenv("EXPORT_DATABASE_PROFILE", "recurring"),
            help=(
                "Perfil de exportação. 'recurring' exporta avaliações e lotes; "
                "'startup' exporta músicas e metadados de clusters."
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
            "--skip-lock",
            action="store_true",
            default=env_bool("EXPORT_DATABASE_SKIP_LOCK", False),
            help="Não usa advisory lock para evitar execuções concorrentes.",
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
