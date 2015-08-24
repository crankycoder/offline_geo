import math


class AbstractLocationFixStrategy(object):

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

    def safe_city_tiles(self, x, y, city_tiles):
        try:
            return city_tiles[(x, y)]
        except KeyError:
            # This can happen if the adjacent tile is on the edge of a
            # city border
            return None

    def adjacent_tile(self, tile_id):
        city_tiles = self.locationFixer.city_tiles
        tx, ty = city_tiles[tile_id]

        # This shouldn't happen but it does.  Just skip this
        # problem for now and come back to it later.
        if (tx, ty) == (None, None):
            raise StopIteration()

        for (x, y) in [(tx-1, ty-1), (tx, ty-1), (tx+1, ty-1),
                       (tx-1, ty), (tx+1, ty), (tx-1, ty+1),
                       (tx, ty+1), (tx+1, ty+1)]:
            tmp_result = self.safe_city_tiles(x, y, city_tiles)
            if tmp_result is not None:
                yield tmp_result

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
                                  tuple(best_guess))


class SimpleTieBreaker(AbstractLocationFixStrategy):
    def __init__(self, locationFixer, prevStep):
        super(SimpleTieBreaker, self).__init__(locationFixer,
                                               prevStep)

    def execute(self, locationSolution):
        # Make a copy of previous data sets
        tile_points = locationSolution.get_soln_data(BasicLocationFix)

        # We have to solve a tie breaker
        assert len(tile_points) == 65535

        max_pts_in_tile = max(tile_points)
        if max_pts_in_tile == 0:
            return

        working_tileset = set()
        for tile_id, tile_pts in enumerate(tile_points):
            if tile_pts == max_pts_in_tile:
                working_tileset.add(tile_id)

        if len(working_tileset) <= 1:
            return

        """
        msg = "Tie breaker with score: [%d]! Highest scoring tiles: %s"
        print msg % (max_pts_in_tile, str(working_tileset))
        """

        adj_tile_points = {}

        for tile in working_tileset:
            # For each adjacent tile, add points into the center
            for adjacent_tileid in self.adjacent_tile(tile):
                new_pts = tile_points[adjacent_tileid]
                if new_pts != 0:
                    """
                    city_tiles = self.locationFixer.city_tiles
                    msg = "Adding %d points from [%s](%d) to tile: %s(%d)"
                    msg_out = msg % (new_pts,
                                 city_tiles[adjacent_tileid],
                                 adjacent_tileid,
                                 city_tiles[tile],
                                 tile)
                    print msg_out
                    """

                    adj_tile_points[tile] = adj_tile_points.get(tile, 0)
                    adj_tile_points[tile] += new_pts

        for k, v in adj_tile_points.items():
            tile_points[k] += v

        max_tilept = 0
        maxpt_tileset = set()
        for i, v in enumerate(tile_points):
            if v >= max_tilept:
                max_tilept = v
                maxpt_tileset.clear()
            if max_tilept == v:
                maxpt_tileset.add(i)

        locationSolution.add_soln(self.__class__,
                                  tile_points,
                                  tuple(maxpt_tileset))
