import os
import json

import pytest

from divvy import location


def _api_response():
    fname = os.path.join(os.path.dirname(__file__),
                         'samples',
                         'sample_divvy_response.json')
    with open(fname, 'r') as _fin:
        return json.load(_fin)


def _station_list():
    return _api_response()['stationBeanList']


def test_find_stations_two_street():
    sta = _station_list()

    found = location.find_station(sta, 'Wells', 'Concord')

    assert isinstance(found, dict)
    assert 'Wells' in found['stationName']
    assert 'Concord' in found['stationName']
    assert not found['testStation']


def test_find_station_one_name():
    sta = _station_list()

    found = location.find_station(sta, 'Adler Planetarium')

    assert isinstance(found, dict)
    assert 'Adler' in found['stationName']
    assert not found['testStation']


def test_find_station_with_and():
    sta = _station_list()

    found = location.find_station(sta, 'Ashland Avenue and Grand Avenue', exact=True)

    assert isinstance(found, dict)
    assert 'Ashland Ave & Grand Ave' == found['stationName']
    assert not found['testStation']


def test_find_station_fuzzy():
    sta = _station_list()

    found = location.find_station(sta, 'ritchie quarton bank street')

    assert isinstance(found, dict)
    assert 'Ritchie Ct & Banks St' == found['stationName']
    assert not found['testStation']


def test_find_station_fuzzy_pair():
    sta = _station_list()

    found = location.find_station(sta, 'ashlande', 'grand avenue',
                                  exact=False)

    assert isinstance(found, dict)
    assert 'Ashland Ave & Grand Ave' == found['stationName']
    assert not found['testStation']


def test_find_station_fuzzy_pair_partial_nomatch():
    # The first thing we check, "concord and Welles", doesn't
    # have any matches with the default cutoff of 0.6.
    # Make sure we can still retrieve the correct station.
    sta = _station_list()

    found = location.find_station(sta, 'concord', 'Welles', exact=False)

    assert isinstance(found, dict)
    assert 'Wells St & Concord Ln' == found['stationName']
    assert not found['testStation']


def test_find_station_fuzzy_pair_complete_nomatch():
    sta = _station_list()

    with pytest.raises(location.AmbiguousStationError) as err:
        location.find_station(sta, '14131', 'xyzzz', exact=False)
    assert str(err.value).startswith("I couldn't find a station at")


def test_find_station_fuzzy_pair_flipped():
    # Fuzzy matching on an inverted pair of street names
    sta = _station_list()

    found = location.find_station(sta, 'grind', 'ashlande avenue',
                                  exact=False)

    assert isinstance(found, dict)
    assert 'Ashland Ave & Grand Ave' == found['stationName']
    assert not found['testStation']


def test_find_station_one_ambiguous():
    sta = _station_list()

    with pytest.raises(location.AmbiguousStationError) as err:
        location.find_station(sta, 'Halsted')
    assert 'halsted street' in err.value.message.lower()


def test_speech_to_text_two_street():
    out = location.speech_to_text('Halsted Street and North Branch Street')
    assert out.lower() == 'halsted st & north branch st'


def test_text_to_speech_two_street():
    out = location.text_to_speech('Halsted St & North Branch St')
    assert out.lower() == 'halsted street and north branch street'


def test_text_to_speech_address():
    out = location.text_to_speech('200 N State St')
    assert out.lower() == '200 north state street'


def test_text_to_speech_two_street_star():
    out = location.text_to_speech('Loomis St & Taylor St (*)')
    assert out.lower() == 'loomis street and taylor street'
