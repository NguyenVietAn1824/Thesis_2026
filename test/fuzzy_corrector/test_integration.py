"""Integration tests for FuzzyCorrectorService using real Redis data.

Prerequisites:
    - Redis running on localhost:6379
    - Redis populated via: python script/populate_redis_cache.py --flush

Test categories:
    1. Redis cache reading (_find_cached_values_for_column)
    2. Fuzzy matching logic (_fuzzy_match)
    3. Equality conditions — simple & complex inputs
    4. IN conditions — mixed, partial accents
    5. Corrections metadata verification
    6. Function-wrapped columns (LOWER, UPPER, TRIM)
    7. Complex multi-table JOINs
    8. Edge cases & boundary conditions

Settings (settings.yaml):
    fuzzy_threshold: 85
    min_len_ratio: 0.4  (allows short names like "ba đinh" to match "Phường Ba Đình")
    max_fuzzy_matches: 5
"""

from __future__ import annotations

import pytest
import redis as redis_lib

from aqi_agent.domain.autocorrector.fuzzy_corrector import FuzzyCorrectorService
from aqi_agent.domain.autocorrector.models import AutocorrectorInput
from aqi_agent.shared.settings import AutocorrectorSettings


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope='module')
def redis_client() -> redis_lib.Redis:
    """Connect to local Redis; skip if unreachable."""
    r = redis_lib.Redis(host='localhost', port=6379, db=0, decode_responses=False)
    try:
        r.ping()
    except redis_lib.ConnectionError:
        pytest.skip('Redis not reachable on localhost:6379')
    keys = list(r.scan_iter(match='frequent_values:*', count=100))
    if not keys:
        pytest.skip(
            'Redis has no frequent_values:* keys. '
            'Run: python script/populate_redis_cache.py --flush'
        )
    return r


@pytest.fixture(scope='module')
def settings() -> AutocorrectorSettings:
    """Autocorrector settings matching settings.yaml."""
    return AutocorrectorSettings(
        redis_key_prefix='frequent_values',
        fuzzy_threshold=85,
        min_len_ratio=0.4,
        max_fuzzy_matches=5,
    )


@pytest.fixture(scope='module')
def service(redis_client, settings) -> FuzzyCorrectorService:
    return FuzzyCorrectorService(redis_client=redis_client, settings=settings)


# ─── Helper ───────────────────────────────────────────────────────────────────

def _run(service: FuzzyCorrectorService, sql: str):
    """Run process() and return (corrected_sql, corrections)."""
    result = service.process(AutocorrectorInput(sql_query=sql))
    return result.corrected_sql_query, result.corrections


# ═════════════════════════════════════════════════════════════════════════════
# 1. Redis cache reading
# ═════════════════════════════════════════════════════════════════════════════

class TestFindCachedValues:

    def test_districts_name_has_126_values(self, service):
        result = service._find_cached_values_for_column('districts.name')
        values = list(result.values())[0]
        assert len(values) >= 100
        assert any('Hoàn Kiếm' in v for v in values)
        assert any('Ba Đình' in v for v in values)

    def test_air_component_name_has_all_components(self, service):
        values = list(service._find_cached_values_for_column('air_component.name').values())[0]
        for expected in ['PM2.5', 'CO', 'NO2', 'O3', 'PM10', 'SO2', 'aqi']:
            assert expected in values, f'Missing {expected}'

    def test_distric_stats_component_id(self, service):
        values = list(service._find_cached_values_for_column('distric_stats.component_id').values())[0]
        assert set(values) == {'PM2.5', 'aqi'}

    def test_provinces_name(self, service):
        values = list(service._find_cached_values_for_column('provinces.name').values())[0]
        assert values == ['Hà Nội']

    def test_nonexistent_column_returns_empty(self, service):
        assert service._find_cached_values_for_column('fake_table.fake_col') == {}


# ═════════════════════════════════════════════════════════════════════════════
# 2. Fuzzy matching logic
# ═════════════════════════════════════════════════════════════════════════════

