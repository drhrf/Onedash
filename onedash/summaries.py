from __future__ import annotations

from datetime import datetime

from onedash import strings_pt_br as t
from onedash.datasources.base import FetchResult
from onedash.freshness import FreshnessLevel, compute_freshness
from onedash.layer_registry import LayerDefinition

FRESHNESS_COLOR: dict[FreshnessLevel, str] = {
    FreshnessLevel.FRESH: "green",
    FreshnessLevel.AGING: "orange",
    FreshnessLevel.STALE: "red",
    FreshnessLevel.UNKNOWN: "gray",
}


def summarize_records(result: FetchResult, layer: LayerDefinition) -> str:
    """One-line headline for a layer's payload. A single-record layer (a
    weather reading, one municipality's case count) already carries its
    number in the record label; a many-record layer (OSM facilities) is
    summarized by count, since listing every name would be noise."""
    records = result.records
    if not records:
        return ""
    if len(records) == 1 and records[0].label:
        return records[0].label
    return f"{len(records)} {layer.record_noun_pt}"


def freshness_line(layer: LayerDefinition, result: FetchResult, now: datetime | None = None) -> str:
    """Markdown for one layer's status caption.

    Two timestamps are shown deliberately: how old the DATA itself is
    (observation_time, color-coded) and how recently the app merely CHECKED
    (fetched_at, plain). Otherwise a cached-but-stale result reads as fresh
    just because it was checked moments ago — hiding exactly the lag this
    feature exists to expose.
    """
    data_age = compute_freshness(result.observation_time, profile=layer.source_cls.freshness_profile, now=now)
    checked = compute_freshness(result.fetched_at, profile="default", now=now)
    color = FRESHNESS_COLOR[data_age.level]

    summary = summarize_records(result, layer)
    value_part = f"{summary} — " if summary else ""
    return (
        f":{color}[●] **{layer.label_pt}**: {value_part}{t.PANEL_FRESHNESS_DATA_PREFIX} {data_age.description} "
        f"({t.PANEL_FRESHNESS_CHECKED_PREFIX} {checked.description})"
    )
