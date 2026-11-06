"""Pruebas de Mi Portal: acceso con OTP/contraseña, aislamiento por cliente, documentos y requerimientos."""

from datetime import date

import pytest
from django.core.cache import cache
from django.core import mail
from rest_framework.test import APIClient

from apps.core.models import Client, Contract, DocumentType
from apps.customer.models import ClientAccount, LoginCode, ServiceRequest
from apps.customer.services import _hash_code
from apps.documents.models import AuditLog, Document, FilingSequence

BASE = "/api/v1/client-portal"
NIT = {"document_type": "NIT", "identification_number": "900.123.456-1"}


@pytest.fixture(autouse=True)
def reset_state(settings):
    cache.clear()
    settings.CLIENT_OTP_DEV_ECHO = True
    yield
    cache.clear()


def login_with_code(api, channel="sms"):
    sent = api.post(f"{BASE}/auth/request-code/", {**NIT, "channel": channel}, format="json")
    assert sent.status_code == 200, sent.content
    verified = api.post(f"{BASE}/auth/verify-code/", {**NIT, "code": sent.json()["dev_code"]}, format="json")
    assert verified.status_code == 200, verified.content
    return verified.json()


@pytest.fixture
def session(anonymous_client, contract):
    return login_with_code(anonymous_client)


@pytest.fixture
def client_api(session):
    api = APIClient()
    api.credentials(HTTP_AUTHORIZATION=f"Client {session['token']}")
    return api


def make_published_document(contract, code, **extra):
    document_type = DocumentType.objects.get(code=code)
    return Document.objects.create(
        filing_number=FilingSequence.get_next_number(extra.pop("day", date(2026, 10, 8))),
        digital_record=contract.digital_record,
        document_type=document_type,
        file_path="expedientes/x/archivo.pdf",
        original_filename=extra.pop("name", "Estado de cuenta octubre de 2026.pdf"),
        file_hash="b" * 64,
        file_size_bytes=100,
        processing_status=Document.ProcessingStatus.PROCESSED,
        document_date=extra.pop("document_date", date(2026, 10, 8)),
        **extra,
    )


@pytest.mark.django_db
class TestOtpLogin:
    def test_sms_code_logs_in_and_creates_account(self, anonymous_client, contract, tenant):
        data = login_with_code(anonymous_client)
        assert data["account"]["has_password"] is False
        assert ClientAccount.objects.get(client=tenant).email == "contacto@logandina.co"

    def test_email_channel_sends_mail(self, anonymous_client, contract):
        response = anonymous_client.post(f"{BASE}/auth/request-code/", {**NIT, "channel": "email"}, format="json")
        assert response.json()["channel"] == "email"
        assert response.json()["destination"].startswith("co")
        assert response.json()["dev_code"] in mail.outbox[0].body

    def test_unknown_client_gets_same_generic_answer_without_code(self, anonymous_client, contract):
        response = anonymous_client.post(
            f"{BASE}/auth/request-code/", {"document_type": "NIT", "identification_number": "1"}, format="json"
        )
        assert response.status_code == 200
        assert "dev_code" not in response.json() and "destination" not in response.json()
        assert LoginCode.objects.count() == 0

    def test_dev_echo_disabled_never_returns_code(self, anonymous_client, contract, settings):
        settings.CLIENT_OTP_DEV_ECHO = False
        response = anonymous_client.post(f"{BASE}/auth/request-code/", NIT | {"channel": "sms"}, format="json")
        assert "dev_code" not in response.json()

    def test_wrong_code_is_rejected_and_locks_after_five_attempts(self, anonymous_client, contract, tenant):
        sent = anonymous_client.post(f"{BASE}/auth/request-code/", NIT | {"channel": "sms"}, format="json").json()
        for _ in range(5):
            bad = anonymous_client.post(f"{BASE}/auth/verify-code/", NIT | {"code": "000000"}, format="json")
            assert bad.status_code == 400
        # Con el código correcto ya no sirve: se agotaron los intentos.
        late = anonymous_client.post(f"{BASE}/auth/verify-code/", NIT | {"code": sent["dev_code"]}, format="json")
        assert late.status_code == 400

    def test_code_is_single_use(self, anonymous_client, contract):
        sent = anonymous_client.post(f"{BASE}/auth/request-code/", NIT | {"channel": "sms"}, format="json").json()
        body = NIT | {"code": sent["dev_code"]}
        assert anonymous_client.post(f"{BASE}/auth/verify-code/", body, format="json").status_code == 200
        assert anonymous_client.post(f"{BASE}/auth/verify-code/", body, format="json").status_code == 400

    def test_resend_cooldown(self, anonymous_client, contract):
        anonymous_client.post(f"{BASE}/auth/request-code/", NIT | {"channel": "sms"}, format="json")
        again = anonymous_client.post(f"{BASE}/auth/request-code/", NIT | {"channel": "sms"}, format="json")
        assert again.status_code == 429

    def test_code_is_stored_hashed(self, anonymous_client, contract, tenant):
        sent = anonymous_client.post(f"{BASE}/auth/request-code/", NIT | {"channel": "sms"}, format="json").json()
        stored = LoginCode.objects.get()
        assert stored.code_hash != sent["dev_code"]
        assert stored.code_hash == _hash_code(sent["dev_code"], tenant.pk)


