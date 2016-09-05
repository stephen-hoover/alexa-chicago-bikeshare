import difflib
import logging
import requests

log = logging.getLogger(__name__)

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

DIRECTIONS = {' n ': ' north ',
              ' w ': ' west ',
              ' s ': ' south ',
              ' e ': ' east '}


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


def matching_station_list(stations, first, second=None, exact=False):
    """Filter the Divvy station list based on locations

    May return multiple stations

    Parameters
    ----------
    stations : list of dict
        The 'stationBeanList' from the Divvy API response
    first : str
        The first component of a station name or address,
        e.g. "Larrabee" or "Larrabee Street".
    second : str, optional
        As `first`.
    exact : bool, optional
        If True, require exact string matches. Otherwise
        always return at least one station name. If no
        exact match, return the closest string match to
        a station name.

    Returns
    -------
    list of dict
        List of station status JSONs from the Divvy API response
    """
    possible = []
    first = speech_to_text(first)
    if not second:
        # Search the "location" field.
        for sta in stations:
            if first == sta['stationName'].lower():
                return [sta]
        # Search the "address" field.
        for sta in stations:
            if first in sta['stAddress1'].lower():
                possible.append(sta)

        if not possible and not exact:
            # Do fuzzy matching if we couldn't find an exact match.
            # Note default "cutoff=0.6" in `get_close_matches`.
            st_names = {s['stationName'].lower(): s for s in stations}
            best_names = difflib.get_close_matches(first, st_names, n=1)
            if not best_names:
                log.info("Didn't find a match for station \"%s\"." % first)
                return []
            else:
                log.info('Heard "%s", matching with station "%s".' %
                         (first, best_names[0]))
                return [st_names[best_names[0]]]
    else:
        second = speech_to_text(second)
        for sta in stations:
            address = sta['stAddress1'].lower()
            name = sta['stationName'].lower()
            if ((first in address and second in address) or
                    (first in name and second in name)):
                possible.append(sta)

        if not possible and not exact:
            # If there's no exact match on the fragments,
            # then do fuzzy matching on the combination.
            # Try each ordering of street names.
            order_one = matching_station_list(
                stations, '%s and %s' % (first, second), exact=False)
            order_two = matching_station_list(
                stations, '%s and %s' % (second, first), exact=False)

            # Pick the best of this pair
            score_one, score_two = 0, 0
            if order_one:
                score_one = difflib.SequenceMatcher(
                    None, '%s and %s' % (first, second),
                    order_one[0]['stationName']).ratio()
            if order_two:
                score_two = difflib.SequenceMatcher(
                    None, '%s and %s' % (second, first),
                    order_two[0]['stationName']).ratio()
            log.info('Heard names "%s" and "%s". Fuzzy match in '
                     'forward order: %d; reverse %d' %
                     (first, second, score_one, score_two))
            if score_one > score_two:
                return order_one
            elif order_two:
                # Make sure the second ordering had a
                # match before returning it.
                return order_two
            else:
                # If no station names look like the user request,
                # return an empty list.
                return []

    return possible


def find_station(stations, first, second=None, exact=False):
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
    exact : bool, optional
        If True, require exact string matches. Otherwise
        always return at least one station name. If no
        exact match, return the closest string match.

    Returns
    -------
    dict
        A single station status JSON from the Divvy API response

    Raises
    ------
    AmbiguousStationError if `first` and `second`
        don't uniquely specify a station
    """
    possible = matching_station_list(stations, first, second, exact=exact)
    return _check_possible(possible, first, second)


def speech_to_text(address):
    """Standardize speech input to look like Divvy station names
    """
    # Add a space, since we look for spaces after abbreviations
    address = address.lower() + ' '
    address = address.replace(' and ', ' & ')

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
    for ab, full in DIRECTIONS.iteritems():
        address = address.replace(ab, full)

    return address.strip()


def get_stations(divvy_api):
    resp = requests.get(divvy_api)
    stations = resp.json()['stationBeanList']

    return stations
