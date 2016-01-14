Generating a marisa trie to store BSSID data.


Raw data sources:

- Raw dump of (bssid, lat, lon) - input.csv

Initial conversion of point data for input.csv must be done by a
dedicated ETL script for the particular raw data.

Steps for conversion:

1. Load GeoJSON data
2. Generate a polygon with matplotlib
3. Compute the pointset that is inside the polygon using PNPoly.
   Points within the city polygon go into pnpoly.csv.
   Points outside the city polygon go into pnpoly_outside.csv
4. Convert pnpoly.csv data to map to tiles.  
   So (bssid, lat, lon) -> (bssid, tile_x, tile_y, zoom_level)
   Zoom level is always defined as Z18
5. Compute the tiles that are within the city.  This means we take the
   polygon for the city and compute a bounding box.
   
   Given the top left and bottom right of the bounding box, we can 
   compute the tile_x and tile_y co-ordinates for those extremes.
   
   With the (tile_x, tile_y) for the top left and bottom right, we can
   iterate over all the tiles within the bounding box and test if the
   center is within the polygon bounding box.

   For each tile that is in the polygon, write out a row with 
   (tile_x, tile_y, zoom_level) into `incity_tiles.csv`
   

Obfuscation layer.

6. Now we generate a sobol sequence that is distributed over
   the number of tiles that are within the city.   This is equal to
   the number of lines within `incity_tiles.csv`. Write the sequence
   out to `sobol_seq.csv`

   The sobol sequence is 100,000 numbers long.  This makes it possible
   to pick an index into the generated sequence and getting a unique
   subsequence of sobol numbers.

7. Read in the pnpoly_tiles.csv file and generate an index into
   `sobol_seq.csv` for each bssid.  This is what will allow us to have
   a unique subsequence of sobol numbers for each bssid.  

8. Generate obfuscated data by applying the sobol sequence indexes to
   the raw bssid.  Write out data to `obfuscated.csv`

9.  Push obfuscated data into a marisa trie and save to disk
