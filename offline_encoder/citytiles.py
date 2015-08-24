import csv


class OrderedCityTiles(object):
    '''
    This class provides acts like an order preserving
    hashtable.

    '''
    def __init__(self, load_fromdisk=False):
        self._hash = {}
        self._hash_list = []
        if load_fromdisk:
            with open('../outputs/incity_tiles.csv') as fin:
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
                return None, None

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
