from __future__ import annotations

import argparse

from .appointment_mail_service import build_client
from .appointment_workflow import MxProviderSettings, configure_appointment_mail


def main() -> None:
    parser = argparse.ArgumentParser(description="Configure prioritized MX records for appointment mail")
    parser.add_argument("domain")
    parser.add_argument("--primary", default="mx1.mail-provider.example")
    parser.add_argument("--backup", default="mx2.mail-provider.example")
    parser.add_argument("--primary-priority", type=int, default=10)
    parser.add_argument("--backup-priority", type=int, default=20)
    args = parser.parse_args()
    settings = MxProviderSettings(
        domain=args.domain,
        primary_exchange=args.primary,
        backup_exchange=args.backup,
        primary_priority=args.primary_priority,
        backup_priority=args.backup_priority,
    )
    result = configure_appointment_mail(settings, build_client())
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
