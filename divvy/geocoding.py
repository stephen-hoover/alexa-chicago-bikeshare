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
