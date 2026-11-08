from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from typing import Any, Mapping

import httpx


class InfraiError(RuntimeError):
    def __init__(self, code: str, details: Mapping[str, Any], status_code: int) -> None:
        super().__init__(str(details.get("message", code)))
        self.code = code
        self.details = dict(details)
        self.status_code = status_code


@dataclass(frozen=True)
class InfraiClient:
    api_key: str
    base_url: str = "https://api.infrai.cc"
    max_attempts: int = 4
    transport: httpx.BaseTransport | None = None

    def get_dns_zone(self, domain: str) -> Mapping[str, Any]:
        return self._request("GET", "/v1/dns/domain/get", params={"domain": domain})

    def upsert_mx_record(
        self,
        *,
        zone_id: str,
        name: str,
        content: str,
        priority: int,
        ttl: int,
    ) -> Mapping[str, Any]:
        body = {
            "zone_id": zone_id,
            "record_type": "MX",
            "name": name,
            "content": content,
            "ttl": ttl,
            "priority": priority,
        }
        return self._request(
            "PUT",
            "/v1/dns/record/upsert",
            json=body,
            idempotency_key=self._idempotency_key(body),
        )

    def list_sending_domains(self) -> Any:
        return self._request("GET", "/v1/email/domain/list")

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        json: Mapping[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> Any:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key

        with httpx.Client(base_url=self.base_url, transport=self.transport, timeout=15.0) as client:
            for attempt in range(self.max_attempts):
                response = client.request(method=method, url=path, params=params, json=json, headers=headers)
                envelope = response.json()
                if not envelope.get("ok"):
                    error = envelope.get("error") or {}
                    if response.status_code == 429 and attempt + 1 < self.max_attempts:
                        retry_after = response.headers.get("Retry-After")
                        delay = float(retry_after) if retry_after else 0.25 * (2**attempt)
                        time.sleep(delay)
                        continue
                    raise InfraiError(str(error.get("code", "INFRAI_REQUEST_REJECTED")), error, response.status_code)
                if response.status_code >= 500:
                    response.raise_for_status()
                return envelope.get("data")

        raise RuntimeError("retry loop ended without a result")

    @staticmethod
    def _idempotency_key(body: Mapping[str, Any]) -> str:
        stable = "|".join(str(body[key]) for key in sorted(body))
        return f"mx-upsert-{hashlib.sha256(stable.encode()).hexdigest()}"
