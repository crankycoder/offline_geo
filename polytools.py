from matplotlib.path import Path


class PNPoly(object):

    _min_norm_lat = None
    _min_norm_lon = None
    _max_norm_lat = None
    _max_norm_lon = None

    def __init__(self, in_pts):
        '''
        We need to compute the dataset for metro toronto by taking
        the set of 4 points and computing the areas where BSSIDs are
        valid.
        '''
        # Normalize lat/lon to only positive values
        pts = []
        for pt in in_pts:
            lat, lon = pt
            lat += 90
            lon += 180

            if self._min_norm_lat is None:
                self._min_norm_lat = lat
            if self._min_norm_lat > lat:
                self._min_norm_lat = lat

            if self._min_norm_lon is None:
                self._min_norm_lon = lon
            if self._min_norm_lon > lon:
                self._min_norm_lon = lon

            if self._max_norm_lat is None:
                self._max_norm_lat = lat
            if self._max_norm_lat < lat:
                self._max_norm_lat = lat

            if self._max_norm_lon is None:
                self._max_norm_lon = lon
            if self._max_norm_lon < lon:
                self._max_norm_lon = lon

            pts.append((lat, lon))

        codes = [Path.MOVETO] + [Path.LINETO] * (len(pts)-2) + [Path.CLOSEPOLY]
        self.matplot_path = Path(pts, codes)

    def bounding_box(self):
        '''
        Return the bounding box min/max lat long pair that defines the
        outside corners of this polygon.
        '''
        return (self._min_norm_lat-90, self._min_norm_lon-180), \
               (self._max_norm_lat-90, self._max_norm_lon-180)

    def contains(self, raw_lat, raw_lon):
        # Normalize the lat/lon to use only positive values
        lat = raw_lat + 90
        lon = raw_lon + 180
        return self.matplot_path.contains_point((lat, lon))
