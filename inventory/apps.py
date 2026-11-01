import os
import sys
from django.apps import AppConfig


class InventoryConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'inventory'

    def ready(self):
        # Prevent scheduler from starting during management commands like migrate/collectstatic
        ignored_commands = {
            'makemigrations', 'migrate', 'collectstatic', 'createsuperuser',
            'shell', 'test', 'run_expiry_check', 'check'
        }
        if any(cmd in sys.argv for cmd in ignored_commands):
            return

        # Avoid double execution under `python manage.py runserver` autoreloader
        is_runserver = 'runserver' in sys.argv
        is_main_process = os.environ.get('RUN_MAIN') == 'true'

        if (is_runserver and is_main_process) or not is_runserver:
            from . import jobs
            jobs.start_scheduler()