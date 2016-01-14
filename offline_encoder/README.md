Usage:


These scripts will generate two datafiles for you for use with offline
location fixes.

You'll need two input files to run this code.

* input.csv

We used to use a complex edge defining only land locked areas for the
geojson.  Now we just use a rectangular area with a maximum of 16k
tiles defined at zoom level 18.


How to use the script:

Just run `python ./encoder.py`

This will first generate 