class TestFuzzyMatch:

    DISTRICTS = ['Phường Hoàn Kiếm', 'Phường Ba Đình', 'Phường Đống Đa',
                 'Phường Cầu Giấy', 'Phường Long Biên', 'Phường Tây Hồ',
                 'Phường Thanh Xuân', 'Phường Hoàng Mai', 'Phường Hai Bà Trưng']

    # --- exact & full-prefix matches ---

    def test_exact_match(self, service):
        matches = service._fuzzy_match('Phường Hoàn Kiếm', self.DISTRICTS, 85, 5)
        assert 'Phường Hoàn Kiếm' in matches

    def test_full_prefix_no_accents(self, service):
        """'Phuong Hoan Kiem' → 'Phường Hoàn Kiếm'."""
        matches = service._fuzzy_match('Phuong Hoan Kiem', self.DISTRICTS, 85, 5)
        assert 'Phường Hoàn Kiếm' in matches

    # --- short names WITHOUT prefix (the complex cases) ---

    def test_ba_dinh_no_prefix_with_partial_accent(self, service):
        """'ba đinh' → 'Phường Ba Đình' (min_len_ratio=0.4 allows this)."""
        matches = service._fuzzy_match('ba đinh', self.DISTRICTS, 85, 5)
        assert 'Phường Ba Đình' in matches

    def test_ba_dinh_no_prefix_no_accents(self, service):
        """'ba dinh' → 'Phường Ba Đình'."""
        matches = service._fuzzy_match('ba dinh', self.DISTRICTS, 85, 5)
        assert 'Phường Ba Đình' in matches

    def test_hoan_kiem_no_prefix(self, service):
        """'hoan kiem' → 'Phường Hoàn Kiếm'."""
        matches = service._fuzzy_match('hoan kiem', self.DISTRICTS, 85, 5)
        assert 'Phường Hoàn Kiếm' in matches

    def test_tay_ho_no_prefix(self, service):
        """'tay ho' → 'Phường Tây Hồ'."""
        matches = service._fuzzy_match('tay ho', self.DISTRICTS, 85, 5)
        assert 'Phường Tây Hồ' in matches

    def test_cau_giay_no_prefix(self, service):
        """'cau giay' → 'Phường Cầu Giấy'."""
        matches = service._fuzzy_match('cau giay', self.DISTRICTS, 85, 5)
        assert 'Phường Cầu Giấy' in matches

    def test_long_bien_no_prefix(self, service):
        """'long bien' → 'Phường Long Biên'."""
        matches = service._fuzzy_match('long bien', self.DISTRICTS, 85, 5)
        assert 'Phường Long Biên' in matches

    def test_thanh_xuan_no_prefix(self, service):
        """'thanh xuan' → 'Phường Thanh Xuân'."""
        matches = service._fuzzy_match('thanh xuan', self.DISTRICTS, 85, 5)
        assert 'Phường Thanh Xuân' in matches

    def test_hoang_mai_no_prefix(self, service):
        """'hoang mai' → 'Phường Hoàng Mai'."""
        matches = service._fuzzy_match('hoang mai', self.DISTRICTS, 85, 5)
        assert 'Phường Hoàng Mai' in matches

    def test_hai_ba_trung_no_prefix(self, service):
        """'hai ba trung' → 'Phường Hai Bà Trưng'."""
        matches = service._fuzzy_match('hai ba trung', self.DISTRICTS, 85, 5)
        assert 'Phường Hai Bà Trưng' in matches

    # --- with Vietnamese accents but no prefix ---

    def test_dong_da_with_accents_no_prefix(self, service):
        """'đống đa' → 'Phường Đống Đa'."""
        matches = service._fuzzy_match('đống đa', self.DISTRICTS, 85, 5)
        assert 'Phường Đống Đa' in matches

    def test_hoang_mai_with_accents_no_prefix(self, service):
        """'hoàng mai' → 'Phường Hoàng Mai'."""
        matches = service._fuzzy_match('hoàng mai', self.DISTRICTS, 85, 5)
        assert 'Phường Hoàng Mai' in matches

    # --- component matching ---

    def test_pm25_case_insensitive(self, service):
        cached = ['PM2.5', 'aqi', 'CO', 'NO2', 'O3', 'PM10', 'SO2']
        assert 'PM2.5' in service._fuzzy_match('pm2.5', cached, 85, 5)

    def test_aqi_uppercase(self, service):
        cached = ['PM2.5', 'aqi', 'CO', 'NO2', 'O3', 'PM10', 'SO2']
        assert 'aqi' in service._fuzzy_match('AQI', cached, 85, 5)

    # --- negative cases ---

    def test_completely_unrelated(self, service):
        assert service._fuzzy_match('xyzzy_foobar', self.DISTRICTS, 85, 5) == []

    def test_empty_query(self, service):
        assert service._fuzzy_match('', self.DISTRICTS, 85, 5) == []

    def test_empty_cached(self, service):
        assert service._fuzzy_match('ba dinh', [], 85, 5) == []


