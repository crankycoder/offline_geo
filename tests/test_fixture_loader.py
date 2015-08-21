from fixture_loader import *

def test_list_fixtures():
    fixtures = list(list_fixtures())
    assert len(fixtures) > 0
    for fname in fixtures:
        assert fname.startswith("toronto_trace/toronto_bssid_")
        bssid_list = list(fetch_bssids(fname))
        assert len(bssid_list) >= 0
        for bssid in bssid_list:
            assert len(bssid) == 12
