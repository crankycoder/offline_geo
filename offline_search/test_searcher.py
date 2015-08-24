"""
These tests are not so much unit tests as a benchmark to see if
strategies actually improve our location fixes
"""

import json
from searcher import offline_fix, load_trie
from citytiles import OrderedCityTiles
from fixture_loader import fetch_bssids
import os

from strategies import BasicLocationFix, SimpleTieBreaker

TOTAL_TORONTO_FIXTURES = 131

TRIE = load_trie('../outputs/toronto.record_trie')
CITY_TILES = OrderedCityTiles(load_fromdisk=True)


def test_basic_location_fix():
    strategies = [BasicLocationFix, ]

    fuzzy_count = 0
    count = 0
    for fixture_filename in os.listdir('tests/fixtures'):
        bssids = fetch_bssids('tests/fixtures/' + fixture_filename)
        soln = offline_fix(TRIE, CITY_TILES, strategies, bssids)

        data = json.loads(soln)
        if len(data['city_tiles']) == 1:
            count += 1
        elif len(data['city_tiles']) > 1:
            fuzzy_count += 1

    tmpl = "Basic location fix rate: %0.2f"
    print tmpl % (count * 1.0 / TOTAL_TORONTO_FIXTURES)

    tmpl = "Basic location fuzzy fix rate: %0.2f"
    print tmpl % (fuzzy_count * 1.0 / TOTAL_TORONTO_FIXTURES)


def test_basic_plus_adjacent():
    strategies = [BasicLocationFix, SimpleTieBreaker]

    fuzzy_count = 0
    count = 0
    for fixture_filename in os.listdir('tests/fixtures'):
        bssids = fetch_bssids('tests/fixtures/' + fixture_filename)
        soln = offline_fix(TRIE, CITY_TILES, strategies, bssids)
        data = json.loads(soln)
        if len(data['city_tiles']) == 1:
            count += 1
        elif len(data['city_tiles']) > 1:
            fuzzy_count += 1

    rate = (count * 1.0/ TOTAL_TORONTO_FIXTURES)
    tmpl = "Basic+SimpleTieBreaker location fix rate: %0.2f" 
    print tmpl % (count * 1.0 / TOTAL_TORONTO_FIXTURES)

    tmpl = "Basic+SimpleTieBreaker location fuzzy fix rate: %0.2f" 
    print tmpl % (fuzzy_count * 1.0 / TOTAL_TORONTO_FIXTURES)