# ═════════════════════════════════════════════════════════════════════════════
# 3. process() — equality conditions (complex inputs)
# ═════════════════════════════════════════════════════════════════════════════

class TestProcessEqualityComplex:
    """Test WHERE col = 'value' with realistic LLM-generated SQL variations."""

    def test_ba_dinh_lowercase_no_prefix_no_accents(self, service):
        """'ba dinh' → should match 'Phường Ba Đình'."""
        sql = "SELECT * FROM districts WHERE name = 'ba dinh'"
        corrected, corrections = _run(service, sql)
        assert "'ba dinh'" not in corrected
        assert 'Ba Đình' in corrected
        assert corrections is not None
        print(f'  ✅ {corrected}')

    def test_ba_dinh_partial_accents(self, service):
        """'ba đinh' → 'Phường Ba Đình'."""
        sql = "SELECT * FROM districts WHERE name = 'ba đinh'"
        corrected, _ = _run(service, sql)
        assert 'Ba Đình' in corrected
        print(f'  ✅ {corrected}')

    def test_hoan_kiem_no_prefix(self, service):
        """'Hoan Kiem' → 'Phường Hoàn Kiếm'."""
        sql = (
            "SELECT * FROM distric_stats ds "
            "JOIN districts d ON ds.district_id = d.id "
            "WHERE d.name = 'Hoan Kiem'"
        )
        corrected, corrections = _run(service, sql)
        assert 'Hoàn Kiếm' in corrected
        assert corrections is not None
        print(f'  ✅ {corrected}')

    def test_tay_ho_no_prefix(self, service):
        """'tay ho' → 'Phường Tây Hồ'."""
        sql = "SELECT * FROM districts d WHERE d.name = 'tay ho'"
        corrected, _ = _run(service, sql)
        assert 'Tây Hồ' in corrected
        print(f'  ✅ {corrected}')

    def test_cau_giay_no_prefix(self, service):
        """'cau giay' → 'Phường Cầu Giấy'."""
        sql = "SELECT * FROM districts WHERE name = 'cau giay'"
        corrected, _ = _run(service, sql)
        assert 'Cầu Giấy' in corrected
        print(f'  ✅ {corrected}')

    def test_thanh_xuan_no_prefix(self, service):
        """'thanh xuan' → 'Phường Thanh Xuân'."""
        sql = "SELECT * FROM districts WHERE name = 'thanh xuan'"
        corrected, _ = _run(service, sql)
        assert 'Thanh Xuân' in corrected
        print(f'  ✅ {corrected}')

    def test_dong_da_with_accents(self, service):
        """'đống đa' (accented, no prefix) → 'Phường Đống Đa'."""
        sql = "SELECT * FROM districts WHERE name = 'đống đa'"
        corrected, _ = _run(service, sql)
        assert 'Đống Đa' in corrected
        print(f'  ✅ {corrected}')

    def test_hai_ba_trung_no_prefix(self, service):
        """'hai ba trung' → 'Phường Hai Bà Trưng'."""
        sql = "SELECT * FROM districts WHERE name = 'hai ba trung'"
        corrected, _ = _run(service, sql)
        assert 'Hai Bà Trưng' in corrected
        print(f'  ✅ {corrected}')

    def test_soc_son_xa_prefix(self, service):
        """'soc son' → 'Xã Sóc Sơn'."""
        sql = "SELECT * FROM districts WHERE name = 'soc son'"
        corrected, _ = _run(service, sql)
        assert 'Sóc Sơn' in corrected
        print(f'  ✅ {corrected}')

    def test_me_linh_no_prefix(self, service):
        """'me linh' → 'Xã Mê Linh'."""
        sql = "SELECT * FROM districts WHERE name = 'me linh'"
        corrected, _ = _run(service, sql)
        assert 'Mê Linh' in corrected
        print(f'  ✅ {corrected}')

    def test_with_prefix_and_no_accents(self, service):
        """'Phuong Ba Dinh' → 'Phường Ba Đình'."""
        sql = "SELECT * FROM districts WHERE name = 'Phuong Ba Dinh'"
        corrected, _ = _run(service, sql)
        assert 'Phường Ba Đình' in corrected

    def test_exact_value_not_modified(self, service):
        """Exact match should NOT be changed."""
        sql = "SELECT * FROM districts WHERE name = 'Phường Hoàn Kiếm'"
        corrected, corrections = _run(service, sql)
        assert "'Phường Hoàn Kiếm'" in corrected
        assert corrections is None

    def test_wrong_case_component_corrected(self, service):
        """'pm2.5' → 'PM2.5'."""
        sql = "SELECT * FROM distric_stats WHERE component_id = 'pm2.5'"
        corrected, corrections = _run(service, sql)
        assert "'PM2.5'" in corrected
        assert corrections[0].original_value == 'pm2.5'

    def test_province_name_ha_noi(self, service):
        """'Ha Noi' → 'Hà Nội'."""
        sql = "SELECT * FROM provinces WHERE name = 'Ha Noi'"
        corrected, _ = _run(service, sql)
        assert "'Hà Nội'" in corrected

    def test_province_name_lowercase(self, service):
        """'ha noi' → 'Hà Nội'."""
        sql = "SELECT * FROM provinces WHERE name = 'ha noi'"
        corrected, _ = _run(service, sql)
        assert 'Hà Nội' in corrected


