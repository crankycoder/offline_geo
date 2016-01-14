"""
Functions to help with loading test data
"""


def fetch_bssids(fname):
    bssids = []
    for line in open(fname):
        bssid = line.strip()
        if len(bssid) == 12:
            bssids.append(bssid)
    return bssids
