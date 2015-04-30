from cStringIO import StringIO
from tiler import generate_stream
from nose.tools import eq_

def test_stable_tiler():
    fout = StringIO()
    generate_stream(fout)

    fout2 = StringIO()
    generate_stream(fout2)

    d1 = fout.getvalue()
    d2 = fout2.getvalue()
    assert len(d1) > 0
    eq_(d1, d2)
