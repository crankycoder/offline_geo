#!/usr/bin/env python

import sys
import csv
import math
from devrand import randint
from marisa_trie import RecordTrie
from matplotlib.path import Path
from fileutil import file_len
from geojson import load_path

# bcrypt isn't used as it's *far* too slow to obfuscate 
# the BSSID data.  In addition, we don't really get the 
# security of bcrypt anyway as we need to use a single
# salt per tile set.
# import bcrypt

from hashlib import sha256
import time

# TODO: this needs to get pulled out into a config file once we know
# this methodology works.
SALT = '$2a$12$t.BjcCgX.UKVpHKfWnMM6u'

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


def compute_pnpoly_set(polygon_filter):
    '''
    Filter input.csv (bssid, lat, lon) down to just
    the datapoints that lie within the polygon defined by
    vertices. Note that the polygon *must* be convex (like a
    rectangle).
    '''
    # TODO: need to sort the input.csv file first
    with open('pnpoly_outside.csv', 'w') as fout_outsidepoly:
        out_pnpoly_writer = csv.writer(fout_outsidepoly)
        with open('pnpoly.csv', 'w') as fout:
            writer = csv.writer(fout)
            for i, (bssid, lat, lon) in enumerate(csv.reader(open('input.csv'))):
                if i % 10 == 0:
                    print "Processed %d records" % i
                try:
                    if polygon_filter.contains(float(lat), float(lon)):
                        writer.writerow((bssid, lat, lon))
                    else:
                        out_pnpoly_writer.writerow((bssid, lat, lon))
                except:
                    print "Can't handle: " + (lat, lon)


def pnpoly_to_tiles():
    result = set()
    # This writes out an ordered
    with open('pnpoly_tiles.csv', 'w') as f_out:
        writer = csv.writer(f_out)
        with open('pnpoly.csv', 'r') as f_in:
            for i, row in enumerate(csv.reader(f_in)):
                bssid = row[0]
                lat = float(row[1])
                lon = float(row[2])
                tile_x, tile_y = deg2num(lat, lon, ZOOM_LEVEL)
                entry = (bssid, tile_x, tile_y)
                result.add(entry)
                entry = (bssid, tile_x, tile_y, ZOOM_LEVEL)
                writer.writerow(entry)
    return result


def num2deg(xtile, ytile, zoom):
    n = 2.0 ** zoom
    lon_deg = xtile / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * ytile / n)))
    lat_deg = math.degrees(lat_rad)
    return (lat_deg, lon_deg)


def deg2num(lat_deg, lon_deg, zoom):
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


def compute_unique_tileids(zoom):
    u_tiles = set()
    for (bssid, tx, ty, ignore_z) in csv.reader(open('pnpoly_tiles.csv')):
        u_tiles.add((int(tx), int(ty)))
    # Just compute the list of (tilex, tiley) tuples
    u_tiles = list(u_tiles)
    MAX_IDX = len(u_tiles)-1

    # Note that this is unstable as the unique set of tiles with BSSID
    # will grow over time.
    # We want a unique set of tiles written out so that we can remap
    # slippy tiles to just the set of tiles that actually exist.
    # Let's say we want to have a map of all tiles.
    # At zoom level 17, each tile is ~305m x 305m.
    # At zoom level 18, each tile is ~152m x 152m.
    # So with Z17, we get sqrt(64k)*305 = 610km on each side of the
    # map.
    # With Z18, we get sqrt(64k)*152 = 38.9km on each side of the map.
    # For reference, toronto is ~20km x 38.6km.
    # This means we can properly encode all of toronto within ~70% of
    # the 16 bits. Lots of extra space!
    u_tiles = sorted(u_tiles)
    with open('unique_tile_ids_z%d.csv' % zoom, 'w') as fout:
        writer = csv.writer(fout)
        for t in u_tiles:
            writer.writerow(t)