@pytest.mark.django_db
class TestPasswordLogin:
    def test_set_password_then_login_with_email(self, client_api, anonymous_client):
        assert client_api.post(f"{BASE}/auth/set-password/", {"password": "corta"}, format="json").status_code == 400
        ok = client_api.post(f"{BASE}/auth/set-password/", {"password": "Clave-segura-1"}, format="json")
        assert ok.status_code == 200
        login = anonymous_client.post(
            f"{BASE}/auth/login/", {"email": "Contacto@logandina.co", "password": "Clave-segura-1"}, format="json"
        )
        assert login.status_code == 200 and login.json()["account"]["has_password"] is True

    def test_wrong_password_and_unknown_email_share_message(self, client_api, anonymous_client):
        client_api.post(f"{BASE}/auth/set-password/", {"password": "Clave-segura-1"}, format="json")
        wrong = anonymous_client.post(
            f"{BASE}/auth/login/", {"email": "contacto@logandina.co", "password": "x" * 9}, format="json"
        )
        unknown = anonymous_client.post(
            f"{BASE}/auth/login/", {"email": "nadie@x.co", "password": "x" * 9}, format="json"
        )
        assert wrong.status_code == unknown.status_code == 401
        assert wrong.json() == unknown.json()


@pytest.mark.django_db
class TestSessionIsolation:
    def test_requires_client_token(self, anonymous_client):
        assert anonymous_client.get(f"{BASE}/me/").status_code in (401, 403)

    def test_staff_jwt_cannot_use_client_endpoints(self, api_client):
        assert api_client.get(f"{BASE}/me/").status_code in (401, 403)

    def test_client_token_cannot_reach_admin_api(self, client_api):
        assert client_api.get("/api/v1/documents/").status_code in (401, 403)
        assert client_api.get("/api/v1/contracts/").status_code in (401, 403)

    def test_tampered_token_rejected(self, anonymous_client, session):
        api = APIClient()
        api.credentials(HTTP_AUTHORIZATION=f"Client {session['token']}x")
        assert api.get(f"{BASE}/me/").status_code == 401


@pytest.mark.django_db
class TestDocuments:
    def test_me_lists_contracts_and_home_counts(self, client_api, contract):
        make_published_document(contract, "ESTADO_CUENTA")
        make_published_document(contract, "FACTURA", name="factura.pdf")
        me = client_api.get(f"{BASE}/me/").json()
        assert [c["contract_number"] for c in me["contracts"]] == ["CONT-2026-042"]
        home = client_api.get(f"{BASE}/home/", {"contract": contract.pk}).json()
        assert home["document_counts"]["estados-de-cuenta"] == 1
        assert home["document_counts"]["facturas"] == 1
        assert home["total_documents"] == 2

    def test_list_filters_by_category_year_month_and_search(self, client_api, contract):
        make_published_document(contract, "ESTADO_CUENTA")
        make_published_document(contract, "ESTADO_CUENTA", document_date=date(2026, 9, 8), name="septiembre.pdf")
        make_published_document(contract, "FACTURA", name="factura.pdf")
        listing = client_api.get(f"{BASE}/documents/", {"category": "estados-de-cuenta"}).json()
        assert listing["count"] == 2
        assert client_api.get(f"{BASE}/documents/", {"category": "estados-de-cuenta", "month": 9}).json()["count"] == 1
        assert client_api.get(f"{BASE}/documents/", {"category": "estados-de-cuenta", "year": 2025}).json()["count"] == 0
        assert client_api.get(f"{BASE}/documents/", {"category": "estados-de-cuenta", "q": "septiem"}).json()["count"] == 1

    def test_unprocessed_documents_are_hidden(self, client_api, contract):
        document = make_published_document(contract, "ESTADO_CUENTA")
        document.processing_status = Document.ProcessingStatus.NEEDS_REVIEW
        document.save()
        assert client_api.get(f"{BASE}/documents/", {"category": "estados-de-cuenta"}).json()["count"] == 0

    def test_other_clients_documents_are_not_visible_or_downloadable(self, client_api, contract):
        other = Client.objects.create(name="Otro", identification_number="800.1-1", email="o@o.co")
        from apps.core.services import create_contract

        other_contract = create_contract(
            contract_number="CONT-OTRO", client=other, property_address="X", start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )
        foreign = make_published_document(other_contract, "ESTADO_CUENTA")
        assert client_api.get(f"{BASE}/documents/", {"category": "estados-de-cuenta"}).json()["count"] == 0
        assert client_api.get(f"{BASE}/documents/{foreign.pk}/download/").status_code == 404

    def test_download_returns_url_and_audits_without_user(self, client_api, contract):
        document = make_published_document(contract, "ESTADO_CUENTA")
        response = client_api.get(f"{BASE}/documents/{document.pk}/download/")
        assert response.status_code == 200 and response.json()["download_url"]
        entry = AuditLog.objects.get(document=document, action=AuditLog.Action.DOWNLOAD)
        assert entry.performed_by is None
        assert entry.details["client_account"] == "contacto@logandina.co"

    def test_client_can_file_a_document_in_own_contract(self, client_api, contract, pdf_factory):
        response = client_api.post(
            f"{BASE}/documents/",
            {"contract": contract.pk, "document_type": "POLIZA_CUMPLIMIENTO", "file": pdf_factory("poliza.pdf")},
            format="multipart",
        )
        assert response.status_code == 201, response.content
        document = Document.objects.get(filing_number=response.json()["filing_number"])
        assert document.source_channel == Document.SourceChannel.WEB_PORTAL
        assert document.digital_record == contract.digital_record
        assert AuditLog.objects.filter(document=document, action=AuditLog.Action.UPLOAD).exists()

    def test_cannot_file_issued_types(self, client_api, contract, pdf_factory):
        response = client_api.post(
            f"{BASE}/documents/",
            {"contract": contract.pk, "document_type": "ESTADO_CUENTA", "file": pdf_factory()},
            format="multipart",
        )
        assert response.status_code == 400


