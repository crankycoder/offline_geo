import copy
import math


class AbstractLocationFixStrategy(object):

    # This is a duplicate of what is in SmartTile. Need to fix that.
    ZOOM_LEVEL = 18

    def __init__(self, locationFixer, prevStep):
        self.locationFixer = locationFixer
        self.prevStep = prevStep

    def num2deg(self, xtile, ytile, zoom):
        n = 2.0 ** zoom
        lon_deg = xtile / n * 360.0 - 180.0
        lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * ytile / n)))
        lat_deg = math.degrees(lat_rad)
        return (lat_deg, lon_deg)

    def deg2num(self, lat_deg, lon_deg, zoom):
        """
        Compute lat, lon and zoom level to an x,y tile co-ordinate
        Zoom level is defined as:
        * 0 (1 tile for the world)
        * 19 max zoom (274,877,906,944 tiles for the world)
        """
        lat_rad = math.radians(lat_deg)
        n = 2.0 ** zoom
        xtile = int((lon_deg + 180.0) / 360.0 * n)
        ytile = int((1.0 - math.log(math.tan(lat_rad) + (1 /
                    math.cos(lat_rad))) / math.pi) / 2.0 * n)
        return (xtile, ytile)

    def adjacent_tile(self, tile_id):
        city_tiles = self.locationFixer.city_tiles
        tx, ty = city_tiles[tile_id]

        yield city_tiles[(tx-1, ty-1)]
        yield city_tiles[(tx, ty-1)]
        yield city_tiles[(tx+1, ty-1)]

        yield city_tiles[(tx-1, ty)]
        yield city_tiles[(tx+1, ty)]

        yield city_tiles[(tx-1, ty+1)]
        yield city_tiles[(tx, ty+1)]
        yield city_tiles[(tx+1, ty+1)]

    def execute(self):
        """ Concrete strategies must implements a strategy against"""
        raise NotImplementedError


class BasicLocationFix(AbstractLocationFixStrategy):
    """
    This tries to build a map of 65535 tiles and tries
    to find tiles where multiple BSSID lookups agree on a location.
    """
    def __init__(self, locationFixer, prevStep):
        super(BasicLocationFix, self).__init__(locationFixer, prevStep)

    def execute(self, locationSolution):
        # This is always the first fix, we don't care about any prior
        # possible solutions

        tile_points = [0] * ((2**16)-1)

        bssids = locationSolution.bssids
        trie = locationSolution.trie

        for bssid in bssids:
            matchContainer = trie.get(bssid)
            if matchContainer is None:
                continue
            for pt in matchContainer[0]:
                tile_points[pt] += 1

        highest_score_intile = max(tile_points)
        best_guess = []

        if highest_score_intile > 0:
            for i, v in enumerate(tile_points):
                if v == highest_score_intile:
                    best_guess.append(i)

        locationSolution.add_soln(self.__class__,
                                  tile_points,
                                  best_guess)


class SimpleTieBreaker(AbstractLocationFixStrategy):
    def __init__(self, locationFixer, prevStep):
        super(SimpleTieBreaker, self).__init__(locationFixer,
                                               prevStep)


    def execute(self, locationSolution):
        # Make a copy of previous data sets
        tile_points = locationSolution.get_soln_data(BasicLocationFix)

        # Handy dandy shortcut
        city_tiles = self.locationFixer.city_tiles

        # We have to solve a tie breaker
        import pdb
        pdb.set_trace()
        if len(tile_points) > 0:
            pass

        import pdb
        pdb.set_trace()

        if len(self.maxpt_tileset) <= 1:
            return

        msg = "Tie breaker with score: [%d]! Highest scoring tiles: %s"
        print msg % (self.max_tilept, str(self.maxpt_tileset))

        adj_tile_points = {}

        for tile in self.maxpt_tileset:
            # For each adjacent tile, add points into the center
            for adjacent_tileid in self.adjacent_tile(tile):
                new_pts = self.tile_points[adjacent_tileid]
                if new_pts != 0:
                    msg = "Adding %d points from [%s](%d) to tile: %s(%d)"
                    print msg % (new_pts,
                                 city_tiles[adjacent_tileid],
                                 adjacent_tileid,
                                 city_tiles[tile],
                                 tile)
                    adj_tile_points[tile] = adj_tile_points.get(tile, 0)
                    adj_tile_points[tile] += new_pts

        for k, v in adj_tile_points.items():
            self.tile_points[k] += v

        max_tilept = 0
        self.maxpt_tileset = set()
        for i, v in enumerate(self.tile_points):
            if v >= max_tilept:
                max_tilept = v
                self.maxpt_tileset.clear()
            if max_tilept == v:
                self.maxpt_tileset.add(i)

        if len(self.maxpt_tileset) == 1:
            print "Tie breaking solution: %s" % str(self.maxpt_tileset)

