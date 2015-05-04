import json
from matplotlib.path import Path


def parse_polygon(geojson_filename):
    jdata = json.load(open(geojson_filename))
    assert jdata['features'][0]['geometry']['type'] == 'Polygon'
    assert len(jdata['features'][0]['geometry']['coordinates']) == 1
    poly_path = jdata['features'][0]['geometry']['coordinates'][0]
    pts = []
    for pt in poly_path:
        lon, lat = pt
        lon = float(lon) + 180
        lat = float(lat) + 90
        pts.append((lat, lon))
    codes = [Path.MOVETO] + [Path.LINETO] * (len(pts)-2) + [Path.CLOSEPOLY]
    matplot_polygon = Path(pts, codes)
    return matplot_polygon
