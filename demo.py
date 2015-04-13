#!/usr/bin/env python

import csv
import math
from scrambler import randint

# Typical tile size at zoom 17
# http://c.tile.openstreetmap.org/17/36629/47838.png
ZOOM_LEVEL = 17

class PNPoly(object):

    def __init__(self, pts):
        '''
        We need to compute the dataset for metro toronto by taking
        the set of 4 points and computing the areas where BSSIDs are
        valid.
        '''
        self.vertx = [pt[1] for pt in pts]
        self.verty = [pt[0] for pt in pts]


    def contains(self, lat, lon):
        nvert = len(self.vertx)
        c = False
        i = 0
        j = nvert-1
        while (i < nvert):
            if (((self.verty[i]>lat) != (self.verty[j]>lat)) and \
                (lon < (self.vertx[j]-self.vertx[i]) * (lat-self.verty[i]) / (self.verty[j]-self.verty[i]) + self.vertx[i]) ):
                c = not(c)
            i += 1
            j = i
        return c;

def compute_pnpoly_set(vertices):
    '''
    Filter input.csv (bssid, lat, lon) down to just
    the datapoints that lie within the polygon defined by 
    vertices. Note that the polygon *must* be convex (like a
    rectangle).
    '''
    filter = PNPoly(vertices)
    with open('pnpoly.csv','w') as fout:
        writer = csv.writer(fout)
        for (bssid, lat, lon) in csv.reader(open('input.csv')):
            if filter.contains(float(lat), float(lon)):
                writer.writerow((bssid, lat, lon))


def pnpoly_to_to_tiles():
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


def generate_ids(pcnt):
    u_tiles = set()
    for (bssid, tx, ty) in csv.reader(open('pnpoly_tiles.csv')):
        u_tiles.add((int(tx), int(ty)))

    # Just compute the list of (tilex, tiley) tuples
    u_tiles = list(u_tiles)
    MAX_IDX = len(u_tiles)-1

    batch_size = int(pcnt * (MAX_IDX+1))

    for (real_bssid, tx, ty) in csv.reader(open('pnpoly_tiles.csv')):
        real_tile_x = int(tx)
        real_tile_y = int(ty)

        MIDDLE = randint(0, batch_size-1)

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

def obfuscate_tile_data():
    # First compute all unique tiles

    # BSSIDs should be duplicated to ~5% of all cells
    PERCENT_DUPE = 0.05

    tile_gen = generate_ids(PERCENT_DUPE)
    with open('obfuscated.csv', 'w') as fout:
        writer = csv.writer(fout)
        for i, row in enumerate(tile_gen):
            if i % 100000 == 0:
                print "Processed %dk records" % (i / 1000)
            writer.writerow(row)
        print "Processed %dk records" % (i / 1000)


def compute_tries():
    pass

if __name__ == '__main__':
    # This set of points roughly contains the Metro toronto area
    v = [(43.754533, -79.631391),
         (43.855652, -79.170215),
         (43.585491, -79.541599),
         (43.585491, -79.170215)]

    compute_pnpoly_set(v)
    pnpoly_to_to_tiles()
    obfuscate_tile_data()
    # TODO
    #compute_tries()
