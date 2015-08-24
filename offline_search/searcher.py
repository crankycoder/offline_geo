"""
This module provides a mechanism to compute fixes using the trie data.

This code should be used when porting the search solution to other
platforms.  Primarily - this means Android/Java

Test this using test_fancy.py and nose.
"""

import json
import datetime
import math
from os.path import abspath, expanduser
import copy
from marisa_trie import RecordTrie

DUPE_NUM = 3


def offline_fix(trie, city_tiles, strategies, bssids):
    """
    Setup an array of small integers (16bit) to map to all possible
    tiles (64k).

    Fetch all set results from the trie for each found BSSID and
    add 1 point to the array index for each location.

    When all BSSIDs have been exhausted, scan the array. For every
    index where we have 2 or more points, we want to weight those
    matches heavily - so multiply the value by 5 and overwrite the
    index value.

    We also want to assign points for adjacent tiles where we have a
    score > 10 (2 tries agree).

    Using the lookup from load_city, find all adjacent tiles and sum
    up the surrounding points and add them into a *second* array to
    avoid double counting.

    Add the values from the second array into the first array.

    Find the index with the maximum value. For ties, return the first
    match.
    """

    fixer = LocationFixer(trie, city_tiles, strategies, '../outputs/toronto.record_trie')

    now = datetime.datetime.now()
    solution = fixer.find_solution(now, bssids)
    return solution.asjson()


def load_trie(trie_filename):
    fmt = ">" + ("i" * DUPE_NUM)
    l = abspath(expanduser(trie_filename))
    return RecordTrie(fmt).mmap(l)


class LocationFixer(object):
    """
    This class provides location fixes for a particular
    city.
    """
    def __init__(self, trie, city_tiles, strategies, trie_filename):

        self.strategies = strategies

        self.offline_trie = trie
        self.city_tiles = city_tiles

    def find_solution(self, fixTime, bssids):
        '''
        Try to find a location fix given a time stamp and the BSSIDs
        that were collected at that time.

        The timestamp is not precise and is considered accurate to within 1
        minute.
        '''

        soln = LocationSolution(self.offline_trie, fixTime, bssids)
        prev_strategy = None

        for strategy in self.strategies:
            curStrategy = strategy(self, prev_strategy)
            curStrategy.execute(soln)
            prev_strategy = curStrategy
        return soln


class LocationSolution(object):
    """
    A LocationSolution is the object that is passed into a chain of
    strategies to determine a location fix.

    A fix_lat_lon value of (None, None) indicates no possible solution
    has been found.

    Each strategy places it's solution data into the dict with a key
    using it's classname. It is the responsibility of each strategy to
    store well structured data. No particular constraints are
    implemented.
    """
    def __init__(self, trie, fix_time, bssids):
        # These should be immutable constants
        self.trie = trie
        self.fixTime = fix_time
        # Make the BSSID list a tuple to force it to be immutable
        self.bssids = tuple(bssids)

        # This is a list of string names that orders simple to most
        # complex strategies
        self.strategy_order = []
        self.strategy_solutions = {}
        self.strategy_guess = {}

    def get_soln_data(self, cls):
        return copy.deepcopy(self.strategy_solutions[cls.__name__])

    def add_soln(self, cls, data, best_guess):
        '''
        Call this method to register a strategy name, it's data and
        it's list of best guess tile ids
        '''
        cls_name = cls.__name__
        assert cls_name not in self.strategy_order

        self.strategy_order.append(cls_name)
        self.strategy_solutions[cls_name] = data
        self.strategy_guess[cls_name] = best_guess

    def best_guess(self):
        # TODO: be smarter.  but for now, just return the first list
        # of results
        for strategy in self.strategy_order:
            soln = self.strategy_guess.get(strategy, [])
            return soln
        return []

    def asjson(self):
        return json.dumps({'city_tiles': self.best_guess()})

    def __str__(self):
        return self.asjson()


class SmartTile(object):
    """
    A convenience class to convert to and from slippy tile
    co-ordinates and lat/lon.
    """
    ZOOM_LEVEL = 18

    @classmethod
    def fromLatLon(cls, lat, lon):
        xtile, ytile = SmartTile.deg2num(lat, lon, cls.ZOOM_LEVEL)
        return SmartTile(xtile, ytile)

    @classmethod
    def fromTileXTileY(cls, xtile, ytile):
        pass

    def __init__(self, xtile, ytile):
        self.xtile = xtile
        self.ytile = ytile
        self.lat, self.lon = SmartTile.num2deg(self.xtile,
                                               self.ytile,
                                               self.ZOOM_LEVEL)

    @staticmethod
    def deg2num(lat_deg, lon_deg, zoom):
        lat_rad = math.radians(lat_deg)
        n = 2.0 ** zoom
        xtile = int((lon_deg + 180.0) / 360.0 * n)
        ytile = int((1.0 - math.log(math.tan(lat_rad) +
                    (1 / math.cos(lat_rad))) / math.pi) / 2.0 * n)
        return (xtile, ytile)

    @staticmethod
    def num2deg(xtile, ytile, zoom):
        n = 2.0 ** zoom
        lon_deg = xtile / n * 360.0 - 180.0
        lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * ytile / n)))
        lat_deg = math.degrees(lat_rad)
        return (lat_deg, lon_deg)
