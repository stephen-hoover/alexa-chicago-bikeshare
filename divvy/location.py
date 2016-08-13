import requests


ABBREV = {' st ': ' street ',
          ' pl ': ' place ',
          ' ave ': ' avenue ',
          ' blvd ': ' boulevard ',
          ' dr ': ' drive ',
          ' rd ': ' road ',
          ' ln ': ' lane ',
          ' pkwy ': ' parkway ',
          ' ter ': ' terrace ',
          ' ct ': ' court '}


class AmbiguousStationError(ValueError):
    pass


def _check_possible(possible, first, second=None):
    if len(possible) == 1:
        return possible[0]
    elif not possible:
        if second:
            raise AmbiguousStationError("I couldn't find a station at %s and %s." % (first, second))
        else:
            raise AmbiguousStationError("I couldn't find a station at %s." % first)
    else:
        possible_list = (', '.join([text_to_speech(p['stationName']) for p in possible[:-1]]) +
                         ', or %s' % text_to_speech(possible[-1]['stationName']))
        raise AmbiguousStationError("I don't know if you mean %s." % possible_list)


def find_station(stations, first, second=None):
    """Filter the Divvy station list to find a single station

    Parameters
    ----------
    stations : list of dict
        The 'stationBeanList' from the Divvy API response
    first : str
        The first component of a station name or address,
        e.g. "Larrabee" or "Larrabee Street".
    second : str, optional
        As `first`.

    Returns
    -------
    dict
        A single station status JSON from the Divvy API response

    Raises
    ------
    AmbiguousStationError if `first` and `second`
        don't uniquely specify a station
    """
    possible = []
    first = speech_to_text(first)
    if not second:
        # Search the "location" field.
        for sta in stations:
            if first == sta['stationName'].lower():
                return sta
        # Search the "address" field.
        for sta in stations:
            if first in sta['stAddress1'].lower():
                possible.append(sta)

        return _check_possible(possible, first, second)
    else:
        second = speech_to_text(second)
        for sta in stations:
            address = sta['stAddress1'].lower()
            name = sta['stationName'].lower()
            if ((first in address and second in address) or
                    (first in name and second in name)):
                possible.append(sta)

        return _check_possible(possible, first, second)


def speech_to_text(address):
    """Standardize speech input to look like Divvy station names
    """
    # Add a space, since we look for spaces after abbreviations
    address = address.lower() + ' '
    address = address.replace('and', '&')

    for ab, full in ABBREV.iteritems():
        address = address.replace(full, ab)

    return address.strip()


def text_to_speech(address):
    """Expand abbreviations in text so that Alexa can speak it
    """
    # Add a space, since we look for spaces after abbreviations
    address = address.lower() + ' '
    address = address.replace('&', 'and')
    address = address.replace('(*)', '')

    for ab, full in ABBREV.iteritems():
        address = address.replace(ab, full)

    return address.strip()


def get_stations(divvy_api):
    resp = requests.get(divvy_api)
    stations = resp.json()['stationBeanList']

    return stations
