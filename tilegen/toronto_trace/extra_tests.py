
import re
bssid_re = re.compile("Using BSSID = \[(.*)\]")

sample = []

file_num = 0
for l in open('2015-05-12-20-29-36.txt'):
    matches = bssid_re.findall(l)
    if matches:
        sample.extend(matches)
    else:
        if sample:
            with open('toronto_bssid_%04d.txt' % file_num, 'w') as fout:
                for s in sample:
                    fout.write(s+"\n")
            file_num += 1
        sample = []

