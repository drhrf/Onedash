> This is the design plan approved before implementation began (via Claude
> Code's plan mode). It's preserved here as-is for reference. A few small
> details evolved during the build — notably, `PanelConfig`/`aoi_override`
> was simplified away (panels take `aoi`/`disease` directly rather than
> through a wrapper model), and `cnes_datasus.py` was left undocumented
> rather than stubbed out, since it was never implemented. See `README.md`
> for what was actually built, including the "Known limitations" section.

# Health & Climate Dashboard — Cabo Frio / Região dos Lagos, Brazil

## Context

The user wants a Python web-app dashboard built around a single interactive
map that pulls live data from several external APIs across two domains —
**health services** and **climate** — for **Brazil, with a default focus on
Cabo Frio and the surrounding Região dos Lagos (Rio de Janeiro state)**. Two
controls are core to the request: which data layer(s) render on a map, and
how many map panels appear at once in a dashboard grid (small multiples, for
comparing layers side by side). A cross-cutting requirement ties it together:
every data layer must visibly show its **time lag vs. real time** — not just
"when did we last fetch this," but how old the underlying observation/report
itself is, since health and climate sources vary wildly in freshness (a
weather model updates hourly; a municipal epidemiological report is
deliberately revised over following weeks; a facility registry entry might be
years old). Finally, the user asked explicitly for testing at every
implementation step, including edge cases — this shaped the whole module
layout (see below): logic that can be tested without a browser or network
access is kept separate from the thin Streamlit wiring that can't.

Two decisions were confirmed with the user directly: the UI should be in
**Portuguese (pt-BR)**, and the location search should be **open** (defaults
to Cabo Frio, but users can search anywhere) rather than hard-locked to the
region.

The repo (`drhrf/Onedash`) is currently empty — no code, no commits, no
constraints from legacy work. Every choice below is a fresh pick.

## Important constraint discovered during planning

This sandbox's outbound network is policy-restricted: verified via direct
`curl` and the agent-proxy status endpoint that `api.open-meteo.com`,
`overpass-api.de`, `nominatim.openstreetmap.org`, `info.dengue.mat.br`,
`apidadosabertos.saude.gov.br`, and `portal.inmet.gov.br` are all **blocked
with 403 policy denials** — coding-infra domains (PyPI, GitHub) go through
fine, so this is a scoped allowlist, not a broken connection. **No live HTTP
call to any target API is possible from inside this sandbox**, during
planning or implementation. Consequently: all automated tests built in this
session must run against mocked HTTP responses (which is good practice
regardless), and genuine end-to-end confirmation that live data renders
correctly on the map will need to happen wherever the app is actually run
with normal internet access (the user's machine, or a differently-configured
environment) — this is called out again in the Verification section.

## Tech stack

- **Streamlit** as the web framework. Chosen over Dash (more correct
  callback-graph model for N independent widgets, but far more boilerplate
  and its browser-based test story via Selenium is heavier than what this
  testing-heavy brief wants) and Panel (weakest testing story of the three —
  no headless app-test equivalent). Use `st.fragment` per grid panel so
  interacting with one panel's layer selector doesn't rerun the whole grid.
- **Plotly** (`go.Scattermap` via `st.plotly_chart`) for the map itself, not
  folium/pydeck. Plotly's MapLibre-based `Scattermap` trace (replacing the
  deprecated Mapbox-token-requiring `Scattermapbox`) renders real pannable/
  zoomable tiles with **no API key** (`"open-street-map"` / `"carto-
  positron"` styles ship in Plotly.js). The deciding factor: `st.plotly_chart`
  is a native Streamlit element, and `map_builder.py` returns a plain
  `go.Figure` that pytest can assert against directly with zero Streamlit and
  zero browser involved — folium's output is an HTML string and pydeck's is a
  JSON-ish dict, both clunkier to unit test.
- **requests** (already installed) for HTTP, synchronous to match Streamlit's
  execution model. **pydantic v2** for the data-validation boundary (this is
  where NaN/out-of-range-coordinate/naive-timestamp edge cases get caught
  once, not scattered per module). Deliberately **no geopandas** — nothing in
  this app needs reprojection or spatial joins; avoids a heavy native
  dependency (GDAL/Fiona/pyproj) for a solo project.
- **Testing:** `pytest`, `responses` (mocks `requests`, blocks any real
  network call inside `@responses.activate`, can simulate raised
  `Timeout`/`ConnectionError`), `freezegun` (deterministic freshness/tz
  tests), `streamlit.testing.v1.AppTest` (headless UI smoke tests, ships with
  Streamlit, no browser needed).

