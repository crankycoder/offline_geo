'''
Hash and truncate the BSSIDs into 12 digit hexdigests
'''

import csv
import hashlib

with open('hashed_input.csv', 'w') as f_out:
    writer = csv.writer(f_out)
    file_in = open('input.csv')
    for i, row in enumerate(csv.reader(file_in, delimiter=',')):
        raw_bssid, lat, lon = row
        hashed_bssid = hashlib.sha256(raw_bssid).hexdigest()[:12]
        writer.writerow([hashed_bssid, lat, lon])
        if i % 2000 == 0:
            print "Processed %d rows" % i
    print "Processed %d rows" % i
