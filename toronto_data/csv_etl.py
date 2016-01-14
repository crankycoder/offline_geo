'''
This just cleans up the Newmarket dataset into something usable.

Output of this should be a CSV file with no header row.

Each row is BSSID, lat, lon

BSSID is lower case and no separators between hex values.

Output rows should look like this:

002351bfaa49,43.5813927142857,-79.6150485714286

Preconditions:
    wifi_raw.csv - raw input file

    The raw input file should have at least some rows which have tab
    delimited rows with (bssid, lat, lon, radius in meters)


Output:
    cleaned_wifi.csv - cleaned input file
'''

import sys
import csv

RAW_INPUT = 'wifi_raw.csv'
CLEAN_OUTPUT = 'cleaned_wifi.csv'

bssid_set = set()
with open(CLEAN_OUTPUT, 'w') as fout:
    writer = csv.writer(fout)
    for i, row in enumerate(csv.reader(open(RAW_INPUT), delimiter='\t')):
        try:
            bssid, lat, lon, accuracy_meters = row

            # Do some nominal cleanup
            bssid = bssid.strip()
            lat = float(lat)
            lon = float(lon)
            accuracy_meters = float(accuracy_meters)

            # TODO: hook plot.ly to generate a histogram of
            # accuracy data by meters
            # For now, we just use the entire dataset

            if len(bssid) == 12:
                if bssid in bssid_set:
                    print "already have : %s" % bssid
                    continue
                bssid_set.add(bssid)
                writer.writerow((row[0], row[1], row[2]))
        except:
            e = sys.exc_info()[0]
            print "Skipping : %d" % i
            continue
