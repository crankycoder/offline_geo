#!/usr/bin/env python

import csv
import math
from scrambler import randint
from marisa_trie import RecordTrie
from matplotlib.path import Path

# Never change this unless you've thought about it 97 times.
# Then still never change it.
ZOOM_LEVEL = 18

class PNPoly(object):

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
            pts.append((lat, lon))

        codes = [Path.MOVETO] + [Path.LINETO] * (len(pts)-2) + [Path.CLOSEPOLY]
        self.matplot_path = Path(pts, codes)

    def contains(self, raw_lat, raw_lon):
        # Normalize the lat/lon to use only positive values
        lat = raw_lat + 90
        lon = raw_lon + 180
        return self.matplot_path.contains_point((lat, lon))


def compute_pnpoly_set(vertices):
    '''
    Filter input.csv (bssid, lat, lon) down to just
    the datapoints that lie within the polygon defined by
    vertices. Note that the polygon *must* be convex (like a
    rectangle).
    '''
    filter = PNPoly(vertices)
    with open('pnpoly_outside.csv', 'w') as fout_outsidepoly:
        out_pnpoly_writer = csv.writer(fout_outsidepoly)
        with open('pnpoly.csv', 'w') as fout:
            writer = csv.writer(fout)

            for (bssid, lat, lon) in csv.reader(open('input.csv')):
                if filter.contains(float(lat), float(lon)):
                    writer.writerow((bssid, lat, lon))
                else:
                    out_pnpoly_writer.writerow((bssid, lat, lon))


def pnpoly_to_tiles():
    result = set()
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


def obfuscate_tile_data(dupe_num):
    # First compute all unique tiles
    tile_gen = generate_ids(dupe_num)
    with open('obfuscated.csv', 'w') as fout:
        writer = csv.writer(fout)
        for i, row in enumerate(tile_gen):
            if i % 100000 == 0:
                print "Obfuscated %dk records" % (i / 1000)
            writer.writerow(row)
        print "Obfuscated %dk records" % (i / 1000)
    return dupe_num


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


def normalize_tilenumbers(in_x, in_y, z):
    """
    Slippy tilenames are specified as having a maximum X or Y tile
    number at 2^zoom-1.

    So zoom level 18 has a maximum tile number of:
    = 2^18-1
    = 262143
    """
    width = 2**z
    return in_y * width + in_x


def denormalize_tileid(tile_id, z):
    width = 2**z
    x = tile_id % width
    y = int(tile_id/width)
    return x, y


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


if __name__ == '__main__':
    # This set of points roughly contains the Metro toronto area
    toronto = [(43.754533, -79.631391),
               (43.855652, -79.170215),
               (43.585491, -79.541599),
               (43.585491, -79.170215)]

    newmarket = [(44.012517, -79.498160),  # SW
                 (44.067909, -79.512454),  # NW
                 (44.088582, -79.421825),  # NE
                 (44.031359, -79.409038)]  # SE
    v = toronto

    #compute_pnpoly_set(v)
    #pnpoly_to_tiles()
    #compute_unique_tileids(ZOOM_LEVEL)
    dupe_num = 100
    fmt = "<" + ("i" * dupe_num)

    #obfuscate_tile_data(dupe_num)
    #compute_tries(dupe_num, fmt, 'toronto.record_trie')

    test_offline_fix(fmt)
