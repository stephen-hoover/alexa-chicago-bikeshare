import os
import json

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


def test_find_station_one_ambiguous():
    sta = _station_list()

    try:
        location.find_station(sta, 'Halsted')
    except location.AmbiguousStationError as err:
        assert 'halsted street' in err.message.lower()
    else:
        assert False, 'Expected an AmbiguousStationError.'


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
