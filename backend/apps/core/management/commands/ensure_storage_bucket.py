"""Crea el bucket S3/MinIO configurado si aún no existe (idempotente)."""
import boto3
from botocore.exceptions import ClientError, EndpointConnectionError
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Garantiza la existencia del bucket AWS_STORAGE_BUCKET_NAME en S3/MinIO."

    def handle(self, *args, **options):
        bucket = settings.AWS_STORAGE_BUCKET_NAME
        client = boto3.client(
            "s3",
            endpoint_url=settings.AWS_S3_ENDPOINT_URL,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME,
        )
        try:
            client.head_bucket(Bucket=bucket)
            self.stdout.write(self.style.SUCCESS(f"Bucket '{bucket}' ya existe."))
            return
        except EndpointConnectionError as exc:
            raise CommandError(f"No se pudo conectar al endpoint S3: {exc}") from exc
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "")
            if code not in ("404", "NoSuchBucket", "NotFound"):
                raise CommandError(f"Error consultando el bucket '{bucket}': {exc}") from exc

        client.create_bucket(Bucket=bucket)
        self.stdout.write(self.style.SUCCESS(f"Bucket '{bucket}' creado correctamente."))
