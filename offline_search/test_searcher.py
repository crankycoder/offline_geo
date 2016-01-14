"""
These tests are not so much unit tests as a benchmark to see if
strategies actually improve our location fixes
"""

import json
from searcher import offline_fix, load_trie
from citytiles import OrderedCityTiles
from fixture_loader import fetch_bssids
import os
from slippytiles import num2deg

from strategies import BasicLocationFix, SimpleTieBreaker

ZOOM_LEVEL = 18
TRIE = load_trie('tests/fixtures/newmarket.trie')
CITY_TILES = OrderedCityTiles(load_fromdisk=True,
                              fname='tests/fixtures/newmarket_ordered_city.csv')


def test_newmarket():
    strategies = [BasicLocationFix, ]
    bssids = fetch_bssids('tests/fixtures/newmarket_fixtures.json')
    soln = offline_fix(TRIE, CITY_TILES, strategies, bssids)

    # Just pick the first solution
    tile_x, tile_y = json.loads(soln)['tile_coord'][0]
    assert (44.06785366935761, -79.5025634765625) == num2deg(tile_x, tile_y, ZOOM_LEVEL)
