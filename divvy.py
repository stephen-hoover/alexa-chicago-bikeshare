import reply


class AmbiguousStationError(ValueError):
    pass


def check_possible(possible, first, second=None):
    if len(possible) == 1:
        return possible[0]
    elif not possible:
        if second:
            raise AmbiguousStationError("I couldn't find a station at %s and %s." % (first, second))
        else:
            raise AmbiguousStationError("I couldn't find a station at %s." % first)
    else:
        possible_list = ', '.join(possible[:-1]) + ', or %s' % possible[-1]
        raise AmbiguousStationError("I don't know if you mean %s." % possible_list)


def find_station(stations, first, second=None):
    possible = []
    first = first.lower()
    if not second:
        # Search the "location" field.
        for sta in stations:
            if sta['location'] and first in sta['location'].lower():
                return sta
        # Search the "address" field.
        for sta in stations:
            if first in sta['stAddress1'].lower():
                possible.append(sta)

        return check_possible(possible, first, second)
    else:
        second = second.lower()
        for sta in stations:
            if first in sta['stAddress1'] and second in sta['stAddress1']:
                possible.append(sta)

        return check_possible(possible, first, second)

                
def format_address(address):
    """Standardize speech input to look like Divvy station names
    """
    address = address.lower()
    address = address.replace('and', '&')

    abbrev = {'street': 'st', 'lane': 'ln', 'avenue': 'av'}
    for full, ab in abbrev.iteritems():
        address = address.replace(full, ab)

    return address


def get_stations(divvy_api):
    resp = requests.get(divvy_api)
    stations = resp.json()['stationBeanList']

    return stations
