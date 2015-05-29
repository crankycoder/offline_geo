"""
This module provides a mechanism to compute fixes using the trie data.

Test this using test_fancy.py and nose.
"""

import json
import os
import datetime
from demo import OrderedCityTiles
from demo import num2deg
from fixture_loader import fetch_bssids
from marisa_trie import RecordTrie
from strategies import BasicLocationFix
import math



DUPE_NUM = 100

def offline_fix(strategies):
    """
    Setup an array of small integers (8bit) to map to all possible
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

    fixer = LocationFixer(strategies)

    for fixture_filename in os.listdir('fixtures'):
        bssids = fetch_bssids('fixtures/' + fixture_filename)

        now = datetime.datetime.now()
        solution = fixer.find_solution(now, bssids)
        if solution.ok():
            print str(solution)

def adjacent_tile(tile_id):
    city_tiles = load_city()
    tx, ty = city_tiles[tile_id]

    yield city_tiles[(tx-1, ty-1)]
    yield city_tiles[(tx  , ty-1)]
    yield city_tiles[(tx+1, ty-1)]

    yield city_tiles[(tx-1, ty)]
    yield city_tiles[(tx+1, ty)]

    yield city_tiles[(tx-1, ty+1)]
    yield city_tiles[(tx  , ty+1)]
    yield city_tiles[(tx+1, ty+1)]


class LocationFixer(object):
    """
    This class provides location fixes for a particular
    city.
    """
    def __init__(self, strategies, trie_filename='offline.record_trie'):
        self.dupe_num = DUPE_NUM
        self.fmt = "<" + ("i" * self.dupe_num)
        self.trie_filename = trie_filename
        self.offline_trie = RecordTrie(self.fmt).mmap(self.trie_filename)

        self.city_tiles = OrderedCityTiles(load_fromdisk=True)
        self.strategies = strategies


    def find_solution(self, fixTime, bssids):
        '''
        Try to find a location fix given a time stamp and the BSSIDs
        that were collected at that time.

        The timestamp is not precise and is considered accurate to within 1
        minute.
        '''

        result = LocationSolution(self.offline_trie, fixTime, bssids)
        prev_strategy = None

        for strategy in self.strategies:
            strategy(self, prev_strategy, result).execute()
        return result

class LocationSolution(object):
    """
    A LocationSolution is the object that is passed into a chain of 
    strategies to determine a location fix.

    A lat_lon value of None indicates no possible solution has been found.
    """
    def __init__(self, trie, fix_time, bssids):
        self.trie = trie
        self.fixTime = fix_time
        self.bssids = bssids

        self.fix_tileset = None
        self.fix_lat_lon = (None, None)

    def ok(self):
        return self.fix_tileset != None or self.fix_lat_lon != (None, None)

    def __str__(self):
        rset = {}

        if self.fix_tileset != None:
            rset["tileset"] = list(self.fix_tileset)

        if self.fix_lat_lon != (None, None):
           rset['lat_lon'] = self.fix_lat_lon

        return json.dumps(rset)


class SmartTile(object):
    """
    A convenience class to convert to and from slippy tile
    co-ordinates and lat/lon.
    """
    ZOOM_LEVEL = 18

    @classmethod
    def fromLatLon(cls, lat, lon):
        xtile, ytile = SmartTile.deg2num(lat, lon, self.ZOOM_LEVEL)
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
        ytile = int((1.0 - math.log(math.tan(lat_rad) + (1 / math.cos(lat_rad))) / math.pi) / 2.0 * n)
        return (xtile, ytile)


    @staticmethod
    def num2deg(xtile, ytile, zoom):
        n = 2.0 ** zoom
        lon_deg = xtile / n * 360.0 - 180.0
        lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * ytile / n)))
        lat_deg = math.degrees(lat_rad)
        return (lat_deg, lon_deg)
