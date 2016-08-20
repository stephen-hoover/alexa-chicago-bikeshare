"""Handle requests sent by Echo

https://developer.amazon.com/public/solutions/alexa/alexa-skills-kit/docs/alexa-skills-kit-interface-reference
The requests are JSON formatted as:
{
  "version": "string",
  "session": {
    "new": boolean,
    "sessionId": "string",
    "application": {
      "applicationId": "string"
    },
    "attributes": {
      "string": object
    },
    "user": {
      "userId": "string",
      "accessToken": "string"
    }
  },
  "request": object
}

There are three kinds of requests: IntentRequest, LaunchRequest, and SessionEndedRequest

IntentRequest:
{
  "type": "IntentRequest",
  "requestId": "string",
  "timestamp": "string",
  "intent": {
    "name": "string",
    "slots": {
      "string": {
        "name": "string",
        "value": "string"
      }
    }
  }
}
"""
from __future__ import print_function, division
import location
import reply

from divvy import config, database, geocoding


def intent(req, session):
    """Identify and handle IntentRequest objects

    Parameters
    ----------
    req : dict
        JSON following the Alexa "IntentRequest" schema
    session : dict
        JSON following the Alexa "Session" schema

    Returns
    -------
    dict
        JSON following the Alexa reply schema
    """
    intent = req['intent']

    if intent['name'] == 'CheckBikeIntent':
        return check_bikes(intent, location.get_stations(config.divvy_api))
    elif intent['name'] == 'CheckStatusIntent':
        return check_status(intent, location.get_stations(config.divvy_api))
    elif intent['name'] == 'ListStationIntent':
        return list_stations(intent, location.get_stations(config.divvy_api))
    elif intent['name'] == 'AddAddressIntent':
        return add_address(intent, session)
    elif intent['name'] == 'AMAZON.NextIntent':
        if session.get('attributes', {}).get('add_address') and \
                    session['attributes']['next_step'] == 'zip':
            session['attributes']['next_step'] = 'check_address'
            session['attributes']['zip_code'] = ''
            return add_address(intent, session)
        else:
            return reply.build("Sorry, I don't know what you mean.",
                               is_end=False)
    elif intent['name'] == 'AMAZON.YesIntent':
        if session.get('attributes', {}).get('add_address') and \
                    session['attributes']['next_step'] == 'store_address':
            return store_address(intent, session)
        else:
            return reply.build("Sorry, I don't know what you mean.",
                               is_end=False)
    elif intent['name'] == 'AMAZON.NoIntent':
        if session.get('attributes', {}).get('add_address') and \
                    session['attributes']['next_step'] == 'store_address':
            session['attributes']['next_step'] = 'zip'
            return reply.build("Okay, what street number and name do you want?",
                               reprompt="What's the street number and name?",
                               persist=session['attributes'],
                               is_end=False)
        else:
            return reply.build("Sorry, I don't know what you mean.",
                               is_end=False)
    elif intent['name'] in ['AMAZON.StopIntent', 'AMAZON.CancelIntent']:
        return reply.build("Okay, exiting.", is_end=True)
    elif intent['name'] == 'AMAZON.HelpIntent':
        return reply.build("You can ask me how many bikes or docks are "
                           "at a specific station, or else just ask the status of a "
                           "station. Use the Divvy station name, such as "
                           "\"Milwaukee Avenue and Rockwell Street\". If you only "
                           "remember one cross-street, you can ask me to list all "
                           "stations on a particular street.", is_end=False)
    else:
        return reply.build("I didn't understand that.", is_end=False)


def _station_from_intent(intent, stations):
    """Given a request and a list of stations, find the desired station

    Parameters
    ----------
    intent : dict
        JSON following the Alexa "IntentRequest"
        schema with name "CheckBikeIntent"
    stations : dict
        JSON following the Divvy "stationBeanList" schema

    Returns
    -------
    dict
        A single station information JSON from the Divvy API response

    Raises
    ------
    AmbiguousStationError if the name(s) in the request
        don't uniquely specify a station
    """
    slots = intent['slots']
    if slots.get('special_name', {}).get('value'):
        first = slots['special_name']['value']
        second = None
    else:
        first = slots['first_street']['value']
        second = slots.get('second_street', {}).get('value')
    sta = location.find_station(stations, first, second)
    return sta


