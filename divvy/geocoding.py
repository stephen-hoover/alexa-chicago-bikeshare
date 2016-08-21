from __future__ import print_function, division
import math

import requests

from divvy import config


def get_lat_lon(addr_string):
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
        "latitude" and "longitude" keys.
    n_nearest : int, optional
        Return this many stations, ordered from nearest to furthest

    Returns
    -------
    list of dict
        A list of `n_nearest` Divvy stations
    """
    lat, lon = float(lat), float(lon)
    distances = [(distance(lat, lon, st['latitude'], st['longitude']), st)
                 for st in stations if st['is_renting']]
    distances = sorted(distances)
    return [pair[1] for pair in distances[:n_nearest]]
