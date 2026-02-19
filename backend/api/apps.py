import os
import sys
import time
import threading
from django.apps import AppConfig
from django.core.management import call_command
from django.db import connections, DEFAULT_DB_ALIAS, OperationalError, ProgrammingError
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

from app_logger import AppLogger


class ApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "api"

    def ready(self):
        skip_cmds = {
            "makemigrations", "migrate", "collectstatic", "shell",
            "createsuperuser", "check", "test", "loaddata", "dumpdata"
        }
        if any(cmd in sys.argv for cmd in skip_cmds):
            return

        if "runserver" in sys.argv and os.environ.get("RUN_MAIN") != "true":
            return

        if os.getenv("BOOTSTRAP_DB", "true").lower() not in {"true", "1", "yes", "y"}:
            return

        logger = AppLogger(__name__)

        def bootstrap():
            max_wait = 30
            waited = 0
            while waited < max_wait:
                try:
                    connections[DEFAULT_DB_ALIAS].cursor()
                    break
                except OperationalError as e:
                    logger.warning(f"[BOOTSTRAP] Aguardando DB... ({e})")
                    time.sleep(2)
                    waited += 2
            else:
                logger.error("[BOOTSTRAP] Banco indisponível após timeout — abortando.")
                return

            try:
                executor = MigrationExecutor(connections[DEFAULT_DB_ALIAS])
                plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
                if plan:
                    logger.warning("[BOOTSTRAP] Migrações pendentes detectadas — pulando bootstrap.")
                    return
            except Exception as e:
                logger.error(f"[BOOTSTRAP] Falha ao verificar migrações: {e}")
                return

            got_lock = True
            try:
                if connection.vendor == "postgresql":
                    with connection.cursor() as cur:
                        cur.execute("SELECT pg_try_advisory_lock( hashtext(%s) );", ["bootstrap_tracks_v1"])
                        got_lock = bool(cur.fetchone()[0])
            except Exception as e:
                logger.warning(f"[BOOTSTRAP] Falha ao obter advisory lock: {e}")

            if not got_lock:
                logger.info("[BOOTSTRAP] Outro processo já está executando o bootstrap — saindo.")
                return

            retries = 3
            for attempt in range(1, retries + 1):
                try:
                    logger.info("[BOOTSTRAP] Iniciando tracks_database_initialization...")
                    call_command("tracks_database_initialization")
                    logger.info("[BOOTSTRAP] Concluído com sucesso.")
                    break
                except (OperationalError, ProgrammingError) as e:
                    logger.error(f"[BOOTSTRAP] Erro de DB (tentativa {attempt}/{retries}): {e}")
                    time.sleep(3 * attempt)
                except Exception as e:
                    logger.error(f"[BOOTSTRAP] Erro ao inicializar o banco de faixas: {e}")
                    break
            try:
                if connection.vendor == "postgresql":
                    with connection.cursor() as cur:
                        cur.execute("SELECT pg_advisory_unlock( hashtext(%s) );", ["bootstrap_tracks_v1"])
            except Exception:
                pass

        t = threading.Thread(target=bootstrap, daemon=True)
        t.start()
