"""
These tests are not so much unit tests as a benchmark to see if
strategies actually improve our location fixes
"""

from searcher import offline_fix, load_trie
from citytiles import OrderedCityTiles
from fixture_loader import fetch_bssids
import os

from strategies import BasicLocationFix, AdjacentTileTieBreaker

TOTAL_TORONTO_FIXTURES = 131

TRIE = load_trie('../outputs/toronto.record_trie')
CITY_TILES = OrderedCityTiles(load_fromdisk=True)


def test_basic_location_fix():
    strategies = [BasicLocationFix, ]

    count = 0
    for fixture_filename in os.listdir('tests/fixtures'):
        bssids = fetch_bssids('tests/fixtures/' + fixture_filename)
        soln = offline_fix(TRIE, CITY_TILES, strategies, bssids)
        if soln:
            count += 1
    tmpl = "Basic location fix rate: %0.2f"
    print tmpl % (count * 1.0 / TOTAL_TORONTO_FIXTURES)


def test_basic_plus_adjacent():
    strategies = [BasicLocationFix, AdjacentTileTieBreaker]

    count = 0
    for fixture_filename in os.listdir('tests/fixtures'):
        bssids = fetch_bssids('tests/fixtures/' + fixture_filename)
        soln = offline_fix(TRIE, CITY_TILES, strategies, bssids)
        if soln:
            count += 1
    print "Basic+Adjacent location fix rate: %0.2f" % (count / TOTAL_TORONTO_FIXTURES)
