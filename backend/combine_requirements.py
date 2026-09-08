"""Read-only projections of GMTM task definitions and required-field presence.

Presence is deliberately weaker than validation, eligibility, review, or program
completion. Answer values never leave this module in its returned projection.
"""

from dataclasses import dataclass
from datetime import date, datetime
from html.parser import HTMLParser
import json
import math


MAX_TASKS = 50
MAX_QUESTIONS = 100
MAX_PAYLOAD_CHARS = 200_000
KNOWN_FIELD_TYPES = {"essay", "phone", "email", "gender_id", "date", "address", "height", "metric", "video"}


class SourceDefinitionError(ValueError):
    """A source shape cannot safely be projected as known requirements."""


def source_int(value, *, minimum=0):
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise SourceDefinitionError("Invalid source integer")
    try:
        result = int(value)
    except (ValueError, OverflowError):
        raise SourceDefinitionError("Invalid source integer") from None
    if result < minimum:
        raise SourceDefinitionError("Invalid source integer")
    return result


def source_text(value, *, limit=20_000, allow_empty=False):
    if not isinstance(value, str) or len(value) > limit:
        raise SourceDefinitionError("Invalid source text")
    if not allow_empty and not value.strip():
        raise SourceDefinitionError("Missing source text")
    return value


def source_timestamp(value):
    if value is None:
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return source_text(value, limit=100)


def _object(value):
    if isinstance(value, str):
        if len(value) > MAX_PAYLOAD_CHARS:
            raise SourceDefinitionError("Source payload too large")
        try:
            value = json.loads(value)
        except (ValueError, RecursionError):
            raise SourceDefinitionError("Invalid source JSON") from None
    if not isinstance(value, dict):
        raise SourceDefinitionError("Expected source object")
    return value


class _PlainText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.hidden += 1
        elif tag in ("br", "p", "div", "li", "h1", "h2", "h3"):
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.hidden = max(0, self.hidden - 1)
        elif tag in ("p", "div", "li"):
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def plain_description(value):
    value = source_text(value, allow_empty=True)
    parser = _PlainText()
    parser.feed(value)
    parser.close()
    return "\n".join(line.strip() for line in "".join(parser.parts).splitlines() if line.strip())


@dataclass(frozen=True)
class RequiredField:
    kind: str
    title: str

    @property
    def key(self):
        # GMTM Task builds this key from the question's type and *exact* title.
        # Metric-template metadata is a different identity and can be stale.
        return f"{self.kind}:{self.title}"


@dataclass(frozen=True)
class Activity:
    task_id: int
    event_id: int
    title: str
    order: int
    kind: str
    description: str
    fields: tuple[RequiredField, ...]


def parse_activities(rows, event_id):
    if not isinstance(rows, (tuple, list)) or not 0 < len(rows) <= MAX_TASKS:
        raise SourceDefinitionError("Unavailable activity definitions")
    activities = []
    seen = set()
    for row in rows:
        task_id = source_int(row.get("task_id"), minimum=1)
        if task_id in seen or source_int(row.get("event_id")) != event_id:
            raise SourceDefinitionError("Conflicting activity identity")
        seen.add(task_id)
        if source_int(row.get("visibility")) != 2:
            raise SourceDefinitionError("Nonpublic activity")
        title = source_text(row.get("title"), limit=500)
        task_type = source_int(row.get("type"))
        if task_type == 2:
            kind = "exercise"
        elif task_type == 0 and title.casefold() == "athlete background":
            kind = "background"
        elif task_type == 0 and title.casefold() == "highlight reel":
            kind = "highlight"
        else:
            raise SourceDefinitionError("Unsupported activity kind")
        questions = _object(row.get("payload")).get("questions")
        if not isinstance(questions, list) or not 0 < len(questions) <= MAX_QUESTIONS:
            raise SourceDefinitionError("Unavailable question definitions")
        fields = []
        keys = set()
        for question in questions:
            if not isinstance(question, dict) or type(question.get("required")) is not bool:
                raise SourceDefinitionError("Invalid required-field definition")
            field = RequiredField(
                source_text(question.get("type"), limit=100),
                source_text(question.get("title"), limit=2000),
            )
            if field.key in keys:
                raise SourceDefinitionError("Duplicate question key")
            keys.add(field.key)
            if question["required"]:
                fields.append(field)
        activities.append(Activity(
            task_id, event_id, title, source_int(row.get("list_order")), kind,
            plain_description(row.get("description")), tuple(fields),
        ))
    return sorted(activities, key=lambda activity: (activity.order, activity.task_id))


def _scalar_presence(value):
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if type(value) is int:
        return True
    if type(value) is float:
        return True if math.isfinite(value) else None
    return None


def _presence(kind, value):
    """True/False for known presence/absence, None for an unsupported shape."""
    if kind not in KNOWN_FIELD_TYPES:
        return None
    if value is None:
        return False
    if kind == "gender_id":
        if not isinstance(value, dict) or "gender" not in value:
            return None
        gender = value["gender"]
        if gender is None:
            return False
        if not isinstance(gender, dict) or "value" not in gender:
            return None
        return _scalar_presence(gender["value"])
    if kind == "address" and isinstance(value, dict):
        if "address_one" not in value:
            return None
        if value["address_one"] is not None and not isinstance(value["address_one"], str):
            return None
        return _scalar_presence(value["address_one"])
    if isinstance(value, dict):
        if "value" not in value:
            return None
        value = value["value"]
    elif kind in {"metric", "video"}:
        # Do not accept metadata or a guessed alternate shape as a saved answer.
        return None
    if kind in {"essay", "phone", "email", "date", "address", "video"} and value is not None and not isinstance(value, str):
        return None
    return _scalar_presence(value)


def project_activity(activity, submission, *, personal_available):
    result = {
        "task_id": activity.task_id, "event_id": activity.event_id,
        "title": activity.title, "order": activity.order, "kind": activity.kind,
        "description": activity.description,
        "continuation_url": f"https://gmtm.com/virtuals/{activity.event_id}",
        "submission_state": "unavailable", "evidence_state": "unknown",
        "missing_fields": [], "required_field_count": len(activity.fields),
        # Public form definitions only. They remain useful before account
        # linking and contain no submitted values or metric-template guesses.
        "required_fields": [{"type": field.kind if field.kind in KNOWN_FIELD_TYPES else "unknown",
                             "title": field.title} for field in activity.fields],
        "submitted_at": None,
    }
    if not personal_available:
        return result
    if submission is None:
        result.update(submission_state="not_submitted", evidence_state="missing_fields",
                      missing_fields=[field.title for field in activity.fields])
        return result
    result.update(submission_state="submitted", submitted_at=source_timestamp(submission.get("created_on")))
    try:
        questions = _object(submission.get("payload")).get("questions")
        if not isinstance(questions, dict) or len(questions) > MAX_QUESTIONS:
            return result
    except SourceDefinitionError:
        return result
    missing = []
    unknown = not activity.fields or any(field.kind not in KNOWN_FIELD_TYPES for field in activity.fields)
    for field in activity.fields:
        if field.key not in questions:
            missing.append(field.title)
            continue
        answer = questions[field.key]
        if not isinstance(answer, dict) or "value" not in answer:
            unknown = True
            continue
        presence = _presence(field.kind, answer["value"])
        if presence is None:
            unknown = True
        elif not presence:
            missing.append(field.title)
    result["missing_fields"] = missing
    result["evidence_state"] = "unknown" if unknown else "missing_fields" if missing else "fields_present"
    return result
