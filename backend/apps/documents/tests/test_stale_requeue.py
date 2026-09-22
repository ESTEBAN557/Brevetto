"""Pruebas de la red de seguridad periódica que re-encola documentos estancados."""
from datetime import timedelta

import pytest
from django.utils import timezone

from apps.documents.models import Document
from apps.documents.tasks import requeue_stale_documents_task


def _make(filing_number, status, minutes_ago):
    doc = Document.objects.create(
        filing_number=filing_number,
        file_path=f"x/{filing_number}.pdf",
        original_filename=f"{filing_number}.pdf",
        file_hash="c" * 64,
        file_size_bytes=10,
        processing_status=status,
    )
    # auto_now impide fijar updated_at en create(); se ajusta con update().
    Document.objects.filter(pk=doc.pk).update(updated_at=timezone.now() - timedelta(minutes=minutes_ago))
    return doc


@pytest.mark.django_db
class TestRequeueStaleDocuments:
    def test_requeues_only_stale_received_or_processing_documents(self, mock_celery_delay, settings):
        settings.PROCESSING_STALE_AFTER_MINUTES = 15
        stale_processing = _make("RAD-20260920-000101", Document.ProcessingStatus.PROCESSING, 40)
        stale_received = _make("RAD-20260920-000102", Document.ProcessingStatus.RECEIVED, 20)
        _make("RAD-20260920-000103", Document.ProcessingStatus.PROCESSING, 5)          # reciente
        _make("RAD-20260920-000104", Document.ProcessingStatus.NEEDS_REVIEW, 120)      # estado final
        _make("RAD-20260920-000105", Document.ProcessingStatus.FAILED, 120)            # estado final

        result = requeue_stale_documents_task.apply().result

        assert result == {"requeued": 2, "stale_after_minutes": 15}
        requeued = {call.args[0] for call in mock_celery_delay.call_args_list}
        assert requeued == {str(stale_processing.pk), str(stale_received.pk)}

    def test_requeued_documents_are_not_picked_again_immediately(self, mock_celery_delay):
        _make("RAD-20260920-000110", Document.ProcessingStatus.PROCESSING, 60)

        first = requeue_stale_documents_task.apply(args=[15]).result
        second = requeue_stale_documents_task.apply(args=[15]).result

        assert first["requeued"] == 1
        assert second["requeued"] == 0
        assert mock_celery_delay.call_count == 1

    def test_explicit_threshold_overrides_settings(self, mock_celery_delay, settings):
        settings.PROCESSING_STALE_AFTER_MINUTES = 15
        _make("RAD-20260920-000120", Document.ProcessingStatus.PROCESSING, 8)

        assert requeue_stale_documents_task.apply(args=[5]).result["requeued"] == 1

    def test_beat_schedule_is_configured(self, settings):
        entry = settings.CELERY_BEAT_SCHEDULE["requeue-stale-documents"]
        assert entry["task"] == requeue_stale_documents_task.name == "documents.requeue_stale_documents"
        assert entry["schedule"] > 0
