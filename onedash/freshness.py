from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum


class FreshnessLevel(str, Enum):
    FRESH = "fresh"
    AGING = "aging"
    STALE = "stale"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class FreshnessThresholds:
    good_max: timedelta
    warn_max: timedelta


THRESHOLDS: dict[str, FreshnessThresholds] = {
    "weather": FreshnessThresholds(timedelta(hours=2), timedelta(hours=12)),
    "air_quality": FreshnessThresholds(timedelta(hours=2), timedelta(hours=12)),
    "marine": FreshnessThresholds(timedelta(hours=2), timedelta(hours=12)),
    "osm_facility": FreshnessThresholds(timedelta(days=90), timedelta(days=730)),
    "epidemiological": FreshnessThresholds(timedelta(weeks=2), timedelta(weeks=6)),
    "default": FreshnessThresholds(timedelta(hours=6), timedelta(days=7)),
}


@dataclass(frozen=True)
class Freshness:
    observation_time: datetime | None
    now: datetime
    lag: timedelta | None
    level: FreshnessLevel
    description: str


def compute_freshness(
    observation_time: datetime | None,
    profile: str = "default",
    now: datetime | None = None,
) -> Freshness:
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    now_utc = now.astimezone(timezone.utc)

    if observation_time is None:
        return Freshness(None, now_utc, None, FreshnessLevel.UNKNOWN, "idade desconhecida")

    if observation_time.tzinfo is None:
        raise ValueError("observation_time must be timezone-aware")
    obs_utc = observation_time.astimezone(timezone.utc)

    lag = now_utc - obs_utc
    if lag.total_seconds() < 0:
        return Freshness(
            obs_utc, now_utc, lag, FreshnessLevel.UNKNOWN,
            "horário futuro (relógio dessincronizado)",
        )

    thresholds = THRESHOLDS.get(profile, THRESHOLDS["default"])
    if lag <= thresholds.good_max:
        level = FreshnessLevel.FRESH
    elif lag <= thresholds.warn_max:
        level = FreshnessLevel.AGING
    else:
        level = FreshnessLevel.STALE

    return Freshness(obs_utc, now_utc, lag, level, _humanize(lag))


def _humanize(lag: timedelta) -> str:
    total_seconds = int(lag.total_seconds())
    if total_seconds < 60:
        return "agora mesmo"
    minutes = total_seconds // 60
    if minutes < 60:
        return f"há {minutes} min"
    hours = minutes // 60
    if hours < 24:
        return f"há {hours} h"
    days = hours // 24
    if days < 60:
        return f"há {days} dias"
    if days < 730:
        months = round(days / 30.44)
        return f"há ~{months} meses"
    years = days / 365.25
    return f"há ~{years:.1f} anos"


def aggregate_observation_time(times: list[datetime | None]) -> datetime | None:
    """Median of the non-None, UTC-normalized timestamps. Used to collapse a
    layer's many per-record timestamps (e.g. varying OSM edit times) into one
    badge. Returns None if every record lacks a timestamp."""
    known = sorted(t.astimezone(timezone.utc) for t in times if t is not None)
    if not known:
        return None
    mid = len(known) // 2
    if len(known) % 2 == 1:
        return known[mid]
    lo, hi = known[mid - 1], known[mid]
    return lo + (hi - lo) / 2