def add_address(intent, session):
    """Controls a dialog which allows users to
    permanently store an address

    Parameters
    ----------
    intent : dict
        JSON following the Alexa "IntentRequest"
        schema with name "AddAddressIntent"
    session : dict
        JSON following the Alexa "Session" schema

    Returns
    -------
    dict
        JSON following the Alexa reply schema
    """
    slots = intent.get('slots')
    sess_data = session.setdefault('attributes', {})
    sess_data['add_address'] = True
    sess_data.setdefault('next_step', 'which')
    if sess_data['next_step'] == 'which':
        if slots['which_address'].get('value') in ['here', 'home', 'origin']:
            sess_data['which'] = 'home'
            sess_data['next_step'] = 'num_and_name'
            return reply.build("Okay, storing this address. "
                               "What's the street number and name?",
                               reprompt="What's the street number and name?",
                               persist=sess_data,
                               is_end=False)
        elif slots['which_address'].get('value') in ['there', 'work',
                                                     'school', 'destination']:
            sess_data['which'] = 'destination'
            sess_data['next_step'] = 'num_and_name'
            return reply.build("Okay, storing your destination address. "
                               "What's the street number and name?",
                               reprompt="What's the street number and name?",
                               persist=sess_data,
                               is_end=False)
        else:
            sess_data['next_step'] = 'which'
            return reply.build("Would you like to set the address here or at "
                               "your destination?",
                               reprompt='You can say "here" or "destination".',
                               persist=sess_data,
                               is_end=False)
    elif sess_data['next_step'] == 'num_and_name':
        if slots['address_street'].get('value'):
            num = slots['address_number'].get('value', '')
            direction = slots['direction'].get('value', '')
            st = slots['address_street'].get('value', '')
            sess_data['spoken_address'] = (('%s %s %s' %
                                            (num, direction, st))
                                           .replace('  ', ' '))
            sess_data['next_step'] = 'zip'
            return reply.build("Got it. Now what's the zip code?",
                               reprompt="What's the zip code?",
                               persist=sess_data,
                               is_end=False)
        else:
            return reply.build("Please say a street number and street name.",
                               reprompt="What's the street number and name?",
                               persist=sess_data,
                               is_end=False)
    elif sess_data['next_step'] == 'zip':
        if not slots['address_number'].get('value'):
            return reply.build("I need the zip code now.",
                               reprompt="What's the zip code?",
                               persist=sess_data,
                               is_end=False)
        sess_data['next_step'] = 'check_address'
        sess_data['zip_code'] = slots['address_number']['value']
        return add_address(intent, session)
    elif sess_data['next_step'] == 'check_address':
        if sess_data['zip_code']:
            addr = '%s, %s' % (sess_data['spoken_address'],
                               sess_data['zip_code'])
        else:
            addr = '%s, Chicago, IL' % sess_data['spoken_address']
        lat, lon, full_address = geocoding.get_lat_lon(addr)
        sess_data['lat'], sess_data['lon'] = lat, lon
        sess_data['full_address'] = full_address
        sess_data['next_step'] = 'store_address'
        return reply.build("Thanks! Do you want to set "
                           "your %s address to %s?" %
                           (sess_data['which'],
                            location.text_to_speech(full_address)),
                           reprompt="Is that the correct address?",
                           persist=sess_data,
                           is_end=False)
    else:
        raise NotImplementedError


