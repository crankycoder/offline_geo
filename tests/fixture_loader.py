"""
Functions to help with loading test data
"""

import glob

def fetch_bssids(fname):
    bssids = []
    for line in open(fname):
        dt, bssid = line.strip().split(",")
        if len(bssid) == 12:
            bssids.append(bssid)
    return bssids

def list_fixtures():
    for fname in glob.glob('toronto_trace/toronto_bssid_*.txt'):
        yield fname