## Repo layout

```
Onedash/
├── app.py                            # thin Streamlit entrypoint
├── onedash/
│   ├── config.py                     # constants, TTLs, timeouts, bbox caps, get_secret()
│   ├── strings_pt_br.py              # centralized Portuguese UI copy (single source, easy to audit)
│   ├── datasources/
│   │   ├── base.py                   # DataSource ABC, FetchResult, GeoRecord, AreaOfInterest, enums
│   │   ├── cached.py                 # st.cache_data-wrapped fetch adapter (only file importing streamlit)
│   │   ├── open_meteo_weather.py
│   │   ├── open_meteo_air_quality.py
│   │   ├── open_meteo_marine.py      # sea surface temp / wave data — directly relevant to Cabo Frio upwelling
│   │   ├── open_meteo_geocoding.py   # powers the location search box
│   │   ├── overpass_health.py        # hospitals/clinics/pharmacies, global coverage incl. Brazil
│   │   ├── infodengue.py             # dengue/zika/chikungunya weekly cases, Brazil municipalities only
│   │   └── cnes_datasus.py           # stretch: official Brazilian health-facility registry (verify live first)
│   ├── br_municipalities.py          # small vetted table: Região dos Lagos municipalities, centroid, IBGE geocode
│   ├── freshness.py                  # compute_freshness(), thresholds, humanizer — no streamlit import
│   ├── geo_utils.py                  # parse_iso8601_utc(), bbox-from-radius, shared lat/lon validation
│   ├── map_builder.py                # (panel_config, fetch_results) -> FigureBuildResult(figure, warnings)
│   ├── layer_registry.py             # declarative layer_id -> {label_pt, DataSource class, freshness profile}
│   ├── grid_layout.py                # pure compute_rows(n) grid math
│   └── ui/
│       ├── sidebar.py                # location search + panel-count control
│       └── panel.py                  # renders one grid panel, wrapped in @st.fragment
├── tests/
│   ├── conftest.py                   # frozen-time fixture, sample AOI, FakeDataSource
│   ├── fixtures/*.json               # canned happy-path + malformed responses per source
│   ├── test_freshness.py
│   ├── test_geo_utils.py
│   ├── test_datasources_base.py
│   ├── test_open_meteo_weather.py
│   ├── test_open_meteo_air_quality.py
│   ├── test_open_meteo_marine.py
│   ├── test_open_meteo_geocoding.py
│   ├── test_overpass_health.py
│   ├── test_infodengue.py
│   ├── test_map_builder.py
│   ├── test_grid_layout.py
│   └── test_app_smoke.py             # AppTest-based
├── .streamlit/config.toml            # wide layout, theme
├── requirements.txt / requirements-dev.txt / pyproject.toml
├── .env.example
└── README.md                         # setup, architecture, attribution (OSM/Overpass/Open-Meteo/InfoDengue/DATASUS), "how to add a DataSource"
```

The split between pure logic (`datasources/*`, `freshness.py`, `geo_utils.py`,
`map_builder.py`, `grid_layout.py` — no `streamlit` import, no network in
tests) and thin UI wiring (`ui/*`, `app.py`) is what makes "test at every
step" actually achievable: the hard logic is 100% pytest-testable with no
browser and no live network; only the wiring layer needs `AppTest`, and only
real-tile-rendering needs a manual `streamlit run` check.

## The `DataSource` abstraction

```python
class SourceStatus(str, Enum):
    OK = "ok"
    EMPTY = "empty"              # query succeeded, legitimately zero records
    ERROR = "error"              # HTTP/timeout/malformed — never raises into the UI
    UNSUPPORTED_LOCATION = "unsupported_location"  # e.g. InfoDengue queried outside Brazil

class GeoRecord(BaseModel):
    id: str
    lat: float | None = None
    lon: float | None = None
    value: float | None = None
    label: str = ""
    observation_time: datetime | None = None   # this record's own timestamp, if the API provides one
    raw: dict[str, Any] = Field(default_factory=dict)

    @field_validator("lat")
    @classmethod
    def _lat_range(cls, v):
        if v is not None and not (-90 <= v <= 90):   # chained comparison: fails NaN closed (see note below)
            raise ValueError(f"lat out of range: {v}")
        return v
    # lon mirrors this via one shared geo_utils helper, not duplicated logic

class FetchResult(BaseModel):
    source_id: str
    status: SourceStatus
    records: list[GeoRecord] = Field(default_factory=list)
    observation_time: datetime | None = None   # source-level "as-of" time, for the freshness badge
    fetched_at: datetime                        # tz-aware, injected via a clock function (testable)
    error_message: str | None = None

class AreaOfInterest(BaseModel):
    lat: float; lon: float; radius_km: float = 25.0; label: str = ""

class DataSource(ABC):
    source_id: str
    display_name_pt: str
    freshness_profile: str = "default"

    def fetch(self, aoi: AreaOfInterest, params: dict) -> FetchResult:
        """Template method: last-resort safety net so one bad source can never
        crash the app. Subclasses still catch their OWN known failure modes
        (HTTP errors, timeouts, bad JSON) for specific, useful error messages."""
        try:
            return self._fetch(aoi, params)
        except Exception as exc:
            return FetchResult(source_id=self.source_id, status=SourceStatus.ERROR,
                                fetched_at=self._clock(), error_message=str(exc))

    @abstractmethod
    def _fetch(self, aoi: AreaOfInterest, params: dict) -> FetchResult: ...
```

