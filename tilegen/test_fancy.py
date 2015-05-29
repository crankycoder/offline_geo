from fancy_algo import offline_fix
from strategies import BasicLocationFix

def test_fancy_fix():
    strategies = [BasicLocationFix, ]

    offline_fix(strategies)