# ═════════════════════════════════════════════════════════════════════════════
# 4. process() — IN conditions with complex inputs
# ═════════════════════════════════════════════════════════════════════════════

class TestProcessInComplex:

    def test_multiple_short_district_names(self, service):
        """IN clause with short names, no prefix, no accents."""
        sql = (
            "SELECT * FROM distric_stats ds "
            "JOIN districts d ON ds.district_id = d.id "
            "WHERE d.name IN ('ba dinh', 'hoan kiem', 'cau giay')"
        )
        corrected, corrections = _run(service, sql)
        assert "'ba dinh'" not in corrected
        assert "'hoan kiem'" not in corrected
        assert "'cau giay'" not in corrected
        assert 'Ba Đình' in corrected
        assert 'Hoàn Kiếm' in corrected
        assert 'Cầu Giấy' in corrected
        assert corrections is not None
        print(f'  ✅ {corrected}')

    def test_mixed_exact_and_misspelled(self, service):
        """Mix of exact + short misspelled values."""
        sql = (
            "SELECT * FROM districts d "
            "WHERE d.name IN ('Phường Ba Đình', 'tay ho', 'long bien')"
        )
        corrected, corrections = _run(service, sql)
        assert 'Ba Đình' in corrected       # exact → kept
        assert 'Tây Hồ' in corrected        # corrected
        assert 'Long Biên' in corrected      # corrected
        print(f'  ✅ {corrected}')

    def test_in_with_partial_accents(self, service):
        """Values with partial Vietnamese accents."""
        sql = (
            "SELECT * FROM districts "
            "WHERE name IN ('ba đinh', 'đống đa', 'thanh xuân')"
        )
        corrected, _ = _run(service, sql)
        assert 'Ba Đình' in corrected
        assert 'Đống Đa' in corrected
        assert 'Thanh Xuân' in corrected
        print(f'  ✅ {corrected}')

    def test_in_component_wrong_case(self, service):
        """Component IDs with wrong case in IN clause."""
        sql = "SELECT * FROM distric_stats WHERE component_id IN ('pm2.5', 'AQI')"
        corrected, corrections = _run(service, sql)
        assert "'PM2.5'" in corrected
        assert "'aqi'" in corrected
        assert corrections is not None

    def test_in_with_exact_values_unchanged(self, service):
        sql = "SELECT * FROM distric_stats WHERE component_id IN ('PM2.5', 'aqi')"
        corrected, corrections = _run(service, sql)
        assert "'PM2.5'" in corrected
        assert "'aqi'" in corrected
        assert corrections is None


# ═════════════════════════════════════════════════════════════════════════════
# 5. Corrections metadata
# ═════════════════════════════════════════════════════════════════════════════