def store_address(intent, session):
    """Permanently store this user's address in the database.
    """
    sess_data = session.setdefault('attributes', {})
    if not sess_data.get('add_address') and \
          not sess_data['next_step'] == 'store_address':
        raise RuntimeError('Something went wrong.')

    data = {sess_data['which']: dict(latitude=sess_data['lat'],
                                     longitude=sess_data['lon'],
                                     address=sess_data['full_address'])}
    success = database.update_user_data(session['user']['userId'], **data)
    if not success:
        return reply.build("I'm sorry, something went wrong and I could't "
                           "store the address.", is_end=True)
    else:
        return reply.build("Okay, I've saved your %s "
                           "address." % sess_data['which'],
                           is_end=True)


def check_bikes(intent, stations):
    """Handle a CheckBikeIntent; return number of bikes at a station

    Parameters
    ----------
    intent : dict
        JSON following the Alexa "IntentRequest"
        schema with name "CheckBikeIntent"
    stations : dict
        JSON following the Divvy "stationBeanList" schema

    Returns
    -------
    dict
        JSON following the Alexa reply schema
    """
    try:
        sta = _station_from_intent(intent, stations)
    except location.AmbiguousStationError as err:
        return reply.build(err.message, is_end=True)
    except:  # NOQA
        return reply.build("I'm sorry, I didn't understand that.",
                           is_end=False)

    if not sta['is_renting']:
        postamble = ", but the station isn't renting right now."
    else:
        postamble = "."

    n_bike = sta['availableBikes']
    n_dock = sta['availableDocks']
    b_or_d = intent['slots']['bikes_or_docks']['value']
    n_things = n_bike if b_or_d == 'bikes' else n_dock

    text = ("There are %d %s available at the %s station%s"
            % (n_things, b_or_d,
               location.text_to_speech(sta['stationName']),
               postamble))
    return reply.build(text, card_text=text, is_end=True)


def check_status(intent, stations):
    """Handle a CheckStatusIntent:
    return number of bikes and docks at a station

    Parameters
    ----------
    intent : dict
        JSON following the Alexa "IntentRequest"
        schema with name "CheckBikeIntent"
    stations : dict
        JSON following the Divvy "stationBeanList" schema

    Returns
    -------
    dict
        JSON following the Alexa reply schema
    """
    try:
        sta = _station_from_intent(intent, stations)
    except location.AmbiguousStationError as err:
        return reply.build(err.message, is_end=True)
    except:  # NOQA
        return reply.build("I'm sorry, I didn't understand that.",
                           is_end=False)

    sta_name = location.text_to_speech(sta['stationName'])
    if not sta['is_renting']:
        return reply.build("The %s station isn't "
                           "renting right now." % sta_name,
                           is_end=True)
    if not sta['statusValue'] == 'In Service':
        return reply.build("The %s station is %s."
                           % (sta_name, sta['statusValue']),
                           is_end=True)

    n_bike = sta['availableBikes']
    n_dock = sta['availableDocks']
    text = ("There are %d bikes and %d docks "
            "at the %s station."
            % (n_bike, n_dock, sta_name))
    return reply.build(text, card_text=text, is_end=True)


def list_stations(intent, stations):
    """Find all stations on a given street

    Parameters
    ----------
    intent : dict
        JSON following the Alexa "IntentRequest"
        schema with name "ListStationIntent"
    stations : dict
        JSON following the Divvy "stationBeanList" schema

    Returns
    -------
    dict
        JSON following the Alexa reply schema
    """
    street_name = intent['slots']['street_name']['value']
    possible = location.matching_station_list(stations, street_name)

    if len(possible) == 0:
        return reply.build("I didn't find any stations on %s." % street_name)
    elif len(possible) == 1:
        sta_name = location.text_to_speech(possible[0]['stationName'])
        return reply.build("There's only one: the %s "
                           "station." % sta_name)
    else:
        last_name = location.text_to_speech(possible[-1]['stationName'])
        speech = (', '.join([location.text_to_speech(p['stationName'])
                             for p in possible[:-1]]) +
                  ', and %s' % last_name)
        return reply.build("There are %d stations on %s: %s."
                           "" % (len(possible), street_name, speech))
