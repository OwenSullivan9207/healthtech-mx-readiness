from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any, Literal, Mapping, Protocol, Sequence


@dataclass
class MxProviderSettings:
    domain: str
    primary_exchange: str
    backup_exchange: str
    primary_priority: int = 10
    backup_priority: int = 20
    record_name: str = "@"
    ttl: int = 3600

    def __post_init__(self) -> None:
        if any(
            len(value) < 3
            for value in (self.domain, self.primary_exchange, self.backup_exchange)
        ):
            raise ValueError("domain and exchanges must be at least 3 characters")
        if (
            not 0 <= self.primary_priority <= 65535
            or not 0 <= self.backup_priority <= 65535
        ):
            raise ValueError("MX priorities must be between 0 and 65535")
        if self.primary_priority >= self.backup_priority:
            raise ValueError("primary_priority must be lower than backup_priority")
        if self.ttl < 60:
            raise ValueError("ttl must be at least 60")


@dataclass
class MxRecordResult:
    host: str
    priority: int


@dataclass
class MailReadiness:
    domain: str
    zone_id: str
    mx_records: list[MxRecordResult]
    sending_domain_configured: bool
    notification_state: Literal["ready", "awaiting_sending_domain"]
    operational_notifications: list[str]

    def model_dump_json(self, *, indent: int | None = None) -> str:
        return json.dumps(asdict(self), indent=indent)


class MailInfrastructure(Protocol):
    def get_dns_zone(self, domain: str) -> Mapping[str, Any]:
        raise AssertionError("protocol method")

    def upsert_mx_record(
        self, *, zone_id: str, name: str, content: str, priority: int, ttl: int
    ) -> Mapping[str, Any]:
        raise AssertionError("protocol method")

    def list_sending_domains(self) -> Any:
        raise AssertionError("protocol method")


def configure_appointment_mail(
    settings: MxProviderSettings, client: MailInfrastructure
) -> MailReadiness:
    zone = client.get_dns_zone(settings.domain)
    zone_id = str(zone["zone_id"])
    records = [
        MxRecordResult(host=settings.primary_exchange, priority=settings.primary_priority),
        MxRecordResult(host=settings.backup_exchange, priority=settings.backup_priority),
    ]
    for record in records:
        client.upsert_mx_record(
            zone_id=zone_id,
            name=settings.record_name,
            content=record.host,
            priority=record.priority,
            ttl=settings.ttl,
        )

    configured_domains = _domain_names(client.list_sending_domains())
    sending_domain_configured = settings.domain.casefold() in configured_domains
    return MailReadiness(
        domain=settings.domain,
        zone_id=zone_id,
        mx_records=records,
        sending_domain_configured=sending_domain_configured,
        notification_state="ready" if sending_domain_configured else "awaiting_sending_domain",
        operational_notifications=[
            "appointment_confirmed",
            "appointment_rescheduled",
            "appointment_cancelled",
        ],
    )


def _domain_names(payload: Any) -> set[str]:
    candidates: Sequence[Any]
    if isinstance(payload, list):
        candidates = payload
    elif isinstance(payload, Mapping):
        value = payload.get("domains", payload.get("items", []))
        candidates = value if isinstance(value, list) else []
    else:
        candidates = []
    return {
        str(item.get("domain", item.get("name", ""))).casefold()
        for item in candidates
        if isinstance(item, Mapping)
    }