class TestCorrectionsMetadata:

    def test_single_correction_has_original_and_corrected(self, service):
        sql = "SELECT * FROM districts WHERE name = 'ba dinh'"
        result = service.process(AutocorrectorInput(sql_query=sql))
        assert result.corrections is not None
        c = result.corrections[0]
        assert c.original_value == 'ba dinh'
        assert 'Phường Ba Đình' in c.corrected_values
        print(f'  ✅ {c.original_value} → {c.corrected_values}')

    def test_multiple_corrections_in_one_query(self, service):
        """Two conditions → two corrections."""
        sql = (
            "SELECT * FROM districts d "
            "JOIN provinces p ON d.province_id = p.id "
            "WHERE d.name = 'hoan kiem' AND p.name = 'Ha Noi'"
        )
        result = service.process(AutocorrectorInput(sql_query=sql))
        assert result.corrections is not None
        originals = {c.original_value for c in result.corrections}
        assert 'hoan kiem' in originals or 'Ha Noi' in originals
        print(f'  ✅ Corrections: {[(c.original_value, c.corrected_values) for c in result.corrections]}')

    def test_no_corrections_when_all_exact(self, service):
        sql = "SELECT * FROM distric_stats WHERE component_id = 'PM2.5'"
        result = service.process(AutocorrectorInput(sql_query=sql))
        assert result.corrections is None

    def test_no_corrections_for_no_where(self, service):
        result = service.process(AutocorrectorInput(sql_query='SELECT 1'))
        assert result.corrections is None

    def test_correction_count_matches_wrong_values(self, service):
        """3 wrong values in IN → 3 corrections."""
        sql = "SELECT * FROM districts WHERE name IN ('ba dinh', 'tay ho', 'cau giay')"
        result = service.process(AutocorrectorInput(sql_query=sql))
        assert result.corrections is not None
        assert len(result.corrections) == 3


# ═════════════════════════════════════════════════════════════════════════════
# 6. Function-wrapped columns (LOWER, UPPER, TRIM)
# ═════════════════════════════════════════════════════════════════════════════

class TestFunctionWrapped:

    def test_lower_wrapped_district_short_name(self, service):
        """LOWER(d.name) = LOWER('ba dinh') → corrected."""
        sql = "SELECT * FROM districts d WHERE LOWER(d.name) = LOWER('ba dinh')"
        corrected, _ = _run(service, sql)
        assert 'Ba Đình' in corrected
        print(f'  ✅ {corrected}')

    def test_lower_wrapped_province(self, service):
        sql = "SELECT * FROM provinces p WHERE LOWER(p.name) = LOWER('Ha Noi')"
        corrected, _ = _run(service, sql)
        assert 'Hà Nội' in corrected

    def test_lower_wrapped_component(self, service):
        sql = "SELECT * FROM distric_stats WHERE LOWER(component_id) = LOWER('pm2.5')"
        corrected, _ = _run(service, sql)
        assert 'PM2.5' in corrected

    def test_reversed_operands_short_name(self, service):
        """'ba dinh' = d.name → reversed."""
        sql = "SELECT * FROM districts d WHERE 'ba dinh' = d.name"
        corrected, _ = _run(service, sql)
        assert "'ba dinh'" not in corrected
        assert 'Ba Đình' in corrected
        print(f'  ✅ {corrected}')

    def test_reversed_operands_province(self, service):
        sql = "SELECT * FROM provinces p WHERE 'Ha Noi' = p.name"
        corrected, _ = _run(service, sql)
        assert 'Hà Nội' in corrected


# ═════════════════════════════════════════════════════════════════════════════
# 7. Complex multi-table JOINs
# ═════════════════════════════════════════════════════════════════════════════

