import os

HTTP_TIMEOUT_SECONDS = float(os.environ.get("ONEDASH_HTTP_TIMEOUT_SECONDS", "10"))

DEFAULT_AOI_LAT = -22.8894
DEFAULT_AOI_LON = -42.0286
DEFAULT_AOI_RADIUS_KM = 25.0
DEFAULT_AOI_LABEL = "Cabo Frio, RJ"

# Cache TTLs (seconds) — how often we're willing to re-hit each upstream API.
# This is about refetch politeness, not the same thing as the freshness
# badge shown to the user (which is computed from the data's own
# observation_time, not from when we happened to fetch it).
CACHE_TTL_WEATHER_SECONDS = 10 * 60
CACHE_TTL_AIR_QUALITY_SECONDS = 15 * 60
CACHE_TTL_MARINE_SECONDS = 30 * 60
CACHE_TTL_GEOCODING_SECONDS = 60 * 60
CACHE_TTL_OVERPASS_SECONDS = 60 * 60
CACHE_TTL_INFODENGUE_SECONDS = 60 * 60

# Overpass is the most rate-limit-sensitive source in the stack; reject
# oversized bounding boxes before sending rather than letting the query time out.
OVERPASS_MAX_RADIUS_KM = 50.0
