#!/usr/bin/python

import csv
from geocalc import add_meters_to_longitude
from geocalc import add_meters_to_latitude
import datetime

center_lat = 37.8043700
center_lon = -122.2708

max_lat = add_meters_to_latitude(center_lat, 7000)
min_lat = add_meters_to_latitude(center_lat, -7000)

max_lon = add_meters_to_longitude(center_lat, center_lon, 7000)
min_lon = add_meters_to_longitude(center_lat, center_lon, -7000)

print min_lat, max_lat
print min_lon, max_lon

def filter_oakland_only():
    with open('MLS-full-cell-export-2015-03-26T000000.csv') as file_in:
        with open('oakland.csv', 'w') as file_out:
            reader = csv.DictReader(file_in)
            writer = None
            for i, row in enumerate(reader):
                if i == 0:
                    writer = csv.writer(file_out)
                    writer.writerow(row.keys())
                if min_lat <= float(row['lat']) <= max_lat:
                    if min_lon <= float(row['lon']) <= max_lon:
                        writer.writerow(row.values())
                if i % 50000 == 0:
                    print "Processed %d records" % i

def find_stingrays():
    with open('oakland.csv') as file_in:
        reader = csv.DictReader(file_in)
        for row in reader:
            last_update = datetime.datetime.fromtimestamp(int(row['updated']))
            if last_update.year < 2015:
                print row

def compute_stats():
    with open('oakland.csv') as file_in:
        reader = csv.DictReader(file_in)
        count = 0
        for i, row in enumerate(reader):
            count += int(row['samples'])
        print "Average samples: %d" % (count / (i+1))

#filter_oakland_only()
compute_stats()
#find_stingrays()
