"""Functions having to do with physical location
"""
import math

import requests

from divvy import config


def get_lat_lon(addr_string):
    """Convert an address to lat/lon

    Use the Google Maps Geocoding API to convert an
    address string (e.g. 123 North State Street)
    to a latitude and longitude. The Google API will
    also return a standarized address string.
    It's pretty good at spelling correction if the street
    name gets garbled by the speech-to-text engine.

    Parameters
    ----------
    addr_string: str
        String address, e.g. "123 North State Street, Chicago, IL".
        The zip code can help disambiguate, but generally
        isn't necessary. It's strongly advised to have
        either the city or the zip: otherwise, Google will
        guess what city you mean, often incorrectly.

    Returns
    -------
    (lat, lon, addr): (float, float, str)
        Latitude (as a float), longitude (as a float), and the
        standardized form of the input address

    See Also
    --------
    https://developers.google.com/maps/documentation/geocoding/
    """
    addr_string = addr_string.replace(' ', '+')
    query = 'json?address=' + addr_string + '&key=' + config.maps_api_key

    resp = requests.get(config.maps_api + query)
    if resp.status_code != 200:
        raise RuntimeError('Error getting map coordinates: ' + resp.status)

    lat = resp.json()['results'][0]['geometry']['location']['lat']
    lon = resp.json()['results'][0]['geometry']['location']['lng']
    addr = resp.json()['results'][0]['formatted_address']

    return lat, lon, addr


def distance(lat1, lon1, lat2, lon2):
    """Calculate the great circle distance between two locations

    Assumes the locations are on Earth.
    Assumes a spherical Earth with radius equal to Earth's average radius.

    Parameters
    ----------
    lat1, lon1 : float, float
        Origin longitude and latitude in decimal degrees
    lat2, lon2 : float, float
        Destination longitude and latitude in decimal degrees

    Returns
    -------
    float
        Distance between the two points in meters

    Notes
    -----
    Uses the haversine formula:

    a = sin^2(\Delta \phi /2) + cos(\phi_1) * cos(\phi_2) * sin^2(\Delta \lambda /2)
    c = 2 * atan2( \sqrt(a), \sqrt(1-a))
    d = R * c
    where \phi is latitude, \lambda is longitude, R is earth's radius (mean radius = 6,371 km)
    """
    lon1, lat1 = math.radians(lon1), math.radians(lat1)
    lon2, lat2 = math.radians(lon2), math.radians(lat2)
    a = (math.sin((lat2 - lat1) / 2) ** 2 +
         math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    d = 6371000 * c

    return d


def station_from_lat_lon(lat, lon, stations, n_nearest=3):
    """Find the nearest station(s) to a given location

    Parameters
    ----------
    lat : float or str
        Latitude
    lon : float or str
        Longitude
    stations : list of dict
        JSON following the Divvy "stationBeanList" schema.
        Each entry in the list must have
        "lat" and "lon" keys.
    n_nearest : int, optional
        Return this many stations, ordered from nearest to furthest

    Returns
    -------
    list of dict
        A list of `n_nearest` Divvy stations
    """
    lat, lon = float(lat), float(lon)
    distances = [(distance(lat, lon, st['lat'], st['lon']), st)
                 for st in stations
                 if (st['is_renting'] and st['is_installed'])]
    distances = sorted(distances)
    return [pair[1] for pair in distances[:n_nearest]]
