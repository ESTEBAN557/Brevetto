"""Paquete de configuración de Brevetto."""
from .celery import app as celery_app

__all__ = ("celery_app",)
