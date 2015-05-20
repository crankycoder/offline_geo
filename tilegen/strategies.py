import copy


class AbstractLocationFixStrategy(object):
    def __init__(self, locationFixer, prevStep, locationSolution):
        self.locationFixer = locationFixer
        self.prevStep = prevStep
        self.locationSolution = locationSolution

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
        super(locationFixer, prevStep, locationSolution)

        # Copy this into strategies that are further down the chain
        self.tile_points = [0] * 65535
        self.maxpt_tileset = set()

    def execute(self):
        bssids = locationSolution.bssids
        trie = locationSolution.trie

        last_result = None
        for bssid in bssids:
            matchContainer = trie.get(bssid)
            if matchContainer is None:
                print "BSSID [%s] is not in the dataset" % bssid
                continue
            for pt in matchContainer[0]:
                self.tile_points[pt] += 1


        max_tilept = 0
        for i, v in enumerate(tile_points):
            if v >= max_tilept:
                max_tilept = v
                self.maxpt_tileset.clear()
            if v == max_tilept:
                self.maxpt_tileset.add(i)

        if max_tilept <= 1:
            print "No tries agreed on a solution"
            return

        if len(self.maxpt_tileset) == 1:
            print "Unique solution found: " + str(self.maxpt_tileset)
            locationSolution.fix_tileset = self.maxpt_tileset

class SimpleTieBreaker():
    def __init__(self, locationFixer, prevStep, locationSolution):
        super(locationFixer, prevStep, locationSolution)

        # Make a copy of the tilepoints
        self.tile_points = [p for p in prevStep.tile_points]

        self.maxpt_tileset = copy.copy(prevStep.maxpt_tileset)
        self.max_tilept = max(self.maxpt_tileset)

    def adjacent_tile(self, tile_id):
        city_tiles = self.locationFixer.city_tiles
        tx, ty = city_tiles[tile_id]

        yield city_tiles[(tx-1, ty-1)]
        yield city_tiles[(tx  , ty-1)]
        yield city_tiles[(tx+1, ty-1)]

        yield city_tiles[(tx-1, ty)]
        yield city_tiles[(tx+1, ty)]

        yield city_tiles[(tx-1, ty+1)]
        yield city_tiles[(tx  , ty+1)]
        yield city_tiles[(tx+1, ty+1)]

    def execute(self):
        # We have to solve a tie breaker
        # Square the points for the max point array
        for pt in self.maxpt_tileset:
            self.tile_points[pt] *= self.tile_points[pt]

        msg = "Tie breaker with score: [%d]! Highest scoring tiles: %s"
        print msg % (self.max_tilept, str(self.maxpt_tileset))
        print "Adjusted score is: %d" % (self.max_tilept*self.max_tilept)

        adj_tile_points = {}

        for tile in self.maxpt_tileset:
            # For each adjacent tile, add points into the center
            for adjacent_tileid in self.adjacent_tile(tile):
                new_pts = self.tile_points[adjacent_tileid]

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
        for i, v in enumerate(tile_points):
            if v >= max_tilept:
                max_tilept = v
                self.maxpt_tileset.clear()
            if max_tilept == v:
                self.maxpt_tileset.add(i)

        if len(self.maxpt_tileset) == 1:
            print "Tie breaking solution: %s" % str(self.maxpt_tileset)

