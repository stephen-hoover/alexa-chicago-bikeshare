import json
import os

from unittest import mock

from divvy import handle


def _api_response(api_type='api'):

    fname = os.path.join(os.path.dirname(__file__),
                         'samples',
                         'sample_divvy_' + api_type + '.json')
    with open(fname, 'r') as _fin:
        return json.load(_fin)


def build_station_mock(not_renting=None):
    """Return a function which can be used to
    mock out `location.get_stations"""
    sta = _api_response('get_stations_output')

    if not_renting:
        # All stations in my sample response are renting, so hack it.
        for s in sta:
            if int(s['station_id']) in not_renting:
                s['is_renting'] = False

    def mock_get_stations(divvy_api):
        return sta

    return mock_get_stations


def _get_request(intent, case):
    fname = os.path.join(os.path.dirname(__file__),
                         'samples',
                         '%s_%s.json' % (intent, case))
    with open(fname, 'r') as _fin:
        return json.load(_fin)


@mock.patch.object(handle.location, "get_stations", build_station_mock())
def test_check_bike_bikes():
    intent = _get_request('check_bike', 'two_street')['request']['intent']

    out = handle.check_bikes(intent, {})
    expected = 'there are 5 bikes available at the ' \
               'halsted street and archer avenue station'

    assert expected in out['response']['outputSpeech']['ssml'].lower()


@mock.patch.object(handle.location, "get_stations", build_station_mock())
def test_check_bike_docks():
    intent = _get_request('check_docks', 'two_street')['request']['intent']

    out = handle.check_bikes(intent, {})
    expected = 'there are 9 docks available at the ' \
               'halsted street and archer avenue station'

    assert expected in out['response']['outputSpeech']['ssml'].lower()


@mock.patch.object(handle.location, "get_stations",
                   build_station_mock(not_renting=[206]))
def test_check_bike_not_renting():
    intent = _get_request('check_bike', 'two_street')['request']['intent']

    out = handle.check_bikes(intent, {})
    expected = "but the station isn't renting right now."

    assert expected in out['response']['outputSpeech']['ssml'].lower()


@mock.patch.object(handle.location, "get_stations", build_station_mock())
def test_check_status():
    intent = _get_request('check_status', 'two_street')['request']['intent']

    out = handle.check_status(intent, {})
    expected = 'there are 5 bikes and 9 docks at the ' \
               'halsted street and archer avenue station'

    assert expected in out['response']['outputSpeech']['ssml'].lower()


@mock.patch.object(handle.location, "get_stations",
                   build_station_mock(not_renting=[206]))
def test_check_status_not_renting():
    intent = _get_request('check_status', 'two_street')['request']['intent']

    out = handle.check_status(intent, {})
    expected = "the halsted street and archer avenue " \
               "station isn't renting right now."

    assert expected in out['response']['outputSpeech']['ssml'].lower()


@mock.patch.object(handle.location, "get_stations", build_station_mock())
@mock.patch.object(handle, "database")
def test_add_address_bad_address(mock_db):
    event = _get_request('add_address', 'bad_address')

    out = handle.intent(event['request'], event['session'])

    assert not out['response']['shouldEndSession']
    assert out['sessionAttributes']['next_step'] == "zip"
    assert (out['sessionAttributes']['spoken_address'] ==
            "16th street museum of science and industry")


@mock.patch.object(handle.location, "get_stations", build_station_mock())
@mock.patch.object(handle, "database")
def test_add_address_no_address(mock_db):
    event = _get_request('add_address', 'bad_address')
    event['request']['intent']['name'] = 'CheckCommuteIntent'

    out = handle.intent(event['request'], event['session'])

    assert not out['response']['shouldEndSession']
    assert out['sessionAttributes']['next_step'] == "num_and_name"
    assert ("I didn't understand that as an address.".lower() in
            out['response']['outputSpeech']['ssml'].lower())
