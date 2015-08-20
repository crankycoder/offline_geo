#!/usr/bin/env python

from devrand import randint
from fileutil import file_len
from geojson import load_geojson
from marisa_trie import RecordTrie
from matplotlib.path import Path
from tiler import generate_stream
import csv
import math
import os
import os.path


# Never change this unless you've thought about it 97 times.
# Then still never change it.
ZOOM_LEVEL = 18


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


class OrderedCityTiles(object):
    '''
    This class provides acts like an order preserving
    hashtable.

    '''
    def __init__(self, load_fromdisk=False):
        self._hash = {}
        self._hash_list = []
        if load_fromdisk:
            with open('ordered_city.csv') as fin:
                reader = csv.reader(fin)
                for row in reader:
                    t = (int(row[0].strip()), int(row[1].strip()))
                    self._hash_list.append(t)
                    self._hash[t] = len(self._hash_list) - 1

    def __contains__(self, k):
        if isinstance(k, tuple):
            # Return the integer tile_id
            return k in self._hash
        raise RuntimeError("Invalid key: %s" % k)

    def finalize(self):
        # Sort the list of tiles in place and fix up all the
        # hash keys

        self._hash_list.sort()
        for i, k in enumerate(self._hash_list):
            self._hash[k] = i

        with open('ordered_city.csv', 'w') as fout:
            writer = csv.writer(fout)
            for item in self._hash_list:
                writer.writerow(item)

    def __getitem__(self, k):
        '''
        Enable fetching the item from the list interface
        '''
        # For indexed fetches into the list
        if isinstance(k, int):
            # Return the (tilex, tiley) tuple
            try:
                return self._hash_list[k]
            except:
                import pdb
                pdb.set_trace()
                print k
                pass
        if isinstance(k, tuple):
            # Return the integer tile_id
            return self._hash[k]

        raise RuntimeError("Invalid key: %s" % k)

    def put(self, k):
        '''
        k must be the (tilex, tiley) co-ordinates where both tilex and
        tiley are integers.
        '''
        assert isinstance(k, tuple)
        assert len(k) == 2
        assert isinstance(k[0], int)
        assert isinstance(k[1], int)
        assert k not in self._hash

        self._hash_list.append(k)
        self._hash[k] = len(self._hash_list)-1

    def size(self):
        return len(self._hash_list)


