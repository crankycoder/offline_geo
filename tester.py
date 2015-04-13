import marisa_trie
import sys
import csv

fmt = '<' + "I" * 572
tries = [marisa_trie.RecordTrie(fmt).mmap('toronto_0.rtrie'),
         marisa_trie.RecordTrie(fmt).mmap('toronto_1.rtrie'),
         marisa_trie.RecordTrie(fmt).mmap('toronto_2.rtrie')]

def compute_min_max_tiles():
    reader = csv.reader(open('wifi_toronto_clean_as_tiles.csv'))
    reader.next()
    min_x = min_y = max_x = max_y = 0

    for row in reader:
        row[1] = int(row[1])
        row[2] = int(row[2])
        if min_x == 0 or min_x > row[1]:
            min_x = row[1]

        if min_y == 0 or min_y > row[2]:
            min_y = row[1]

        if max_x == 0 or max_x < row[1]:
            max_x = row[1]

        if max_y == 0 or max_y < row[1]:
            max_y = row[1]

    print "Total tiles: %d" % ((max_x-min_x) * (max_y-min_y))
    print "Min X, Min Y: %d  %d" % (min_x, min_y)
    print "Width %d" % (max_x-min_x)


def intersect(*args):
    cur_results = None
    for x in args:
        for t in tries:
            tmp = t.get(x)
            if tmp != None and tmp != []:
                if cur_results == None:
                    cur_results = set(*tmp)
                else:
                    cur_results = cur_results.intersection(set(*tmp))
    print "results: " + str(list(cur_results))

#intersect('c0a0bbe3df93', '0018f84fc20e', '68b6fcc7dcb9', 'd86ce9269fe5')
compute_min_max_tiles()
