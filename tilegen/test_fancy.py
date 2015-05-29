from fancy_algo import offline_fix, load_trie, OrderedCityTiles
from strategies import BasicLocationFix
from fixture_loader import fetch_bssids
import os

def test_fancy_fix():
    strategies = [BasicLocationFix, ]

    trie = load_trie('offline.record_trie')
    city_tiles = OrderedCityTiles(load_fromdisk=True)

    for fixture_filename in os.listdir('fixtures'):
        bssids = fetch_bssids('fixtures/' + fixture_filename)
        soln = offline_fix(trie, city_tiles, strategies, bssids)
        if soln:
            print soln
