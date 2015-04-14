#!/usr/bin/env python

import csv
import math
from scrambler import randint
from marisa_trie import RecordTrie

# Typical tile size at zoom 17
# http://c.tile.openstreetmap.org/17/36629/47838.png
ZOOM_LEVEL = 17


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
            pt.append((lat, lon))

        self.vertx = [pt[1] for pt in pts]
        self.verty = [pt[0] for pt in pts]

    def contains(self, raw_lat, raw_lon):
        # Normalize the lat/lon to use only positive values
        lat = raw_lat + 90
        lon = raw_lon + 180

        nvert = len(self.vertx)
        c = False
        i = 0
        j = nvert-1
        while (i < nvert):
            if (((self.verty[i] > lat) != (self.verty[j] > lat)) and
               (lon < (self.vertx[j] - self.vertx[i]) *
               (lat - self.verty[i]) /
               (self.verty[j]-self.verty[i]) + self.vertx[i])):
                c = not(c)
            i += 1
            j = i
        return c


def compute_pnpoly_set(vertices):
    '''
    Filter input.csv (bssid, lat, lon) down to just
    the datapoints that lie within the polygon defined by
    vertices. Note that the polygon *must* be convex (like a
    rectangle).
    '''
    filter = PNPoly(vertices)
    with open('pnpoly.csv', 'w') as fout:
        writer = csv.writer(fout)
        for (bssid, lat, lon) in csv.reader(open('input.csv')):
            if filter.contains(float(lat), float(lon)):
                writer.writerow((bssid, lat, lon))


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


def compute_dupe_num(pcnt, zoom):
    u_tiles = set()
    for (bssid, tx, ty) in csv.reader(open('pnpoly_tiles.csv')):
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

    return int(pcnt * (MAX_IDX+1))


def generate_ids(batch_size):
    u_tiles = set()
    for (bssid, tx, ty) in csv.reader(open('pnpoly_tiles.csv')):
        u_tiles.add((int(tx), int(ty)))

    # Just compute the list of (tilex, tiley) tuples
    u_tiles = list(u_tiles)
    MAX_IDX = len(u_tiles)-1

    for (real_bssid, tx, ty) in csv.reader(open('pnpoly_tiles.csv')):
        real_tile_x = int(tx)
        real_tile_y = int(ty)

        MIDDLE = randint(0, batch_size-2)

        randomized_set = set()

        # TODO: this needs to build up the entire randomized dataset
        # and fix uniques before
        while len(randomized_set) < MIDDLE:
            x, y = u_tiles[randint(0, MAX_IDX)]
            randomized_set.add((real_bssid, x, y))

        # Return the real tile location
        randomized_set.add((real_bssid, real_tile_x, real_tile_y))

        while len(randomized_set) < (batch_size-1):
            x, y = u_tiles[randint(0, MAX_IDX)]
            randomized_set.add((real_bssid, x, y))

        for k in randomized_set:
            yield k


def obfuscate_tile_data(dupe_num):
    # First compute all unique tiles
    tile_gen = generate_ids(dupe_num)
    with open('obfuscated.csv', 'w') as fout:
        writer = csv.writer(fout)
        for i, row in enumerate(tile_gen):
            if i % 100000 == 0:
                print "Processed %dk records" % (i / 1000)
            writer.writerow(row)
        print "Processed %dk records" % (i / 1000)
    return dupe_num


def compute_tries():
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
                    print len(dataset)
            bssid_locations.append(tile_map[(int(x), int(y))])
            last_bssid = bssid
    trie = RecordTrie("<" + ("I" * len(bssid_locations)), dataset.items())
    trie.save('toronto.record_trie')
    print "saved!"


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


if __name__ == '__main__':
    # This set of points roughly contains the Metro toronto area
    v = [(43.754533, -79.631391),
         (43.855652, -79.170215),
         (43.585491, -79.541599),
         (43.585491, -79.170215)]

    # BSSIDs should be duplicated to ~5% of all cells
    PERCENT_DUPE = 0.05

    '''
    compute_pnpoly_set(v)
    pnpoly_to_tiles()
    dupe_num = compute_dupe_num(PERCENT_DUPE, ZOOM_LEVEL)
    obfuscate_tile_data(dupe_num)
    '''
    compute_tries()