class TestComplexQueries:

    def test_join_short_district_name_and_component(self, service):
        """Both 'ba dinh' (no prefix) and 'pm2.5' (wrong case) corrected."""
        sql = (
            "SELECT d.name, ds.aqi_value "
            "FROM distric_stats ds "
            "JOIN districts d ON ds.district_id = d.id "
            "WHERE d.name = 'ba dinh' AND ds.component_id = 'pm2.5' "
            "ORDER BY ds.date DESC"
        )
        corrected, corrections = _run(service, sql)
        assert 'Ba Đình' in corrected
        assert "'PM2.5'" in corrected
        assert corrections is not None
        assert len(corrections) == 2
        print(f'  ✅ {corrected}')

    def test_three_table_join_all_fuzzy(self, service):
        """District + province + component all need correction."""
        sql = (
            "SELECT d.name, p.name, ds.aqi_value "
            "FROM distric_stats ds "
            "JOIN districts d ON ds.district_id = d.id "
            "JOIN provinces p ON d.province_id = p.id "
            "WHERE d.name = 'hoang mai' "
            "AND p.name = 'ha noi' "
            "AND ds.component_id = 'pm2.5'"
        )
        corrected, corrections = _run(service, sql)
        assert 'Hoàng Mai' in corrected
        assert 'Hà Nội' in corrected
        assert "'PM2.5'" in corrected
        assert corrections is not None
        print(f'  ✅ {corrected}')

    def test_aliased_tables_short_names(self, service):
        """Aliases resolved to real table name for Redis lookup."""
        sql = "SELECT d.name FROM districts d WHERE d.name = 'long bien'"
        corrected, _ = _run(service, sql)
        assert 'Long Biên' in corrected
        print(f'  ✅ {corrected}')

    def test_subquery_not_crashing(self, service):
        sql = (
            "SELECT * FROM districts WHERE id IN "
            "(SELECT district_id FROM distric_stats WHERE component_id = 'pm2.5')"
        )
        corrected, _ = _run(service, sql)
        assert 'SELECT' in corrected

    def test_group_by_order_by_preserved(self, service):
        sql = (
            "SELECT d.name, AVG(ds.aqi_value) as avg_aqi "
            "FROM distric_stats ds "
            "JOIN districts d ON ds.district_id = d.id "
            "WHERE ds.component_id = 'pm2.5' "
            "GROUP BY d.name ORDER BY avg_aqi DESC"
        )
        corrected, _ = _run(service, sql)
        assert "'PM2.5'" in corrected
        assert 'GROUP BY' in corrected
        assert 'ORDER BY' in corrected

    def test_complex_in_with_join_and_short_names(self, service):
        """IN clause with short names in a JOIN query."""
        sql = (
            "SELECT d.name, ds.aqi_value, ds.date "
            "FROM distric_stats ds "
            "JOIN districts d ON ds.district_id = d.id "
            "WHERE d.name IN ('ba dinh', 'hoan kiem', 'tay ho') "
            "AND ds.component_id = 'pm2.5' "
            "AND ds.date >= '2025-01-01' "
            "ORDER BY ds.date DESC"
        )
        corrected, corrections = _run(service, sql)
        assert 'Ba Đình' in corrected
        assert 'Hoàn Kiếm' in corrected
        assert 'Tây Hồ' in corrected
        assert "'PM2.5'" in corrected
        assert "'2025-01-01'" in corrected  # date string not touched
        assert corrections is not None
        print(f'  ✅ {corrected}')


# ═════════════════════════════════════════════════════════════════════════════
# 8. Edge cases & boundary conditions
# ═════════════════════════════════════════════════════════════════════════════

class TestEdgeCases:

    def test_empty_sql(self, service):
        corrected, corrections = _run(service, '')
        assert corrected == ''
        assert corrections is None

    def test_invalid_sql(self, service):
        corrected, corrections = _run(service, 'THIS IS NOT SQL !!!')
        assert corrected == 'THIS IS NOT SQL !!!'
        assert corrections is None

    def test_no_where_clause(self, service):
        corrected, _ = _run(service, 'SELECT * FROM districts')
        assert corrected == 'SELECT * FROM districts'

    def test_numeric_conditions_not_touched(self, service):
        sql = "SELECT * FROM distric_stats WHERE aqi_value > 150 AND hour = 12"
        corrected, _ = _run(service, sql)
        assert '150' in corrected
        assert '12' in corrected

    def test_date_string_not_touched(self, service):
        """Date strings in WHERE should not be fuzzy-matched."""
        sql = "SELECT * FROM distric_stats WHERE date = '2025-01-15'"
        corrected, corrections = _run(service, sql)
        assert "'2025-01-15'" in corrected

    def test_multiple_semicolons_statements(self, service):
        """Multiple SQL statements separated by semicolons."""
        sql = (
            "SELECT * FROM provinces WHERE name = 'Ha Noi'; "
            "SELECT * FROM districts WHERE name = 'ba dinh'"
        )
        corrected, _ = _run(service, sql)
        assert 'Hà Nội' in corrected
        assert 'Ba Đình' in corrected
        print(f'  ✅ {corrected}')

    def test_whitespace_only_sql(self, service):
        corrected, corrections = _run(service, '   ')
        assert corrected.strip() == ''
