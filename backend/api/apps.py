from django.apps import AppConfig
from django.core.management import call_command
from django.db.utils import OperationalError, ProgrammingError
import threading


class ApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api'

    def ready(self):
        def load_data():
            try:
                call_command('load_csv_data')
            except (OperationalError, ProgrammingError):
                pass
            except Exception as e:
                print(f"[INFO] Erro ao carregar CSV: {e}")

        threading.Thread(target=load_data).start()