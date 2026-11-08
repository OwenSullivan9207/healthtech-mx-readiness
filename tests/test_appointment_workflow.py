from typing import Any

from clinic_mail.appointment_workflow import MxProviderSettings, configure_appointment_mail


class RecordingMailInfrastructure:
    def __init__(self, sending_domains: list[dict[str, str]]) -> None:
        self.sending_domains = sending_domains
        self.writes: list[dict[str, Any]] = []

    def get_dns_zone(self, domain: str) -> dict[str, str]:
        assert domain == "care.example.com"
        return {"zone_id": "zone_clinic"}

    def upsert_mx_record(self, **record: Any) -> dict[str, bool]:
        self.writes.append(record)
        return {"saved": True}

    def list_sending_domains(self) -> list[dict[str, str]]:
        return self.sending_domains


def test_mail_becomes_ready_only_for_a_configured_sending_domain() -> None:
    settings = MxProviderSettings(
        domain="care.example.com",
        primary_exchange="mx1.provider.example",
        backup_exchange="mx2.provider.example",
        primary_priority=10,
        backup_priority=30,
    )

    awaiting_client = RecordingMailInfrastructure([])
    awaiting = configure_appointment_mail(settings, awaiting_client)
    ready_client = RecordingMailInfrastructure([{"domain": "care.example.com"}])
    ready = configure_appointment_mail(settings, ready_client)

    assert awaiting.notification_state == "awaiting_sending_domain"
    assert ready.notification_state == "ready"
    assert [write["priority"] for write in ready_client.writes] == [10, 30]
    assert all(write["zone_id"] == "zone_clinic" for write in ready_client.writes)
