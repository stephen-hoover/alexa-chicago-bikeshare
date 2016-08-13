import json
import os

from divvy import handle


def _api_response():
    fname = os.path.join(os.path.dirname(__file__),
                         'samples',
                         'sample_divvy_response.json')
    with open(fname, 'r') as _fin:
        return json.load(_fin)


def _station_list():
    return _api_response()['stationBeanList']


def _get_request(intent, case):

    fname = os.path.join(os.path.dirname(__file__),
                         'samples',
                         '%s_%s.json' % (intent, case))
    with open(fname, 'r') as _fin:
        return json.load(_fin)


def test_check_bike_bikes():
    sta = _station_list()
    intent = _get_request('check_bike', 'two_street')['request']['intent']

    out = handle.check_bikes(intent, sta)
    expected = 'there are 5 bikes available at the ' \
               'halsted street and archer avenue station'

    assert expected in out['response']['outputSpeech']['ssml'].lower()


def test_check_bike_docks():
    sta = _station_list()
    intent = _get_request('check_docks', 'two_street')['request']['intent']

    out = handle.check_bikes(intent, sta)
    expected = 'there are 9 docks available at the ' \
               'halsted street and archer avenue station'

    assert expected in out['response']['outputSpeech']['ssml'].lower()


def test_check_bike_not_renting():
    sta = _station_list()
    intent = _get_request('check_bike', 'two_street')['request']['intent']

    # All stations in my sample response are renting, so hack it.
    [s for s in sta if s['id'] == 206][0]['is_renting'] = False

    out = handle.check_bikes(intent, sta)
    expected = "but the station isn't renting right now."

    assert expected in out['response']['outputSpeech']['ssml'].lower()
