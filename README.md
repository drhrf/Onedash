# Onedash — Painel de Saúde e Clima (Região dos Lagos, RJ)

A single-page Streamlit dashboard built around one interactive map. Users
choose which data layers to plot (health facilities, weather, air quality,
marine conditions, arbovirus surveillance) and how many map panels to show
at once in a grid (1, 2, 3, 4 or 6). Every layer shows how stale its data
is compared to real time — not just when the app last checked, but how old
the underlying observation or report actually is.

Defaults to Cabo Frio / Região dos Lagos (RJ, Brazil), but the location
search works anywhere.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
streamlit run app.py
```

Opens at `http://localhost:8501`. No API key is required — every data
source wired up so far is free and keyless.

## Running the tests

```bash
pytest                      # full suite
pytest --cov=onedash -q     # with coverage
```

All HTTP calls in the test suite are mocked (`responses`); nothing in
`pytest` touches the network. See **Known limitations** below for what
that does and doesn't guarantee.

## Architecture

```
app.py                      thin entrypoint: sidebar + grid of panels
onedash/
  config.py                 constants, TTLs, timeouts
  strings_pt_br.py          all UI copy in one place
  br_municipalities.py      Região dos Lagos municipalities + IBGE codes
  geo_utils.py               timestamp parsing, bbox/haversine math
  freshness.py               time-lag computation (no streamlit import)
  map_builder.py             FetchResult(s) -> plotly Figure (no streamlit import)
  layer_registry.py          declares the available layers
  grid_layout.py             panel-count -> row/column shape (pure)
  datasources/
    base.py                  DataSource ABC, GeoRecord, FetchResult, AreaOfInterest
    cached.py                 the ONLY module here that imports streamlit
    open_meteo_*.py           weather / air quality / marine / geocoding
    overpass_health.py        OSM health facilities
    infodengue.py             dengue/chikungunya/zika surveillance
  ui/
    sidebar.py                location search, radius, disease, panel count
    panel.py                  one grid panel, wrapped in @st.fragment
tests/
```

The core design split: **pure logic** (`datasources/*` except `cached.py`,
`freshness.py`, `geo_utils.py`, `map_builder.py`, `grid_layout.py`) has no
Streamlit import and no network access in its tests — it's plain,
fast `pytest`. Only the thin UI wiring (`ui/*`, `app.py`) needs
`streamlit.testing.v1.AppTest`, and only real tile rendering needs a
browser. This is what makes "test every step" actually tractable.

### The `DataSource` abstraction

Every API integration subclasses `DataSource` and implements
`_fetch(aoi, params) -> FetchResult`. The base class's `fetch()` is a
template method that catches anything unanticipated, so one failing
source can never crash the app — a bad request becomes a `FetchResult`
with `status=ERROR` and a Portuguese error message, not an exception.

```python
class SourceStatus(str, Enum):
    OK = "ok"
    EMPTY = "empty"                    # succeeded, genuinely zero records
    ERROR = "error"                    # HTTP/timeout/malformed response
    UNSUPPORTED_LOCATION = "unsupported_location"  # e.g. InfoDengue outside Brazil
```

### Adding a new data source

1. Create `onedash/datasources/my_source.py`, subclass `DataSource`, set
   `source_id`, `display_name_pt`, `freshness_profile`, implement `_fetch`.
   Use the `_ok()` / `_empty()` / `_error()` / `_unsupported_location()`
   helpers on the base class to build the result.
2. Normalize any timestamp through `geo_utils.parse_iso8601_utc` so it's
   UTC and timezone-aware — `freshness.py` requires that.
3. Register it in `onedash/layer_registry.py` (one `LayerDefinition` line).
4. Write tests mirroring an existing source's test file: happy path, HTTP
   errors (500/timeout/connection error), malformed/empty responses, and an
   unmocked-request case (`@responses.activate` with nothing registered) to
   confirm graceful degradation without depending on real network access.

### Time-lag / freshness design

`freshness.compute_freshness(observation_time, profile, now)` compares the
data's own observation timestamp — not when the app fetched it — against
now, and buckets the result into `FRESH` / `AGING` / `STALE` / `UNKNOWN`
using per-profile thresholds (weather is stale after ~12h; a facility
registry after ~2 years; epidemiological data after ~6 weeks, reflecting
InfoDengue's own revision cadence). Each panel shows both numbers: how old
the **data** is (color-coded) and how recently the app **checked** (plain
caption) — a cached-but-stale result should never read as fresh just
because it was checked a moment ago.

## Data sources & attribution

| Source | Domain | Key required | Notes |
|---|---|---|---|
| [Open-Meteo](https://open-meteo.com/) | Weather, air quality, marine, geocoding | No | Free tier, global |
| [OpenStreetMap / Overpass](https://wiki.openstreetmap.org/wiki/Overpass_API) | Health facilities | No | © OpenStreetMap contributors |
| [InfoDengue](https://info.dengue.mat.br/) | Dengue/chikungunya/zika surveillance | No | Brazilian municipalities only |

Marine data (wave height, sea surface temperature) was included specifically
because Cabo Frio sits on a well-known cold-water upwelling (*ressurgência*)
— it's a regionally meaningful layer, not generic decoration.

## Known limitations

- **This was built in a network-restricted sandbox.** The dev environment
  used to write and test this app could not reach any of the target APIs
  (confirmed via its egress proxy: 403 policy denials on every one of
  them, including Open-Meteo). All automated tests mock HTTP and pass
  without real network access — but that also means live responses were
  never captured. **Before trusting this in a real setting, do a manual
  pass with normal internet access**: run the app, try a few searches,
  toggle every layer, and check that each freshness badge looks sane.
- **InfoDengue's response schema is a best-effort reconstruction.** Its
  request parameters are confirmed against the official docs, but the
  exact JSON field names in the response (`SE`, `data_iniSE`, `casos_est`)
  come from general knowledge of the project, not a captured live
  response. Parsing is defensive (fails to a clean error, never a crash)
  in case some field differs.
- **Região dos Lagos IBGE codes should get one more check.** The table in
  `br_municipalities.py` was cross-referenced against multiple independent
  sources during development (and one wrong value — Cabo Frio, from
  memory — was caught and fixed this way), but a direct hit against IBGE's
  own API (`servicodados.ibge.gov.br/api/v1/localidades/municipios`) is
  still worth doing before relying on it.
- **Not yet built (by design, not oversight):** an official CNES/DATASUS
  health-facility layer and INMET weather-station data were scoped out of
  the MVP because their exact API shape/auth requirements couldn't be
  confirmed live. `DataSource` makes both a plug-in away once verified.
