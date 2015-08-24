import copy
import math


class AbstractLocationFixStrategy(object):

    # This is a duplicate of what is in SmartTile. Need to fix that.
    ZOOM_LEVEL = 18

    def __init__(self, locationFixer, prevStep, locationSolution):
        self.locationFixer = locationFixer
        self.prevStep = prevStep
        self.locationSolution = locationSolution

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
    to find a single point where trie lookups yield a single
    maximum.
    """
    def __init__(self, locationFixer, prevStep, locationSolution):
        super(BasicLocationFix, self).__init__(locationFixer, prevStep, locationSolution)

        # Copy this into strategies that are further down the chain
        self.tile_points = [0] * 65535
        self.maxpt_tileset = set()

    def execute(self):
        # This is always the first fix, we don't care about any prior
        # possible solutions

        bssids = self.locationSolution.bssids
        trie = self.locationSolution.trie

        for bssid in bssids:
            matchContainer = trie.get(bssid)
            if matchContainer is None:
                continue
            for pt in matchContainer[0]:
                self.tile_points[pt] += 1

        max_tilept = 0
        for i, v in enumerate(self.tile_points):
            if v >= max_tilept:
                max_tilept = v
                self.maxpt_tileset.clear()
            if v == max_tilept:
                self.maxpt_tileset.add(i)

        if max_tilept <= 1:
            return

        if len(self.maxpt_tileset) == 1:
            self.locationSolution.fix_tileset = self.maxpt_tileset


class SimpleTieBreaker(AbstractLocationFixStrategy):
    def __init__(self, locationFixer, prevStep, locationSolution):
        super(SimpleTieBreaker, self).__init__(locationFixer, prevStep, locationSolution)

        # Make a copy of previous data sets
        self.tile_points = [p for p in prevStep.tile_points]
        self.maxpt_tileset = copy.copy(prevStep.maxpt_tileset)

        self.max_tilept = max(self.tile_points)

        # Handy dandy shortcut
        self.city_tiles = locationFixer.city_tiles

    def execute(self):
        # We have to solve a tie breaker
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
                                 self.city_tiles[adjacent_tileid],
                                 adjacent_tileid,
                                 self.city_tiles[tile],
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


class AdjacentTileTieBreaker(AbstractLocationFixStrategy):
    """
    By default, the lat/lon we return is simply the center of
    an OSM tile @ zoom 18.

    For a given fix, we may actually see BSSID radios from adjacent
    tiles.

    Note that this strategy should be used *last* as it perturbs the
    lat/lon from the center of a tile.
    """
    def __init__(self, locationFixer, prevStep, locationSolution):
        super(AdjacentTileTieBreaker, self).__init__(locationFixer, prevStep, locationSolution)

        # Make a copy of previous data sets
        self.tile_points = [p for p in prevStep.tile_points]
        self.maxpt_tileset = copy.copy(prevStep.maxpt_tileset)
        self.max_tilept = max(self.maxpt_tileset)

    def execute(self):
        '''
        '''
        if len(self.maxpt_tileset) == 1:
            # No need to do anymore work here
            return

        msg = "Multiple solutions: "
        print msg + self.maxpt_tileset
        tiebreaking_set = set()
        maxpt_tilelist = list(self.maxpt_tileset)

        # This is a bit tricky - we extracting the subset of tiles
        # from maxpt_tilelist which are adjacent to each other.  If
        # multiple adajacent tiles have tying high scores, then the
        # true location is probably some average of those scores.

        for i, pt in enumerate(maxpt_tilelist):
            adjacent_tilelist = list(self.adjacent_tile(pt))
            s1 = set(adjacent_tilelist)
            s2 = set(maxpt_tilelist[i+1:])
            adjacent_tileset = s1 & s2
            if adjacent_tileset:
                tiebreaking_set.add(pt)
                tiebreaking_set = tiebreaking_set.union(pt)

        final_lat = final_lon = 0
        for tie in tiebreaking_set:
            tx, ty = self.city_tiles[tie]
            tmp_lat, tmp_lon = self.num2deg(tx, ty, self.ZOOM_LEVEL)
            final_lat += (tmp_lat * 1.0/len(tiebreaking_set))
            final_lon += (tmp_lon * 1.0/len(tiebreaking_set))

        self.locationSolution.fix_lat_lon = (final_lat, final_lon)

        msg = "Multiple solutions converging on : "
        print msg + self.locationSolution.fix_lat_lon

