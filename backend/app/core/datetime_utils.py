from datetime import datetime, timezone
from typing import Annotated, Optional
from pydantic import PlainSerializer


def ensure_utc(dt: datetime) -> datetime:
    """Normalize a naive (assumed UTC) or offset-aware datetime to UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def serialize_utc_datetime(dt: Optional[datetime]) -> Optional[str]:
    """Serialize a datetime as an ISO 8601 UTC string ending with 'Z'."""
    if dt is None:
        return None
    return ensure_utc(dt).isoformat().replace("+00:00", "Z")


UTCDatetime = Annotated[
    datetime,
    PlainSerializer(serialize_utc_datetime, return_type=str, when_used="json"),
]
