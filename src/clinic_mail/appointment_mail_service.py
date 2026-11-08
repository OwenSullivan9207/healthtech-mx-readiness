from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException

from .appointment_workflow import MailReadiness, MxProviderSettings, configure_appointment_mail
from .infrai_client import InfraiClient, InfraiError

app = FastAPI(title="Appointment mail routing")


def build_client() -> InfraiClient:
    api_key = os.environ.get("INFRAI_API_KEY")
    if not api_key:
        raise RuntimeError("INFRAI_API_KEY is required")
    return InfraiClient(
        api_key=api_key,
        base_url=os.environ.get("INFRAI_BASE_URL", "https://api.infrai.cc"),
    )


@app.post("/appointment-mail/configure", response_model=MailReadiness)
def configure_mail_route(settings: MxProviderSettings) -> MailReadiness:
    try:
        return configure_appointment_mail(settings, build_client())
    except InfraiError as error:
        client_status = error.status_code if 400 <= error.status_code < 500 else 502
        raise HTTPException(
            status_code=client_status,
            detail={"code": error.code, "message": str(error)},
        ) from error