def generate_ids(batch_size):
    """
    Compute all unique tiles.

    This is no longer useful, but I've kept it here anyway as it's an
    interesting metric.  It lets us see the proportion of tiles we
    have with real measurements.
    """

    u_tiles = set()
    for (bssid, tx, ty, ignore_z) in csv.reader(open('pnpoly_tiles.csv')):
        u_tiles.add((int(tx), int(ty)))

    # Just compute the list of (tilex, tiley) tuples
    u_tiles = list(u_tiles)
    MAX_IDX = len(u_tiles)-1

    for (real_bssid, tx, ty, ignore_z) in csv.reader(open('pnpoly_tiles.csv')):
        real_tile_x = int(tx)
        real_tile_y = int(ty)

        MIDDLE = randint(0, batch_size-1)

        randomized_set = set()

        while len(randomized_set) < MIDDLE:
            x, y = u_tiles[randint(0, MAX_IDX)]
            randomized_set.add((real_bssid, x, y))

        # Return the real tile location
        randomized_set.add((real_bssid, real_tile_x, real_tile_y))

        while len(randomized_set) < (batch_size):
            x, y = u_tiles[randint(0, MAX_IDX)]
            randomized_set.add((real_bssid, x, y))

        assert len(randomized_set) == batch_size
        for k in randomized_set:
            yield k


def compute_all_tiles_in_polygon(polygon):
    '''
    This computes an ordered list of tiles at the global zoomlevel.

    We take the geojson polygon shape and create a bounding box.

    Compute the tile ID at each of the corners.

    Interpolate between 4 corners to get a superset of all possible 
    tiles.

    For each tile, we need to convert back into lat/long and compare
    against PNPoly.
    '''
    p1, p2 = polygon.bounding_box()
    # TODO: compute tiles at each corner
    # TODO: run nested loop over the whole box to determine which
    # tiles are in 

    tx0, ty0 = deg2num(p1[0], p1[1], ZOOM_LEVEL)
    tx1, ty1 = deg2num(p2[0], p2[1], ZOOM_LEVEL)

    # Now iterate over tx0 to tx1 at ty0
    i = 0


    tiles_in_poly = []
    tx_tiles = sorted([tx0, tx1])
    ty_tiles = sorted([ty0, ty1])
    total_tiles = (tx_tiles[1]-tx_tiles[0]+1) * (ty_tiles[1]-ty_tiles[0]+1)

    with open('incity_tiles.csv','w') as fout:
        writer = csv.writer(fout)
        for x in range(*tx_tiles):
            for y in range(*ty_tiles):
                tile_pt = num2deg(x, y, ZOOM_LEVEL)
                if polygon.contains(tile_pt[0], tile_pt[1]):
                    writer.writerow((x, y, ZOOM_LEVEL))
                i += 1
                if i % 100 == 0:
                    print "Processed %d out of %d tiles in polygon" % (i, total_tiles)

    # TODO: i manually did `sort incity_tiles.csv > # # incity_tiles.csv.sorted`



def obfuscate_tile_data(dupe_num):

    # TODO: load the sobol sequence file 
    # and load it into a circular buffer
    TOTAL_SOBOL_LENGTH = file_len('sobol_seq.csv')

    sobol_seq = []
    with open('sobol_seq.csv') as sobol_in:
        reader = csv.reader(sobol_in)
        for rand_int, seed in reader:
            sobol_seq.append((randint, seed))

    # TODO: read in pnpoly
    with open('obfuscated.csv', 'w') as fout:
        with open('sha256_bssid_sobol_idx.csv') as file_in:
            reader = csv.reader(file_in)
            for row in reader:
                (sha_bssid, tile_x, tile_y, zlevel, sobol_key) = row
                sha_bssid_bytes = sha_bssid.decode("hex")
                # Ok, no we read off the 'dupe_num' number of keys
                # from the sobol sequence file

                # Base sobol tile 
                sobol_base_tileid = sobol_seq[sobol_key]
                for idx in range(int(sobol_offset), int(sobol_offset) + dupe_num):
                    offset_tile_id = sobol_seq[idx % TOTAL_SOBOL_LENGTH]
                    sobol_offset = offset_tile_id - sobol_base_tile_id



