'''
This module generates a stream of stable quasi-random numbers
to position fake BSSIDs.


We use a SOBOL sequence to generate a large stream of random numbers.

'''
# Std lib
import csv

# PyPI
from numpy import bitwise_xor
from sobol import i4_uniform

# Custom stuff
from fileutil import file_len

def write_sobol_seq(fname, seed, max_tilenum):
    with open(fname, 'w') as fout:
        _generate_stream(fout, seed, max_tilenum)
    return file_len(fname)

def _generate_stream(fout, seed=0, max_tilenum=0):
    """
    This generates a stable stream of quasi-random numbers and write
    it out to disk.  The idea is to use the list as a circular buffer.

    For each BSSID, we store an index into this list and then iterate
    for N fake BSSIDs.  
    
    Still need to figure out how to make this work at lower zoom
    levels when more area is visible, or how to handle the case where
    we want continuous maps that are greater than a city boundary.
    """

    # This seed number should be held on the ichnaea server as a
    # secret.  It's not critically important to maintain as a secret
    # as the i4_uniform function generates a new seed for every
    # iteration.
    DEFAULT_INITIAL_SEED = 1233441294

    # We want to generate 100,000 numbers in the sequence
    SEQUENCE_LENGTH = 100000

    DEFAULT_MAX_TILENUM = 65535

    if max_tilenum == 0:
        max_tilenum = DEFAULT_MAX_TILENUM

    if seed == 0:
        seed = DEFAULT_INITIAL_SEED

    writer = csv.writer(fout)
    for test in xrange(0, SEQUENCE_LENGTH):
        (i, seed) = i4_uniform (0, max_tilenum, seed)
        writer.writerow((i, seed))
    fout.flush()
