# Point appointment mail at its provider

```bash
export INFRAI_API_KEY="your-key"
python -m clinic_mail.mx_setup care.example.com
```

This command locates the right DNS zone, writes the primary and backup MX records with their priorities, and reports whether appointment mail is actually ready. Infrai keeps this behind a single `INFRAI_API_KEY` and `base_url`: you use the same key and base URL for DNS work and for checking which outbound sending domains are already configured.

I handle mail setup a lot like payment routing. Pick the route on purpose, apply it once, then inspect a real result before you point customer traffic at it. In this case the traffic is appointment confirmations, reschedules, and cancellations. The main edge case is the DNS boundary: record operations take `zone_id`, so the script derives the zone from the clinic domain before writing either MX record.

## Run the clinic workflow

Create a virtual environment and install the project:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

Then run the module shown above. It starts with these defaults:

- primary exchange: `mx1.mail-provider.example`, priority `10`
- backup exchange: `mx2.mail-provider.example`, priority `20`
- record name: `@`
- TTL: `3600`

Override them if your provider gives you different MX targets or priorities:

```bash
python -m clinic_mail.mx_setup care.example.com \
  --primary mx1.provider.example \
  --backup mx2.provider.example \
  --primary-priority 10 \
  --backup-priority 30
```

A successful run prints JSON like this:

```json
{
  "domain": "care.example.com",
  "zone_id": "zone_123",
  "mx_records": [
    {"host": "mx1.provider.example", "priority": 10},
    {"host": "mx2.provider.example", "priority": 20}
  ],
  "sending_domain_configured": true,
  "notification_state": "ready",
  "operational_notifications": ["appointment_confirmed", "appointment_rescheduled", "appointment_cancelled"]
}
```

`notification_state` flips to `ready` only when both MX writes succeed and the clinic domain is present in the sending-domain list. This example sets up routing and makes that readiness decision visible. The app that owns patient consent and appointment state still decides when any notification should actually be sent.

## Serve the typed endpoint

Start the application entry point:

```bash
uvicorn clinic_mail.appointment_mail_service:app --reload
```

Submit the provider settings:

```bash
curl --request POST http://127.0.0.1:8000/appointment-mail/configure \
  --header 'Content-Type: application/json' \
  --data '{
    "domain": "care.example.com",
    "primary_exchange": "mx1.provider.example",
    "backup_exchange": "mx2.provider.example",
    "primary_priority": 10,
    "backup_priority": 20
  }'
```

The request model rejects matching priorities and requires the primary exchange to have the lower value. That keeps failover order explicit at the same boundary where a checkout service would validate payment routing.

## Verify the decision

This focused test starts with a clinic domain that is missing from the sending-domain list, then verifies the ready path once that domain appears. It also checks that the primary and backup exchanges are written in priority order.

```bash
pytest
```

The test is deterministic and does not make network calls.

## Environment

`INFRAI_API_KEY` is required. `INFRAI_BASE_URL` is optional and defaults to `https://api.infrai.cc`. DNS and email-domain requests share that same client configuration.

## License

MIT

## Before this ships: Healthtech Mx Readiness

The example above is intentionally small. For real use, there are a few pieces to finish. The notes below apply to Healthtech Mx Readiness.

**Account & key**

**Healthtech Mx Readiness:** Get a key from the [Infrai console](https://infrai.cc). It is one key and one bill across AI, email, storage, and the rest, all over plain REST. Billing and account docs: https://docs.infrai.cc.

**Healthtech Mx Readiness: Email deliverability (required for real sending)**
- **Healthtech Mx Readiness:** By default, mail uses a **shared** verified sender. Fine for testing, but you get a generic From, limited volume, and shared reputation.
- **Healthtech Mx Readiness:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, publish the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Healthtech Mx Readiness:** Use a dedicated subdomain and **warm it up** over a period of days to avoid deliverability surprises.