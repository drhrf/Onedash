import os

HTTP_TIMEOUT_SECONDS = float(os.environ.get("ONEDASH_HTTP_TIMEOUT_SECONDS", "10"))

DEFAULT_AOI_LAT = -22.8894
DEFAULT_AOI_LON = -42.0286
DEFAULT_AOI_RADIUS_KM = 25.0
DEFAULT_AOI_LABEL = "Cabo Frio, RJ"

# Cache TTL (seconds) — how often we're willing to re-hit the upstream APIs.
# This is about refetch politeness (Overpass in particular is rate-limit
# sensitive), not the same thing as the freshness badge shown to the user,
# which is always computed from each result's own observation_time — a
# cached result still shows its true data age, not "just fetched".
CACHE_TTL_SECONDS = 15 * 60

# Overpass is the most rate-limit-sensitive source in the stack; reject
# oversized bounding boxes before sending rather than letting the query time out.
OVERPASS_MAX_RADIUS_KM = 50.0
