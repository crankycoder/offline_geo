from demo import num2deg
from fixture_loader import fetch_bssids
import math
from marisa_trie import RecordTrie
from demo import OrderedCityTiles




def offline_fix(dupe_num):
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

    fixer = LocationFixer(dupe_num)

    tile_points = [0] * 65535

    # These BSSIDs are visible in Newmarket near Vic's house
    bssids = fetch_bssids('toronto.bssid')

    last_result = None
    for bssid in bssids:
        matchContainer = t.get(bssid)
        if matchContainer is None:
            print "BSSID [%s] is not in the dataset" % bssid
            continue
        for pt in matchContainer[0]:
            tile_points[pt] += 1

    max_tilept = max(tile_points)
    if max_tilept <= 1:
        print "No tries agreed on a solution"
        return

    maxpt_tileset = set()
    for i, v in enumerate(tile_points):
        if v == max_tilept:
            maxpt_tileset.add(i)

    city_tiles = load_city()
    if len(maxpt_tileset) == 1:
        print "Unique solution found: " + str(maxpt_tileset)
        adjust_center_with_adjacent_wifi(city_tiles, list(maxpt_tileset)[0], max_tilept, tile_points)
        return
    else:
        # We have to solve a tie breaker
        # Square the points for the max point array
        for pt in maxpt_tileset:
            tile_points[pt] *= tile_points[pt]

        msg = "Tie breaker with score: [%d]! Highest scoring tiles: %s"
        print msg % (max_tilept, str(maxpt_tileset))
        print "Adjusted score is: %d" % (max_tilept*max_tilept)

        adj_tile_points = {}

        for tile in maxpt_tileset:
            # For each adjacent tile, add points into the center
            for adjacent_tileid in adjacent_tile(tile):
                new_pts = tile_points[adjacent_tileid]

                msg = "Adding %d points from [%s](%d) to tile: %s(%d)"
                print msg % (new_pts,
                        city_tiles[adjacent_tileid],
                        adjacent_tileid,
                        city_tiles[tile],
                        tile)
                adj_tile_points[tile] = adj_tile_points.get(tile, 0)
                adj_tile_points[tile] += new_pts

        for k, v in adj_tile_points.items():
            tile_points[k] += v

        max_tilept = max(tile_points)
        maxpt_tileset = set()
        for i, v in enumerate(tile_points):
            if v == max_tilept:
                maxpt_tileset.add(i)

        if len(maxpt_tileset) == 1:
            print "Tie breaking solution: %s" % str(maxpt_tileset)
        else:
            msg = "Multiple solutions: "
            print msg + maxpt_tileset

            tiebreaking_set = set()
            maxpt_tilelist = list(maxpt_tileset)
            for i, pt in enumerate(maxpt_tilelist):
                adjacent_tilelist = list(adjacent_tile(pt))
                adjacent_tileset = set(adjacent_tilelist) & set(maxpt_tilelist[i+1:])
                if adjacent_tileset:
                    tiebreaking_set.add(pt)
                    tiebreaking_set = tiebreaking_set.union(pt)

            final_lat = 0
            final_lon = 0
            for tie in tiebreaking_set:
                tx, ty = city_tiles[tie]
                tmp_lat, tmp_lon = num2deg(tx, ty, ZOOM_LEVEL)
                final_lat += (tmp_lat * 1.0/len(tiebreaking_set))
                final_lon += (tmp_lon * 1.0/len(tiebreaking_set))

            msg = "Multiple solutions converging on : " + (final_lat, final_lon)
            # TODO: maybe add adjacent signals to the final solution


def adjust_center_with_adjacent_wifi(city_tiles, center_pt, center_height, tile_points):
    tx, ty = city_tiles[center_pt]
    c_lat, c_lon = num2deg(tx, ty, ZOOM_LEVEL)
    print "Center is at: %f, %f" % (c_lat, c_lon)

    weighted_lat_lon = []
    for adj_tileid in adjacent_tile(center_pt):
        adj_tx, adj_ty = city_tiles[adj_tileid]
        adj_pts = tile_points[adj_tileid]
        if adj_pts:
            print "Extra points at: ", adj_tileid, adj_pts
            print "Lat Lon for %d is %s" % (adj_tileid, num2deg(adj_tx, adj_ty, ZOOM_LEVEL))
            tx, ty = city_tiles[adj_tileid]
            lat, lon = num2deg(tx, ty, ZOOM_LEVEL)
            weighted_lat_lon.append((adj_pts, (lat, lon)))

    # Now compute a new center
    w_lat = 0
    w_lon = 0
    for (adj_pts, (lat, lon)) in weighted_lat_lon:
        w_lat += (lat * adj_pts)
        w_lon += (lon * adj_pts)
    shift_weight = sum([x[0] for x in weighted_lat_lon])
    w_lat /= shift_weight
    w_lon /= shift_weight
    print "Adjacent wlat/wlon: %f, %f" % (w_lat, w_lon)


    # No need to be overly smart here.  Just use 50% real fix, 50%
    # weighted adjusted location.
    n_lat = (c_lat * 0.5 + w_lat * 0.5)
    n_lon = (c_lon * 0.5 + w_lon * 0.5)

    print "Recomputed lat/lon: %f, %f" % (n_lat, n_lon)




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
    def __init__(self, dupe_num, trie_filename='offline.record_trie')
        self.dupe_num = dupe_num
        self.fmt = "<" + ("i" * self.dupe_num)
        self.trie_filename = trie_filename
        self.offline_trie = RecordTrie(self.fmt).mmap(self.trie_filename)

        self.city_tiles = OrderedCityTiles(load_fromdisk=True)

        # TODO: fill in strategies
        self.strategies = []

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
            result = strategy(self, prev_strategy, result)

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


