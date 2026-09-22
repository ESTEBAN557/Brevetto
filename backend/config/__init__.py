"""Paquete de configuración de Brevetto.

Importa la app de Celery para que `@shared_task` la registre al iniciar Django.
"""
from .celery import app as celery_app

__all__ = ("celery_app",)
