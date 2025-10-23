import os
import threading
from django.apps import AppConfig
from django.core.management import call_command
from django.db.utils import OperationalError, ProgrammingError

from app_logger import AppLogger

class ApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api'

    def ready(self):
        if os.environ.get('RUN_MAIN') != 'true':
            return
        def load_data():
            logger = AppLogger(__name__)
            try:
                call_command('tracks_database_initialization')
            except (OperationalError, ProgrammingError):
                pass
            except Exception as e:
               logger.error(f"Erro ao inicializar o banco de faixas: {e}")

        threading.Thread(target=load_data).start()