"""
These tests are not so much unit tests as a benchmark to see if
strategies actually improve our location fixes
"""

from fancy_algo import offline_fix, load_trie, OrderedCityTiles
from fixture_loader import fetch_bssids
import os

from strategies import BasicLocationFix, SimpleTieBreaker

TOTAL_TORONTO_FIXTURES = 131.0

TRIE = load_trie('offline.record_trie')
CITY_TILES = OrderedCityTiles(load_fromdisk=True)

def test_basic_location_fix():
    strategies = [BasicLocationFix, ]

    count = 0
    for fixture_filename in os.listdir('fixtures'):
        bssids = fetch_bssids('fixtures/' + fixture_filename)
        soln = offline_fix(TRIE, CITY_TILES, strategies, bssids)
        if soln:
            count += 1
    print "Basic location fix rate: %0.2f" % (count / TOTAL_TORONTO_FIXTURES)


def test_basic_plus_tie_breaker():
    strategies = [BasicLocationFix, SimpleTieBreaker]

    count = 0
    for fixture_filename in os.listdir('fixtures'):
        bssids = fetch_bssids('fixtures/' + fixture_filename)
        soln = offline_fix(TRIE, CITY_TILES, strategies, bssids)
        if soln:
            count += 1
    print "Basic+SimpleTie location fix rate: %0.2f" % (count / TOTAL_TORONTO_FIXTURES)