def compute_tries(dupe_num, fmt, output_fname):
    tile_map = {}
    with open('unique_tile_ids_z%d.csv' % ZOOM_LEVEL, 'r') as fin:
        reader = csv.reader(fin)
        for i, (tx, ty) in enumerate(reader):
            tile_map[(int(tx), int(ty))] = i

    dataset = {}
    with open('obfuscated.csv') as file_in:
        reader = csv.reader(file_in)
        last_bssid = None
        bssid_locations = None
        for row in reader:
            bssid, x, y = row
            bssid = unicode(bssid)
            if bssid != last_bssid:
                if last_bssid is not None:
                    # push bssid-locations into dataset
                    dataset[last_bssid] = bssid_locations  # NOQA
                bssid_locations = []
                if len(dataset) % 10000 == 0:
                    print "Writing obfuscated record: %d" % len(dataset)
            bssid_locations.append(tile_map[(int(x), int(y))])
            last_bssid = bssid
    trie = RecordTrie("<" + ("I" * dupe_num), dataset.items())
    trie.save(output_fname)
    print "obfuscated.csv saved!"


def test_offline_fix(fmt):
    # verify that any three BSSIDs in the block should generate a
    # valid hit.

    # These BSSIDs are visible from the Moz Toronto office.
    bssids = ['ccb255dd9fbe',
              '68b6fc3fbe19',
              '9094e439de3c',
              'bc140152c7da',
              '7444012ed618']

    last_result = None
    t = RecordTrie(fmt).mmap('toronto.record_trie')
    for i in range(len(bssids)-2):
        for j in range(i+1, len(bssids)-1):
            for k in range(j+1, len(bssids)):
                cur_results = None
                for x in bssids[i], bssids[j], bssids[k]:
                    tmpMatches = t.get(x)
                    if tmpMatches is not None and tmpMatches != []:
                        if cur_results is None:
                            cur_results = set(*tmpMatches)
                        else:
                            cur_results = cur_results.intersection(set(*tmpMatches))
                if cur_results is None or len(cur_results) <> 1:
                    print "Can't get fix with: %s %s %s" % (
                            bssids[i],
                            bssids[j],
                            bssids[k],
                            )
                    print "Bad result size: %d" % len(cur_results)
                    continue
                assert 1151 in cur_results
                last_result = cur_results
                print bssids[i], bssids[j], bssids[k] + " is ok"
    print "Final results: " + str(last_result)


def hash_bssids():
    '''
    this takes in the bssid_sobol_idx.csv file and hashes all BSSIDs
    using sha256 to obscure what the original BSSID actually is.
    '''
    FILE_LEN = file_len('bssid_sobol_idx.csv')
    with open('bssid_sobol_idx.csv') as file_in:
        with open('sha256_bssid_sobol_idx.csv', 'w') as file_out:
            writer = csv.writer(file_out)
            start = time.time()
            for i, (bssid, tile_x, tile_y, z_level, sobol_idx) in enumerate(csv.reader(file_in)):
                h = sha256(SALT + bssid)
                hash_bssid = h.hexdigest()
                if i % 5 == 0 and i != 0:
                    now = time.time()
                    rate = i/(now-start)
                    msg = "Hashed %d BSSID. Rate is %0.3f BSSID/sec.  %0.2f seconds to go." 
                    print msg % (i, rate, (FILE_LEN-i)/rate)
                t = hash_bssid, tile_x, tile_y, z_level, sobol_idx
                writer.writerow(t)


if __name__ == '__main__':
    # This set of points roughly contains the Metro toronto area
    v = load_path('toronto.geojson')
    polygon = PNPoly(v)

    #compute_pnpoly_set(poly)
    #pnpoly_to_tiles()
    compute_all_tiles_in_polygon(polygon)

    dupe_num = 100
    fmt = "<" + ("i" * dupe_num)

    #hash_bssids()
    #obfuscate_tile_data(dupe_num)
    #compute_tries(dupe_num, fmt, 'toronto.record_trie')
    #test_offline_fix(fmt)