class PrivateLocations(object):
    '''
    This class encapsulates everything needed to compute a record trie
    for a given city.

    To use this class,

    '''
    def __init__(self):
        self.dupe_num = 3

        # Always always always write big endian/network byte order
        self.fmt = ">" + ("i" * self.dupe_num)

        # This is the file with the geojson encoded shapefile
        # describing the outer boundary of the city scape.
        # This boundary may include bodies of water. We don't really
        # care.
        self.geojson_fname = 'input.geojson'

        self.pnpoly_outside = 'pnpoly_outside.csv'
        self.pnpoly_inside = 'pnpoly.csv'

        # This is a CSV file with BSSID, lat, lon
        self.bssid_input = 'input.csv'

        # This is the pnpoly_inside file but the lat/lon have been
        # converted into tile numbers
        self.pnpoly_tiles = 'pnpoly_tiles.csv'

        # This file contains the slippy tile coordinates and zoom
        # level for all tiles within the city shapefile boundaries.
        # CSV file is formatted with (x, y, zoom level) using slippy
        # tile zoom level 18 (or whatever ZOOM_LEVEL) is defined as.
        self.incity_tiles = 'incity_tiles.csv'

        self.sobol_seq_csv = 'sobol_seq.csv'

        self.sobol_seed = 1233441294

        self.bssid_sobol_idx_csv = 'bssid_sobol_idx.csv'

        self.bssid_sobol_obfuscated_csv = 'obfuscated.csv'

        self.output_trie_fname = 'toronto.record_trie'

    def _compute_pnpoly_set(self):
        '''
        Filter input.csv (bssid, lat, lon) down to just
        the datapoints that lie within the polygon defined by
        vertices.
        '''

        # Load a polygon for the outer edge of the cityscape
        v = load_geojson(self.geojson_fname)
        self.polygon_filter = PNPoly(v)

        # This splits all lat/lon points for BSSIDs into
        # either within the polygon or outside the city polygon.

        # TODO: This part is computationally expensive.
        # This loop can be parallelized using multiprocessing
        # and using a multiprocessing.Queue to collect data for
        # each of of pnpoly_in and pnpoly_out datasets.

        with open(self.pnpoly_outside, 'w') as fout_outsidepoly:
            out_pnpoly_writer = csv.writer(fout_outsidepoly)
            with open(self.pnpoly_inside, 'w') as fout:
                in_pnpoly_writer = csv.writer(fout)
                for (bssid, lat, lon) in csv.reader(open(self.bssid_input)):
                    try:
                        if self.polygon_filter.contains(float(lat), float(lon)):
                            in_pnpoly_writer.writerow((bssid, lat, lon))
                        else:
                            out_pnpoly_writer.writerow((bssid, lat, lon))
                    except:
                        print "Can't handle: " + (lat, lon)

    def _pnpoly_to_tiles(self):
        # TODO: this can be optimised using multiprocessing
        # and adding a multiprocessing.Queue to collect conversions
        # of lat/lon to tile_id and writing out results into the
        # output file.
        with open(self.pnpoly_tiles, 'w') as f_out:
            writer = csv.writer(f_out)
            with open(self.pnpoly_inside, 'r') as f_in:
                for i, row in enumerate(csv.reader(f_in)):
                    bssid = row[0]
                    lat = float(row[1])
                    lon = float(row[2])
                    tile_x, tile_y = self._deg2num(lat, lon, ZOOM_LEVEL)
                    entry = (bssid, tile_x, tile_y)
                    entry = (bssid, tile_x, tile_y, ZOOM_LEVEL)
                    writer.writerow(entry)

    def _deg2num(self, lat_deg, lon_deg, zoom):
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

    def _compute_all_tiles_in_polygon(self):
        '''
        Compute the bounding box for the polygon containing the
        city.

        Compute the tile ID at each of the corners

        Interpolate between 4 corners to get the list of all tiles in
        the bounding box.

        We then take each of the tiles in the bounding
        box and compute the lat/lon of the center of the tile to
        determine if the tile is 'in' the city boundaries.

        The final set of tile information is written to a CSV file
        defined in self.incity_tiles with the following format:

        x, y, zoom level

        Where x, y and z are defined with slippy tile zoom level 18.
        '''
        p1, p2 = self.polygon_filter.bounding_box()

        tx0, ty0 = self._deg2num(p1[0], p1[1], ZOOM_LEVEL)
        tx1, ty1 = self._deg2num(p2[0], p2[1], ZOOM_LEVEL)

        # Now iterate over tx0 to tx1 at ty0
        i = 0

        tx_tiles = sorted([tx0, tx1])
        ty_tiles = sorted([ty0, ty1])
        total_tiles = (tx_tiles[1]-tx_tiles[0]+1) * (ty_tiles[1]-ty_tiles[0]+1)

        # TODO: this can also be reworked using multiprocessing and a
        # bunch of workers and a queue to handle writes to
        # the disk.
        with open(self.incity_tiles, 'w') as fout:
            writer = csv.writer(fout)
            for x in range(*tx_tiles):
                for y in range(*ty_tiles):
                    tile_pt = self._num2deg(x, y, ZOOM_LEVEL)
                    if self.polygon_filter.contains(tile_pt[0], tile_pt[1]):
                        writer.writerow((x, y, ZOOM_LEVEL))
                    i += 1
                    if i % 100 == 0:
                        msg = "Processed %d out of %d tiles in polygon"
                        print msg % (i, total_tiles)

    def _num2deg(self, xtile, ytile, zoom):
        n = 2.0 ** zoom
        lon_deg = xtile / n * 360.0 - 180.0
        lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * ytile / n)))
        lat_deg = math.degrees(lat_rad)
        return (lat_deg, lon_deg)

    def _generate_bssid_sobol_keys(self):
        # Read in pnpoly_tiles.csv
        # and write out `bssid_sobol_idx.csv` CSV file
        # with BSSID -> index into sobol sequence CSV file
        #
        # Note that the bssid_sobol_idx.csv file will have
        # random numbers assigned into it so it's important
        # to keep the bssid_sobol_idx.csv file around for the
        # next iteration of the tile generation.
        max_idx = self._generate_sobol_csv()

        if os.path.isfile(self.bssid_sobol_idx_csv):
            print "Reusing the existing %s file" % self.bssid_sobol_idx_csv
            return

        with open(self.bssid_sobol_idx_csv, 'w') as file_out:
            writer = csv.writer(file_out)
            with open(self.pnpoly_tiles) as file_in:
                reader = csv.reader(file_in)
                for row in reader:
                    (bssid, tilex, tiley, zlevel) = row
                    sobol_idx = randint(0, max_idx-1)
                    r = (bssid, tilex, tiley, zlevel, sobol_idx)
                    writer.writerow(r)

    def _generate_sobol_csv(self):
        """
        generate a sobol sequence distributed over a range equal
        to the the total length of incity_tiles.csv.  Sequence length
        should be 10x the distribution width. write this out to
        sobol_seq.csv
        """
        with open(self.sobol_seq_csv, 'w') as fout:
            generate_stream(fout,
                            seed=self.sobol_seed,
                            max_tilenum=self.total_city_tiles)
        return file_len(self.sobol_seq_csv)

    def _obfuscate_tile_data(self):
        # TODO: this stage should be pluggable
        # Consider rewriting this as a generator
        # so that we can stream data into the file output.

        '''
        1. load in the sobol sequence as a circular list.
        2. Read in the sha256_bssid_sobol_idx.csv file to get
           a (hashed bssid, tilex, tiley, zlevel, sobol idx)
        3. keep the sobol idx as set it as the base index
        4. read in dupe_num items from the circular list of sobol numbers
           starting at the base index.

        This is the tricky part.  We need to transform the sobol delta
        into an offset so that we can 'rebase' the sobol sequence onto
        the actual location of the tile.
        5. for each sobol number:
                a. delta = (new sobol - sobol base)
                b. new_tile = sobol_seq[(base_idx+delta) % len(sobol_seq)]
        '''

        print "Obscuring data now..."

        sobol_seq = []
        with open(self.sobol_seq_csv) as sobol_in:
            reader = csv.reader(sobol_in)
            for sobol_int, seed in reader:
                sobol_seq.append((int(sobol_int), seed))

        ordered_city_tiles = self._load_city()

        obfuscated_count = 0
        with open(self.bssid_sobol_obfuscated_csv, 'w') as fout:
            writer = csv.writer(fout)
            with open(self.bssid_sobol_idx_csv) as file_in:
                reader = csv.reader(file_in)
                for row_idx, row in enumerate(reader):
                    (bssid, tile_x, tile_y, zlevel, sobol_key) = row
                    (bssid,
                     tile_x,
                     tile_y,
                     zlevel,
                     sobol_key) = (bssid,
                                   int(tile_x),
                                   int(tile_y),
                                   int(zlevel),
                                   int(sobol_key))

                    # Ok, we need to get the key into the ordered tile
                    # list.
                    orig_tile_key = (tile_x, tile_y)
                    orig_tile_idx = ordered_city_tiles[orig_tile_key]

                    # Base sobol tile
                    sobol_base_tile_id, _ignored = sobol_seq[sobol_key]

                    # We need the delta so that we can transform the sobol
                    # tile offsets and 'rebase' them onto the original
                    # tile tile index

                    tile_delta = orig_tile_idx - sobol_base_tile_id

                    for i in range(self.dupe_num):
                        (next_sobol_tile_id, next_sobol_seed) = sobol_seq[(sobol_key+i) % len(sobol_seq)]

                        # Note that for i = 0, this will be the original
                        # tile id
                        norm_tile_id = (tile_delta + next_sobol_tile_id) % ordered_city_tiles.size()

                        norm_tile_x, norm_tile_y, = ordered_city_tiles[norm_tile_id]
                        r = (bssid, norm_tile_x, norm_tile_y, zlevel)

                        writer.writerow(r)
                        obfuscated_count += 1
                        if obfuscated_count % 10000 == 0:
                            print "Wrote %d rows of obfuscated data" % obfuscated_count

    def _load_city(self):
        """
        TODO: this is called a couple times. it could use caching
        """
        ordered_city_tiles = OrderedCityTiles()
        with open(self.incity_tiles) as file_in:
            for row in csv.reader(file_in):
                (tile_x, tile_y, zlevel) = row
                ordered_city_tiles.put((int(tile_x), int(tile_y)))

        with open(self.pnpoly_tiles) as file_in:
            for row in csv.reader(file_in):
                (bssid, tile_x, tile_y, zlevel) = row
                k = (int(tile_x), int(tile_y))
                if k not in ordered_city_tiles:
                    ordered_city_tiles.put(k)
        ordered_city_tiles.finalize()
        return ordered_city_tiles

    def _compute_tries(self):
        ordered_city_tiles = self._load_city()

        dataset = {}
        with open(self.bssid_sobol_obfuscated_csv) as file_in:
            reader = csv.reader(file_in)
            last_bssid = None
            bssid_locations = None
            for row in reader:
                bssid, tile_x, tile_y, zlevel = row

                bssid = unicode(bssid)
                tile_key = (int(tile_x), int(tile_y))
                tile_id = ordered_city_tiles[tile_key]

                if bssid != last_bssid:
                    if last_bssid is not None:
                        # push bssid-locations into dataset
                        dataset[last_bssid] = bssid_locations
                    bssid_locations = []
                    if len(dataset) % 10000 == 0:
                        print "Constructing trie with record: %d" % len(dataset)
                bssid_locations.append(tile_id)
                last_bssid = bssid

            # Copy the last batch into the dataset
            if bssid_locations:
                dataset[last_bssid] = bssid_locations
                bssid_locations = []

        print "Constructing trie"
        trie = RecordTrie(self.fmt, dataset.items())
        trie.save(self.output_trie_fname)
        print "trie saved!"

    def generate_recordtrie(self):
        # This set of points roughly contains the Metro toronto area
        self._compute_pnpoly_set()
        self._pnpoly_to_tiles()
        self._compute_all_tiles_in_polygon()

        self.total_city_tiles = file_len(self.incity_tiles)
        self._generate_bssid_sobol_keys()

        self._obfuscate_tile_data()

        self._compute_tries()


def main():

    """
    TODO: we need to be able to setup
    links to varying input files for each city.

    In particular, we need to set the :

    * city name
    * bssid_sobol_idx.csv file needs to be namespaced to just the city

    """
    pl = PrivateLocations()
    pl.generate_recordtrie()

if __name__ == '__main__':
    main()
