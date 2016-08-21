import math

from divvy import geocoding
from divvy import test_handle


def test_distance():
    for _in, _exp in [((50.1, -87.3, 50.15,  -87.3), 5560),
                      ((50.1, -87.3, 50.15, -87.29), 5605),
                      ((-50.1, 87.3, -50.15, 87.29), 5605),
                      ((49.1, -86.3, 50.15, -87.3), 136800)]:
        delta = geocoding.distance(*_in) - _exp
        assert math.fabs(delta) / _exp < 1 ** -5


def test_stations_from_lat_lon():
    stations = test_handle.station_list()
    nearest = geocoding.station_from_lat_lon(41.866500, -87.609210,
                                             stations, n_nearest=3)
    assert len(nearest) == 3
    assert nearest[0]["stationName"] == "Adler Planetarium"
    assert nearest[1]["stationName"] == "Shedd Aquarium"
    assert nearest[2]["stationName"] == "Field Museum"

