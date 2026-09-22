"""Configuración de Celery (broker Redis) para Brevetto.

Arranque del worker: `celery -A config worker -l info`
"""
import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("brevetto")

# Toda la configuración de Celery vive en settings.py con el prefijo CELERY_.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Descubre automáticamente tasks.py en cada app instalada (apps.documents.tasks, etc.).
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Tarea de diagnóstico para verificar que el worker recibe mensajes del broker."""
    print(f"Request: {self.request!r}")
