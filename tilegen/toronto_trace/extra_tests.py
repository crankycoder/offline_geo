import re
import dateutil.parser

bssid_re = re.compile("Using BSSID = \[(.*)\]")

sample = []

file_num = 0
for l in open('2015-05-12-20-29-36.txt'):
    matches = bssid_re.findall(l)
    if matches:
        sample.extend(matches)
    else:
        if sample:
            date_part = l[:14]
            sample_date = dateutil.parser.parse(date_part)
            with open('toronto_bssid_%04d.txt' % file_num, 'w') as fout:
                for bssid in sample:
                    fout.write(sample_date.isoformat() + "," + bssid + "\n")
            file_num += 1
        sample = []

if sample:
    date_part = l[:14]
    sample_date = dateutil.parser.parse(date_part)
    with open('toronto_bssid_%04d.txt' % file_num, 'w') as fout:
        for bssid in sample:
            fout.write(sample_date.isoformat() + "," + bssid + "\n")
    file_num += 1
