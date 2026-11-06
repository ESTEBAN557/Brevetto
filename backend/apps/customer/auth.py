"""
Sesión de cliente de Mi Portal: token firmado (HMAC + vencimiento) con esquema `Authorization: Client <token>`.

Es independiente del JWT del personal (`Bearer`): `JWTAuthentication` ignora este esquema, de modo
que un token de cliente nunca autentica contra los endpoints administrativos.
"""

from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.core import signing
from rest_framework import exceptions
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.permissions import BasePermission

from apps.customer.models import ClientAccount

CLIENT_TOKEN_SALT = "brevetto.customer.session"
KEYWORD = "Client"


def session_ttl_seconds() -> int:
    return int(getattr(settings, "CLIENT_SESSION_TTL_SECONDS", 8 * 3600))


def issue_client_token(account: ClientAccount) -> str:
    return signing.TimestampSigner(salt=CLIENT_TOKEN_SALT).sign_object({"account_id": str(account.pk)})


class ClientPrincipal:
    """Objeto `request.user` para las vistas de cliente (no es un modelo de Django)."""

    is_authenticated = True
    is_anonymous = False

    def __init__(self, account: ClientAccount):
        self.account = account
        self.client = account.client
        self.pk = account.pk

    def __str__(self):
        return self.account.email


class ClientTokenAuthentication(BaseAuthentication):
    keyword = KEYWORD

    def authenticate(self, request):
        header = get_authorization_header(request).split()
        if not header or header[0].decode().lower() != self.keyword.lower():
            return None
        if len(header) != 2:
            raise exceptions.AuthenticationFailed("Encabezado de autorización inválido.")
        token = header[1].decode()
        try:
            payload = signing.TimestampSigner(salt=CLIENT_TOKEN_SALT).unsign_object(
                token, max_age=timedelta(seconds=session_ttl_seconds())
            )
        except signing.SignatureExpired as exc:
            raise exceptions.AuthenticationFailed("Tu sesión expiró. Inicia sesión nuevamente.") from exc
        except signing.BadSignature as exc:
            raise exceptions.AuthenticationFailed("Sesión inválida.") from exc
        account = ClientAccount.objects.select_related("client").filter(pk=payload.get("account_id")).first()
        if account is None:
            raise exceptions.AuthenticationFailed("La cuenta ya no existe.")
        return ClientPrincipal(account), token

    def authenticate_header(self, request):
        return self.keyword


class IsClient(BasePermission):
    def has_permission(self, request, view):
        return isinstance(request.user, ClientPrincipal)
