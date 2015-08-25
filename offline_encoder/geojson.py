import json


def load_geojson(geojson_filename):
    jdata = json.load(open(geojson_filename))
    assert jdata['features'][0]['geometry']['type'] == 'Polygon'
    assert len(jdata['features'][0]['geometry']['coordinates']) == 1
    poly_path = jdata['features'][0]['geometry']['coordinates'][0]
    pts = []
    for pt in poly_path:
        lon, lat = pt
        lon = float(lon)
        lat = float(lat)
        pts.append((lat, lon))
    return pts