A new API becomes: subclass `DataSource`, implement `_fetch()`, register in
`layer_registry.py`. Everything else — error boundary, caching, freshness,
rendering — is shared.

**NaN gotcha to pin with a named test:** `-90 <= v <= 90` correctly rejects
`NaN` (any comparison with NaN is `False` in Python, so the chained form
fails closed). The seemingly-equivalent `if v < -90 or v > 90: raise` fails
**open** for NaN (both comparisons are `False`), silently letting invalid
coordinates through. `test_datasources_base.py` pins the correct behavior
explicitly (`test_lat_rejects_nan`), not just a generic out-of-range case.

**Caching** lives outside the `DataSource` classes in `datasources/cached.py`
(the only module allowed to `import streamlit`), because `st.cache_data`
needs hashable arguments and a bound method holding a `requests.Session`
isn't hashable. TTL (refetch politeness) is deliberately **not** the same
thing as the freshness badge (data honesty) — weather/air-quality/marine
cache ~10–15 min, Overpass/CNES ~1 hour+ (facility locations barely change,
and Overpass is the most rate-limit-sensitive source), InfoDengue ~1 hour
(weekly-cadence data, but recent weeks get revised so don't cache too long).

## Regional data & Brazil-specific handling

**Location input:** a free-text search box (Open-Meteo geocoding API, global,
no key) as the primary control, pre-loaded with **Cabo Frio** (lat -22.88,
lon -42.02 — to be confirmed precisely at implementation time rather than
trusted from memory) as the default `AreaOfInterest` on first load. This
satisfies the "open search, Cabo Frio default" decision.

**Layer coverage differs by source, and must degrade gracefully:**
- *Globally applicable* (work anywhere the user searches): Open-Meteo
  weather/air-quality/marine, Overpass health facilities.
- *Brazil/region-specific* (only meaningful for Brazilian municipalities):
  InfoDengue, CNES/DATASUS. These resolve the current AOI against a small
  vetted table in `br_municipalities.py` (Região dos Lagos: Cabo Frio,
  Armação dos Búzios, Arraial do Cabo, São Pedro da Aldeia, Iguaba Grande,
  Araruama, Saquarema — each with centroid + **IBGE 7-digit geocode**, to be
  verified against IBGE's official data at implementation time, not guessed
  from memory, since InfoDengue's `geocode` parameter requires the exact
  code). If the AOI is farther than a small threshold from any known
  municipality, these sources return `SourceStatus.UNSUPPORTED_LOCATION`
  with a clear Portuguese message ("dados do InfoDengue disponíveis apenas
  para municípios da Região dos Lagos neste protótipo") instead of erroring —
  this is itself a named edge-case test.

**InfoDengue** (`info.dengue.mat.br/api/alertcity`) — confirmed via
documentation research: no API key; mandatory params `geocode` (IBGE code),
`disease` (dengue|chikungunya|zika), `format` (json|csv), `ew_start`/
`ew_end` (epi week 1–53), `ey_start`/`ey_end` (year). Explicitly models
reporting delay via **nowcasting** (recent weeks flagged preliminary,
revised later) — this is the strongest, most honest showcase of the time-lag
feature in the whole app, and directly relevant given dengue's regional
importance on the RJ coast.

**CNES/DATASUS** via `apidadosabertos.saude.gov.br` (official Brazilian gov
open-data API, Swagger-documented `CNES/get_cnes_estabelecimentos` endpoint)
— shipped as a **stretch/verify-first** layer, not a launch blocker, since
its exact filtering/schema can't be confirmed live from this sandbox. Until
verified, Overpass is the core (reliable, no-key, already-global) source for
health-facility points, including within Brazil.

**INMET** (national weather stations) — auth requirements couldn't be
confirmed via research; **not** part of MVP, noted only as a possible future
enhancement layer once someone with network access confirms it's key-free.

**Open-Meteo Marine** (wave height/period, sea surface temperature) — no
key, directly motivated by the Cabo Frio upwelling (ressurgência), a well-
known local oceanographic feature that makes sea-temperature data more than
generic decoration for this specific region.

## Freshness / time-lag design

- Everything internal is **UTC, timezone-aware, always**. Every
  `_fetch()` normalizes upstream timestamps immediately (e.g., always
  request Open-Meteo with `&timezone=UTC`; OSM timestamps are already
  `Z`-suffixed; InfoDengue's epidemiological week/year converts to that
  week's Thursday-UTC-midpoint, documented as an approximation). All parsing
  goes through one shared `geo_utils.parse_iso8601_utc()` so a timezone bug
  gets fixed once, not five times.
- `compute_freshness(observation_time, profile, now)` returns a lag
  (`now - observation_time`), a level (`FRESH`/`AGING`/`STALE`/`UNKNOWN`),
  and a Portuguese human-readable string, using per-profile thresholds
  (weather: fresh ≤2h/stale >12h; facility registries: fresh ≤90d/stale
  >2y; epidemiological: fresh ≤2 weeks/stale >6 weeks, reflecting
  InfoDengue's own revision cadence).
- `observation_time=None` → always-visible `UNKNOWN` state (never hidden);
  a naive (non-tz-aware) timestamp raises loudly rather than guessing; a
  **future** timestamp (clock skew) is its own branch, never rendered as
  a nonsensical negative age.
- Point layers with many records (e.g. Overpass nodes with varying OSM edit
  times) collapse to one badge via the **median** record time, with a
  documented `median([])`-on-empty guard falling back to `UNKNOWN`.
- UI shows the freshness badge (`:green[...]`/`:orange[...]`/`:red[...]`)
  prominently per active layer, and a de-emphasized separate "verificado há
  Xmin" (checked N min ago) caption — so users never confuse fetch recency
  with actual data recency, which is the whole point of the feature.

## Configurable map grid

- Panel counts `{1, 2, 3, 4, 6}` map to grid shapes via a pure
  `compute_rows(n)` function (fully unit-tested, including an invalid-N case).
- **Shared location, per-panel layer choice** — matches the literal request
  ("select what data to plot" + "how many maps"): all panels query the same
  `AreaOfInterest`, each panel independently picks which layer(s) render.
  This avoids multiplying Overpass/InfoDengue calls per panel. The
  `PanelConfig` model keeps an unused `aoi_override` field so per-panel
  location becomes an additive future feature, not a rearchitecture.
- **Widget-key collision fix:** pre-allocate `st.session_state.panels` at
  `MAX_PANELS=6` length on first run regardless of how many are currently
  visible; every widget key derives from a **fixed absolute panel index**
  (`f"panel_{i}_layers"`), never a range that changes with the visible
  count. Shrinking the grid just stops rendering panels 4–5 (their state
  persists harmlessly); growing reveals already-initialized state. This is
  what prevents Streamlit's classic `DuplicateWidgetID` bug when panel count
  changes, and gets a dedicated resize-sequence test (1→4→6→2, asserting no
  exception and that panel 0's layer choice survives the whole sequence).
- Zero layers selected on a panel → `map_builder.build_figure([])` returns a
  valid base-map-only figure (never an error); the panel shows an info
  message instead of a blank/broken chart.

## Milestone sequence (every milestone ends with `pytest` green)

1. **Scaffolding** — package skeleton, `requirements*.txt`, `pyproject.toml`,
   `.streamlit/config.toml`. Test: `pytest` collects (0 tests, exit 0);
   `python -c "import onedash"` succeeds.
2. **Minimal running shell** — `app.py` with one static hardcoded point on a
   tokenless `go.Scattermap`. Isolates "does the map actually render/pan/
   zoom" before anything else is built on it. Test: `AppTest` runs without
   exception. Manual check: `streamlit run app.py` in a real browser.
3. **`DataSource` core + `freshness.py`** (pure logic, no real API calls
   yet) — `base.py`, `geo_utils.parse_iso8601_utc`, `freshness.py`, a
   `FakeDataSource` test double. Edge cases: fresh/aging/stale boundaries
   per profile; `None` timestamp → `UNKNOWN`; naive datetime raises; future
   timestamp → clock-skew branch; malformed ISO strings; NaN/±inf/out-of-
   range lat & lon (including the NaN-comparison-chain regression test).
4. **Open-Meteo weather** — fixtures for happy path, empty response, missing
   keys, bad types. Edge cases: 200/500/429, `Timeout`, `ConnectionError`,
   non-JSON body, missing expected keys (no leaking `KeyError`), a
   URL/params-correctness assertion via `responses.calls[0].request.url`.
5. **Open-Meteo air quality + marine + geocoding** — same edge-case matrix
   per endpoint; geocoding additionally covers "no results found" and
   ambiguous/special-character queries.
6. **Overpass health facilities** (the fragile one) — Overpass QL with
   `out meta;` (must remember this or per-node timestamps silently vanish),
   pre-flight bbox-size cap (reject oversized bbox before sending, clear
   message), bounded retry/backoff for 429/504. Edge cases: empty-but-valid
   bbox (e.g. open ocean) → `EMPTY` not error; oversized bbox rejected
   pre-flight; truncated/malformed JSON (Overpass sometimes partials on its
   own timeout); nodes missing `tags.name` (very common — fall back to
   amenity type, never crash); nodes without timestamps → per-record
   `observation_time=None`, median-aggregation falls back to `UNKNOWN`.
7. **InfoDengue** — `br_municipalities.py` table (with verified IBGE codes),
   nearest-municipality resolution with distance threshold. Edge cases: AOI
   outside coverage → `UNSUPPORTED_LOCATION` with clear pt-BR message,
   never an error; disease param variations; malformed/empty responses;
   a named test asserting recent weeks render as visually "preliminary"
   given the nowcasting/reporting-delay data — this is the time-lag
   feature's showcase case.
8. **`map_builder.py` + `layer_registry.py`** (pure, zero Streamlit/network)
   — one layer → one correctly-labeled/colored trace; multiple layers →
   multiple traces; zero layers → base map only; `ERROR` status excluded
   from traces but surfaced in `warnings`; `EMPTY`/`UNSUPPORTED_LOCATION`
   surfaced with distinct messages.
9. **Wire one panel end-to-end (N=1)** — `ui/panel.py` chains: layer
   multiselect → cached fetch → `build_figure` → `st.plotly_chart` →
   freshness badges → warning banners. Sidebar location search, Cabo Frio
   default. Tests: `AppTest` with the cached-fetch adapter monkeypatched to
   canned `FetchResult`s (must never trigger real HTTP) — default AOI runs
   clean, switching layers reruns clean, zero layers shows the info message,
   an unfound search shows a graceful message. **Manual checkpoint**: first
   point a human opens a browser and needs real network access to see real
   data — flagged as blocked in this sandbox (see Verification below).
10. **Configurable grid (1/2/3/4/6)** — `grid_layout` tests over the full
    supported set plus an invalid-N case; the resize-sequence test
    (1→4→6→2) described above.
11. **Polish** — README (setup, architecture, attribution for OSM/Overpass/
    Open-Meteo/InfoDengue/DATASUS, "how to add a DataSource" guide),
    `strings_pt_br.py` audit for consistency, final full-suite + coverage
    run. CNES/DATASUS and INMET remain explicitly-labeled stretch items to
    build only after live endpoint verification happens outside this
    sandbox.

## Running

- **Local dev:** `python -m venv .venv && source .venv/bin/activate`,
  `pip install -r requirements.txt -r requirements-dev.txt`,
  `streamlit run app.py` → `http://localhost:8501`. This alone satisfies
  "lives on a web app"; no deployment infrastructure is built beyond this
  unless requested later (a Streamlit Community Cloud deploy is a trivial
  follow-up — push to GitHub, connect the repo — deliberately not built now
  since no hosting target was requested).

## Verification

- **Every milestone above ends with `pytest -q` green**, covering the pure
  logic (freshness math, timestamp parsing, coordinate validation, HTTP
  error handling via mocked `responses`, figure construction, grid math)
  with zero live network calls — this works fully inside this sandbox.
- **`AppTest`-based smoke tests** confirm the app wires together without
  exceptions, using monkeypatched fetch results — also fully sandbox-safe.
- **Real end-to-end confirmation (live data actually appears correctly on
  the map) cannot happen inside this sandbox** given the network policy
  found during planning. After implementation, this needs a manual pass in
  an environment with normal internet access: `streamlit run app.py`,
  confirm Cabo Frio loads by default, search a couple of other places,
  toggle each layer on/off, resize the grid through 1/2/3/4/6, and confirm
  each layer's freshness badge shows a sensible age (including watching
  InfoDengue show its "preliminary" recent-week state). This is called out
  explicitly rather than silently assumed to work.
