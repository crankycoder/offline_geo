from demo import num2deg, ZOOM_LEVEL

def load_city():
    from demo import OrderedCityTiles
    return OrderedCityTiles(load_fromdisk=True)


def fetch_bssids():
    bssids = []
    for line in open('toronto.bssid'):
        bssid = line.strip()
        if len(bssid) == 12:
            bssids.append(bssid)
    return bssids

def load_trie(fmt):
    from marisa_trie import RecordTrie
    return RecordTrie(fmt).mmap('offline.record_trie')

def offline_fix(fmt):
    """
    Setup an array of small integers (8bit) to map to all possible
    tiles (64k).

    Fetch all set results from the trie for each found BSSID and
    add 1 point to the array index for each location.

    When all BSSIDs have been exhausted, scan the array. For every
    index where we have 2 or more points, we want to weight those
    matches heavily - so multiply the value by 5 and overwrite the
    index value.

    We also want to assign points for adjacent tiles where we have a
    score > 10 (2 tries agree).

    Using the lookup from load_city, find all adjacent tiles and sum
    up the surrounding points and add them into a *second* array to
    avoid double counting.

    Add the values from the second array into the first array.

    Find the index with the maximum value. For ties, return the first
    match.
    """

    t = load_trie(fmt)

    tile_points = [0] * 65535

    # These BSSIDs are visible in Newmarket near Vic's house
    bssids = fetch_bssids()

    last_result = None
    for bssid in bssids:
        matchContainer = t.get(bssid)
        if matchContainer is None:
            print "BSSID [%s] is not in the dataset" % bssid
            continue
        for pt in matchContainer[0]:
            tile_points[pt] += 1

    max_tilept = max(tile_points)
    if max_tilept <= 1:
        print "No tries agreed on a solution"
        return

    maxpt_tileset = set()
    for i, v in enumerate(tile_points):
        if v == max_tilept:
            maxpt_tileset.add(i)

    city_tiles = load_city()
    if len(maxpt_tileset) == 1:
        print "Unique solution found: " + str(maxpt_tileset)
        extra_info(city_tiles, list(maxpt_tileset)[0], max_tilept, tile_points)
        return
    else:
        # We have to solve a tie breaker
        # Square the points for the max point array
        for pt in maxpt_tileset:
            tile_points[pt] *= tile_points[pt]

        msg = "Tie breaker with score: [%d]! Highest scoring tiles: %s"
        print msg % (max_tilept, str(maxpt_tileset))
        print "Adjusted score is: %d" % (max_tilept*max_tilept)

        adj_tile_points = {}

        for tile in maxpt_tileset:
            # For each adjacent tile, add points into the center
            for adjacent_tileid in adjacent_tile(tile):
                new_pts = tile_points[adjacent_tileid]

                msg = "Adding %d points from [%s](%d) to tile: %s(%d)"
                print msg % (new_pts,
                        city_tiles[adjacent_tileid],
                        adjacent_tileid,
                        city_tiles[tile],
                        tile)
                adj_tile_points[tile] = adj_tile_points.get(tile, 0)
                adj_tile_points[tile] += new_pts

        for k, v in adj_tile_points.items():
            tile_points[k] += v

        max_tilept = max(tile_points)
        maxpt_tileset = set()
        for i, v in enumerate(tile_points):
            if v == max_tilept:
                maxpt_tileset.add(i)

        if len(maxpt_tileset) == 1:
            print "Tie breaking solution: %s" % str(maxpt_tileset)
        else:
            msg = "Multiple solutions: "
            print msg + maxpt_tileset

            tiebreaking_set = set()
            maxpt_tilelist = list(maxpt_tileset)
            for i, pt in enumerate(maxpt_tilelist):
                adjacent_tilelist = list(adjacent_tile(pt))
                adjacent_tileset = set(adjacent_tilelist) & set(maxpt_tilelist[i+1:])
                if adjacent_tileset:
                    tiebreaking_set.add(pt)
                    tiebreaking_set = tiebreaking_set.union(pt)

            final_lat = 0
            final_lon = 0
            for tie in tiebreaking_set:
                tx, ty = city_tiles[tie]
                tmp_lat, tmp_lon = num2deg(tx, ty, ZOOM_LEVEL)
                final_lat += (tmp_lat * 1.0/len(tiebreaking_set))
                final_lon += (tmp_lon * 1.0/len(tiebreaking_set))

            msg = "Multiple solutions converging on : " + (final_lat, final_lon)
            # TODO: maybe add adjacent signals to the final solution


def extra_info(city_tiles, center_pt, center_height, tile_points):
    tx, ty = city_tiles[center_pt]
    c_lat, c_lon = num2deg(tx, ty, ZOOM_LEVEL)
    print "Center is at: %f, %f" % (c_lat, c_lon)

    weighted_lat_lon = []
    for adj_tileid in adjacent_tile(center_pt):
        adj_tx, adj_ty = city_tiles[adj_tileid]
        adj_pts = tile_points[adj_tileid]
        if adj_pts:
            print "Extra points at: ", adj_tileid, adj_pts
            print "Lat Lon for %d is %s" % (adj_tileid, num2deg(adj_tx, adj_ty, ZOOM_LEVEL))
            tx, ty = city_tiles[adj_tileid]
            lat, lon = num2deg(tx, ty, ZOOM_LEVEL)
            weighted_lat_lon.append((adj_pts, (lat, lon)))

    # Now compute a new center
    w_lat = 0
    w_lon = 0
    for (adj_pts, (lat, lon)) in weighted_lat_lon:
        w_lat += (lat * adj_pts)
        w_lon += (lon * adj_pts)
    shift_weight = sum([x[0] for x in weighted_lat_lon])
    w_lat /= shift_weight
    w_lon /= shift_weight
    print "Adjacent wlat/wlon: %f, %f" % (w_lat, w_lon)


    # No need to be overly smart here.  Just use 50% real fix, 50%
    # weighted adjusted location.
    n_lat = (c_lat * 0.5 + w_lat * 0.5)
    n_lon = (c_lon * 0.5 + w_lon * 0.5)

    print "Recomputed lat/lon: %f, %f" % (n_lat, n_lon)




def adjacent_tile(tile_id):
    city_tiles = load_city()
    tx, ty = city_tiles[tile_id]

    yield city_tiles[(tx-1, ty-1)]
    yield city_tiles[(tx  , ty-1)]
    yield city_tiles[(tx+1, ty-1)]

    yield city_tiles[(tx-1, ty)]
    yield city_tiles[(tx+1, ty)]

    yield city_tiles[(tx-1, ty+1)]
    yield city_tiles[(tx  , ty+1)]
    yield city_tiles[(tx+1, ty+1)]


def fancy_fix():
    dupe_num = 100
    fmt = "<" + ("i" * dupe_num)
    offline_fix(fmt)

if __name__ == '__main__':
    fancy_fix()
