from geojson import parse_polygon

def test_toronto():
    poly = parse_polygon('toronto.geojson')
