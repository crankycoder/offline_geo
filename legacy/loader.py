import csv
import random
import math
import gc
from scrambler import randint
from marisa_trie import RecordTrie
from dawg import RecordDAWG
import struct
from itertools import izip

# Typical tile size at zoom 18
# http://c.tile.openstreetmap.org/18/73258/95677.png
ZOOM_LEVEL = 18

def dump_trie(fname):
    import marisa_trie
    with open(fname) as f_in:
        keys = (row['key'] for row in csv.DictReader(f_in, delimiter='\t'))
        trie = marisa_trie.Trie(keys)
    trie.save(fname + ".trie")


def dump_tuples():
    fname = 'wifi_toronto_clean.csv'
    with open(fname) as f_in:
        for i, row in enumerate(csv.reader(f_in)):
            value = bytes(str(int(abs(float(row[1]))*10000) % 65535))
            row = (unicode(row[0]), value)
            if i % 500 == 0:
                print "Processing entry: %d" % i
            for d in scrambler(row):
                yield d


def clean_toronto():
    with open('wifi_toronto.csv') as f_in:
        with open('wifi_toronto_clean.csv', 'w') as f_out:
            writer = csv.writer(f_out)
            for row in csv.DictReader(f_in, delimiter='\t'):
                writer.writerow([row['key'], row['lat'], row['lon']])


class BatchIterator(object):
    BATCH_SIZE = 100000

    def __init__(self, big_iterable):
        self._iterable = big_iterable
        self._count = 0
        self._done = False

    def __iter__(self):
        return self

    def next(self):
        self._count += 1
        if (self._count % self.BATCH_SIZE) == (self.BATCH_SIZE-1):
            print "Dumping batch up to %d" % self._count
            raise StopIteration()
        try:
            if (self._count % 1000) == 0:
                print "Processing record %d" % self._count
            return self._iterable.next()
        except StopIteration:
            self._done = True
            raise


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

def compute_toronto_to_tiles():
    result = set()
    with open('wifi_toronto_clean_as_tiles.csv', 'w') as f_out:
        writer = csv.writer(f_out)
        writer.writerow(('bssid', 'x', 'y', 'zoom'))
        with open('wifi_toronto_clean.csv', 'r') as f_in:
            for i, row in enumerate(csv.reader(f_in)):
                bssid = row[0]
                lat = float(row[1])
                lon = float(row[2])
                tile_x, tile_y = deg2num(lat, lon, ZOOM_LEVEL)
                entry = (bssid, tile_x, tile_y)
                result.add(entry)
                writer.writerow(entry)
    return result

def compute_tiles_with_wifi():
    """
    We only want to obtain the set of tile IDs where we have at least
    a single BSSID.
    """
    tile_ids = set()
    with open('wifi_toronto_clean_as_tiles.csv', 'r') as f_in:
        for i, row in enumerate(csv.reader(f_in)):
            if i == 0:
                continue
            x = int(row[1])
            y = int(row[2])
            tile_ids.add((x,y))

    actual_tiles = len(tile_ids)
    return tile_ids


def create_random_sequence_generator(tileid_set):
    '''
    Given a set of tile_ids, this function will create a generator
    which will yield a list of randomly generated tuple of the 
    form (bssid, tile_x, tile_y) including the real tile location.
    '''
    def generate_ids(batch_size, bssid, tile_x, tile_y):
        tile_list = list(tileid_set)
        max_tile_idx = len(tile_list)-1
        middle = randint(0, batch_size-1)
        for i in range(middle):
            x, y = tile_list[randint(0, max_tile_idx)]
            yield bssid, x, y

        # Return the real tile location
        yield bssid, tile_x, tile_y

        for i in range(middle, batch_size-1):
            x, y = tile_list[randint(0, max_tile_idx)]
            yield bssid, x, y
    return generate_ids


def generate_scrambled_data(dupe_num, tile_set, generator):
    for i, (real_bssid, real_tile_x, real_tile_y) in enumerate(tile_set):
        if i % 200 == 0:
            print i
        tile_ids = []
        for bssid, tilex, tiley in generator(dupe_num, 
                real_bssid,
                real_tile_x,
                real_tile_y):
            # bitshift to compresss x and y co-ords into 32bits
            # TODO: this needs to be reworked so that the tile offsets
            # are recomputed w.r.t the viewport for the city
            # FYI- zoom 18 has 262,144^2 tiles so we need each
            # axis to fit inside of 0-32k
            value = int((tilex<<15) + tiley)
            tile_ids.append(value)
        yield tile_ids

if __name__ == '__main__':
    #clean_toronto()
    #write_all_toronto()

    toronto_set = compute_toronto_to_tiles()
    tile_set = compute_tiles_with_wifi()

    generator1 = create_random_sequence_generator(tile_set)
    dupe_num = int(len(tile_set) * 0.05)

    print "Duping each tile %d times" % dupe_num
    print "Total Toronto set size: %d" % len(toronto_set)

    def get_bssids():
        for i, (real_bssid, real_tile_x, real_tile_y) in enumerate(toronto_set):
            yield unicode(real_bssid)

    bi = BatchIterator(izip(get_bssids(), generate_scrambled_data(dupe_num, 
                                          toronto_set,
                                          generator1)))

    fnum = 0
    fmt = "<" + ("I" * dupe_num)
    while not bi._done:
        rtrie = RecordTrie(fmt, bi)
        gc.collect()
        fname = 'toronto_%d.rtrie' % fnum

        rtrie.save(fname)
        gc.collect()

        print "Wrote: %s" % fname
        fnum += 1
    print "Finished all records"
