"""
Tool implementations for the agent (function calling).
Spelpaus/GamStop do not expose stable public JSON APIs; we return curated official
registry metadata (verifiable URLs + last-reviewed notes). Therapist lookup returns
search URLs (Psychology Today / EU equivalents) — real directory APIs are gated.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

SELF_EXCLUSION_REGISTRY: dict[str, dict[str, Any]] = {
    "SE": {
        "name": "Spelpaus",
        "official_url": "https://www.spelpaus.se",
        "coverage": "All Swedish licensed operators; national register.",
        "notes": "Instant self-exclusion; verified against public Spelinspektionen guidance.",
    },
    "GB": {
        "name": "GamStop",
        "official_url": "https://www.gamstop.co.uk",
        "coverage": "UK Gambling Commission licensed operators.",
        "notes": "Typically effective within 24h; multi-year options available.",
    },
    "US": {
        "name": "State programs",
        "official_url": "https://www.ncsl.org/research/financial-services-and-commerce/gambling-overview.aspx",
        "coverage": "Varies by state — each state maintains its own exclusion list.",
        "notes": "Use your state gaming board site for the authoritative register.",
    },
    "AU": {
        "name": "BetStop",
        "official_url": "https://www.betstop.gov.au",
        "coverage": "Australian licensed wagering operators.",
        "notes": "National register (ACMA).",
    },
    "DE": {
        "name": "OASIS",
        "official_url": "https://www.spielen-mit-verantwortung.de",
        "coverage": "Mandatory cross-operator exclusion for licensed DE gambling.",
        "notes": "Operator staff must register exclusions in OASIS.",
    },
    "IE": {
        "name": "Operator self-exclusion",
        "official_url": "https://www.gamblingcare.ie",
        "coverage": "Per-operator; national scheme evolving — check Gambling Regulatory Authority of Ireland.",
        "notes": "Gambling Care Ireland lists helplines and support.",
    },
}


def lookup_self_exclusion(country_code: str) -> str:
    code = (country_code or "").upper().strip()
    data = SELF_EXCLUSION_REGISTRY.get(code)
    if not data:
        data = {
            "name": "Unknown region",
            "official_url": "",
            "coverage": "Use local regulator or Gamblers Anonymous (ga.org) for chapters.",
            "notes": f"No curated register for {code!r} in SafeHarbor DB.",
        }
    return json.dumps(data, ensure_ascii=False)


def find_therapist(city: str, country_code: str) -> str:
    """Return vetted search URLs — no scraping; user completes search on provider site."""
    city_q = (city or "").strip().replace(" ", "+")
    cc = (country_code or "").upper()
    out: dict[str, Any] = {
        "disclaimer": "SafeHarbor does not endorse individual providers; verify credentials (licensed psychologist / addiction specialist).",
        "psychology_today_search": f"https://www.psychologytoday.com/us/therapists?search={city_q}",
        "note": "Outside the US, use national psychology society directories or your GP for referral.",
    }
    if cc == "GB":
        out["bacp_search"] = "https://www.bacp.co.uk/search/Therapists"
    if cc == "SE":
        out["1177_guidance"] = "https://www.1177.se"
    return json.dumps(out, ensure_ascii=False)


def send_sms_nudge(phone_e164: str, message: str) -> str:
    """Send via Twilio when TWILIO_* env vars are set; otherwise dry-run."""
    sid = os.environ.get("TWILIO_ACCOUNT_SID")
    token = os.environ.get("TWILIO_AUTH_TOKEN")
    from_num = os.environ.get("TWILIO_FROM_NUMBER")
    if not all([sid, token, from_num, phone_e164]):
        logger.info("SMS dry-run to %s: %s", phone_e164, message[:80])
        return json.dumps(
            {
                "status": "dry_run",
                "detail": "Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER to send real SMS.",
            }
        )
    try:
        from twilio.rest import Client

        client = Client(sid, token)
        msg = client.messages.create(
            body=message[:1400],
            from_=from_num,
            to=phone_e164,
        )
        return json.dumps({"status": "sent", "sid": msg.sid})
    except Exception as e:
        logger.exception("Twilio SMS failed")
        return json.dumps({"status": "error", "detail": str(e)})


def record_progress(session_id: str, days_clean: int | None, note: str | None) -> str:
    """Persist progress — imported lazily to avoid circular imports."""
    from django.utils import timezone

    from .models import ChatSession, UserProgress

    try:
        session = ChatSession.objects.get(id=session_id)
    except ChatSession.DoesNotExist:
        return json.dumps({"status": "error", "detail": "session not found"})
    prog, _ = UserProgress.objects.get_or_create(session=session)
    if days_clean is not None:
        prog.days_clean = max(0, int(days_clean))
    if note and str(note).strip():
        prog.summary = (prog.summary + "\n" if prog.summary else "") + str(note).strip()
    prog.last_message_at = timezone.now()
    prog.save()
    return json.dumps(
        {
            "status": "ok",
            "days_clean": prog.days_clean,
            "summary_tail": prog.summary[-500:] if prog.summary else "",
        }
    )


def run_tool(name: str, tool_input: dict[str, Any], *, session_id: str = "") -> str:
    try:
        if name == "lookup_self_exclusion":
            return lookup_self_exclusion(tool_input.get("country_code", ""))
        if name == "find_therapist":
            return find_therapist(
                tool_input.get("city", ""), tool_input.get("country_code", "")
            )
        if name == "send_sms_nudge":
            return send_sms_nudge(
                tool_input.get("phone_e164", ""), tool_input.get("message", "")
            )
        if name == "record_progress":
            if not session_id:
                return json.dumps({"error": "missing session context"})
            return record_progress(
                session_id,
                tool_input.get("days_clean"),
                tool_input.get("note"),
            )
        return json.dumps({"error": f"unknown tool {name}"})
    except Exception as e:
        logger.exception("tool %s failed", name)
        return json.dumps({"error": str(e)})


ANTHROPIC_TOOL_DEFS = [
    {
        "name": "lookup_self_exclusion",
        "description": (
            "Get official self-exclusion program name, URL, and coverage for a country "
            "(ISO code: SE, GB, US, AU, DE, IE)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "country_code": {
                    "type": "string",
                    "description": "Two-letter country code",
                }
            },
            "required": ["country_code"],
        },
    },
    {
        "name": "find_therapist",
        "description": (
            "Return directory search URLs to find licensed therapists for gambling "
            "addiction near a city."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "city": {"type": "string"},
                "country_code": {"type": "string"},
            },
            "required": ["city", "country_code"],
        },
    },
    {
        "name": "send_sms_nudge",
        "description": (
            "Send a short supportive SMS to the user. Requires phone in E.164 format. "
            "Use sparingly and only when the user explicitly asked for text check-ins."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "phone_e164": {"type": "string", "description": "E.164 e.g. +46701234567"},
                "message": {"type": "string"},
            },
            "required": ["phone_e164", "message"],
        },
    },
    {
        "name": "record_progress",
        "description": (
            "Save recovery progress to memory: days gamble-free and/or a short factual note "
            "(e.g. 'User reported 5 days clean'). Do not pass session_id — the server fills it."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "days_clean": {"type": "integer"},
                "note": {"type": "string"},
            },
            "required": [],
        },
    },
]
