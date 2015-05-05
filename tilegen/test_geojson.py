from geojson import load_path

from nose.tools import eq_
from nose.tools import assert_almost_equal as almost


def compare_pt(p1, p2):
    eq_(2, len(p1))
    eq_(2, len(p2))
    almost(p1[0], p2[0])
    almost(p1[1], p2[1])


def test_toronto_path():
    poly = load_path('toronto.geojson')
    first = (43.67115634799999, -79.28004521399998)
    last = (43.67115634799999, -79.28004521399998)

    compare_pt(first, poly[0])
    compare_pt(last, poly[-1])
