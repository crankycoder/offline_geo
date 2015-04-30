from nose.tools import eq_
from zoompack import pack_24bits, unpack_24bits

def test_packer():
    v = 2 ** 16 + 5 
    eq_(v, unpack_24bits(pack_24bits(v)))
