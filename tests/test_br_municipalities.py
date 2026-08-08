from __future__ import annotations

from onedash.br_municipalities import REGIAO_DOS_LAGOS, find_nearest


class TestMunicipalityTableIntegrity:
    def test_has_seven_municipalities(self):
        assert len(REGIAO_DOS_LAGOS) == 7

    def test_ibge_codes_are_unique(self):
        codes = [m.ibge_code for m in REGIAO_DOS_LAGOS]
        assert len(codes) == len(set(codes))

    def test_ibge_codes_are_seven_digits_and_start_with_rj_prefix(self):
        for m in REGIAO_DOS_LAGOS:
            assert 3300000 <= m.ibge_code <= 3399999, m.name

    def test_names_are_unique(self):
        names = [m.name for m in REGIAO_DOS_LAGOS]
        assert len(names) == len(set(names))

    def test_all_coordinates_are_in_plausible_rj_range(self):
        for m in REGIAO_DOS_LAGOS:
            assert -24.0 < m.lat < -21.0, m.name
            assert -43.5 < m.lon < -40.5, m.name


class TestFindNearest:
    def test_exact_match_on_cabo_frio(self):
        result = find_nearest(-22.8894, -42.0286)
        assert result is not None
        assert result.name == "Cabo Frio"

    def test_exact_match_on_buzios(self):
        result = find_nearest(-22.7469, -41.8817)
        assert result is not None
        assert result.name == "Armação dos Búzios"

    def test_far_away_location_returns_none(self):
        # São Paulo city, ~350km from Cabo Frio — well outside the region.
        result = find_nearest(-23.5505, -46.6333)
        assert result is None

    def test_very_far_location_returns_none(self):
        result = find_nearest(35.6762, 139.6503)  # Tokyo
        assert result is None

    def test_respects_custom_max_distance(self):
        # A point ~1km from Cabo Frio should match with a generous radius...
        near_cabo_frio = (-22.8894 + 0.005, -42.0286)
        assert find_nearest(*near_cabo_frio, max_distance_km=50.0) is not None
        # ...but not with an unreasonably tight one.
        assert find_nearest(*near_cabo_frio, max_distance_km=0.01) is None
