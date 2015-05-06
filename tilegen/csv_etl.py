'''
This just cleans up the Toronto dataset into something usable.

Output of this should be a CSV file with no header row.

Each row is BSSID, lat, lon

BSSID is lower case and no separators between hex values.

ex row:

002351bfaa49,43.5813927142857,-79.6150485714286

'''
import sys
import csv

bssid_set = set()
with open('wifi_toronto_clean.csv', 'w') as fout:
    writer = csv.writer(fout)
    for i, row in enumerate(csv.reader(open('toronto.csv'), delimiter='\t')):
        try:
            float(row[1])
            float(row[2])
            bssid = row[0].strip()
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
