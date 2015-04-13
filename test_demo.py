from nose.tools import eq_
from demo import denormalize_tileid, normalize_tilenumbers

def test_normalization():
    z, x, y = 17, 36594, 47643
    tile_id = normalize_tilenumbers(x, y, z)
    result = denormalize_tileid(tile_id, z)
    eq_((x, y), result)