@pytest.mark.django_db
class TestServiceRequests:
    def create(self, client_api, contract, files=()):
        return client_api.post(
            f"{BASE}/requests/",
            {
                "contract": contract.pk,
                "catalog_id": 0,
                "subject": "Solicitud de estado de cuenta",
                "description": "Necesito el detalle de los giros.",
                "files": list(files),
            },
            format="multipart",
        )

    def test_create_builds_timeline_and_attachments(self, client_api, contract, pdf_factory):
        response = self.create(client_api, contract, [pdf_factory("soporte.pdf")])
        assert response.status_code == 201, response.content
        body = response.json()
        assert body["status"] == "NUEVO"
        assert body["events"][0]["status"] == "NUEVO"
        assert body["attachments"][0]["original_filename"] == "soporte.pdf"
        assert body["service"] == "Contabilidad"

    def test_list_search_and_detail(self, client_api, contract):
        created = self.create(client_api, contract).json()
        listing = client_api.get(f"{BASE}/requests/", {"q": f"#{created['id']}"}).json()
        assert [r["id"] for r in listing] == [created["id"]]
        assert client_api.get(f"{BASE}/requests/", {"q": "zzz"}).json() == []
        assert client_api.get(f"{BASE}/requests/{created['id']}/").status_code == 200

    def test_chat_and_attachments_blocked_when_closed(self, client_api, contract, pdf_factory):
        created = self.create(client_api, contract).json()
        url = f"{BASE}/requests/{created['id']}"
        assert client_api.post(f"{url}/messages/", {"body": "Hola"}, format="json").status_code == 201
        service_request = ServiceRequest.objects.get(pk=created["id"])
        service_request.change_status(ServiceRequest.Status.CLOSED, actor="Asesor", note="Resuelto")
        assert client_api.post(f"{url}/messages/", {"body": "Otra vez"}, format="json").status_code == 409
        assert (
            client_api.post(f"{url}/attachments/", {"files": [pdf_factory()]}, format="multipart").status_code == 409
        )
        detail = client_api.get(f"{url}/").json()
        assert [e["status"] for e in detail["events"]] == ["NUEVO", "CERRADO"]

    def test_attachment_download_and_validation(self, client_api, contract, pdf_factory):
        created = self.create(client_api, contract).json()
        url = f"{BASE}/requests/{created['id']}/attachments/"
        bad = client_api.post(url, {"files": [pdf_factory("virus.exe")]}, format="multipart")
        assert bad.status_code == 400
        ok = client_api.post(url, {"files": [pdf_factory("ok.pdf")]}, format="multipart")
        attachment_id = ok.json()[0]["id"]
        assert client_api.get(f"{url}{attachment_id}/download/").json()["download_url"]

    def test_cannot_read_requests_of_other_client(self, client_api, contract):
        other = Client.objects.create(name="Otro", identification_number="800.1-1", email="o@o.co")
        from apps.core.services import create_contract

        other_contract = create_contract(
            contract_number="CONT-OTRO", client=other, property_address="X", start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )
        foreign = ServiceRequest.objects.create(
            client=other, contract=other_contract, case_type="a", service="b", subcategory="c", subject="s",
            description="d",
        )
        assert client_api.get(f"{BASE}/requests/{foreign.pk}/").status_code == 404
        assert client_api.post(f"{BASE}/requests/{foreign.pk}/messages/", {"body": "x"}, format="json").status_code == 404

    def test_cannot_use_contract_of_other_client(self, client_api, contract):
        other = Client.objects.create(name="Otro", identification_number="800.1-1", email="o@o.co")
        from apps.core.services import create_contract

        other_contract = create_contract(
            contract_number="CONT-OTRO", client=other, property_address="X", start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )
        assert self.create(client_api, other_contract).status_code == 404

    def test_catalog(self, client_api):
        catalog = client_api.get(f"{BASE}/request-catalog/").json()
        assert catalog[0] == {
            "id": 0, "case_type": "Administrativo", "service": "Contabilidad",
            "subcategory": "Información de estados de cuenta",
        }
