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
import logging
import reply

from divvy import config, database, geocoding

log = logging.getLogger(__name__)


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
        if not intent['slots']['bikes_or_docks'].get('value'):
            # If something went wrong understanding the bike/dock
            # value, fall back on the status check.
            return check_status(intent,
                                location.get_stations(config.divvy_api))
        else:
            return check_bikes(intent,
                               location.get_stations(config.divvy_api))
    elif intent['name'] == 'CheckStatusIntent':
        return check_status(intent, location.get_stations(config.divvy_api))
    elif intent['name'] == 'ListStationIntent':
        return list_stations(intent, location.get_stations(config.divvy_api))
    elif intent['name'] == 'CheckCommuteIntent':
        return check_commute(intent, session)
    elif intent['name'] == 'AddAddressIntent':
        return add_address(intent, session)
    elif intent['name'] == 'CheckAddressIntent':
        return check_address(intent, session)
    elif intent['name'] == 'RemoveAddressIntent':
        return remove_address(intent, session)
    elif intent['name'] == 'AMAZON.NextIntent':
        # This is part of the AddAddressIntent dialog
        if session.get('attributes', {}).get('add_address') and \
                    session['attributes']['next_step'] == 'zip':
            session['attributes']['next_step'] = 'check_address'
            session['attributes']['zip_code'] = ''
            return add_address(intent, session)
        else:
            return reply.build("Sorry, I don't know what you mean.",
                               is_end=False)
    elif intent['name'] == 'AMAZON.YesIntent':
        # This is part of the AddAddressIntent or
        # RemoveAddressIntent dialog
        if session.get('attributes', {}).get('add_address') and \
                    session['attributes']['next_step'] == 'store_address':
            return store_address(intent, session)
        elif session.get('attributes', {}).get('remove_address'):
            return remove_address(intent, session)
        else:
            return reply.build("Sorry, I don't know what you mean.",
                               is_end=False)
    elif intent['name'] == 'AMAZON.NoIntent':
        # This is part of the AddAddressIntent or
        # RemoveAddressIntent dialog
        if session.get('attributes', {}).get('add_address') and \
                    session['attributes']['next_step'] == 'store_address':
            session['attributes']['next_step'] = 'zip'
            return reply.build("Okay, what street number and name do you want?",
                               reprompt="What's the street number and name?",
                               persist=session['attributes'],
                               is_end=False)
        elif session.get('attributes', {}).get('remove_address'):
            return remove_address(intent, session)
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
    stations : list of dict
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
    if slots.get('station_name', {}).get('value'):
        name = slots['station_name']['value']
        if ' and ' in name:
            # Try to be robust to re-orderings of street names.
            tokens = name.split(' and ')
            if len(tokens) != 2:
                first, second = name, None
            else:
                first, second = name.split(' and ')
        else:
            first, second = name, None
    else:
        first = slots['first_street']['value']
        second = slots.get('second_street', {}).get('value')
    sta = location.find_station(stations, first, second, exact=False)
    return sta


def check_commute(intent, session):
    """Checks nearest station status for home and work

    The user must previously have stored both addresses
    in the database.

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
    user_data = database.get_user_data(session['user']['userId'])
    if not user_data:
        return reply.build("I don't remember any of your addresses.",
                           is_end=True)
    stations = location.get_stations(config.divvy_api)
    utter = []
    first_phrase = True
    for which, av_key, av_name in \
          [('home', 'availableBikes', 'bikes'),
           ('destination', 'availableDocks', 'docks')]:
        if user_data.get(which):
            lat = user_data[which]['latitude']
            lon = user_data[which]['longitude']
            nearest_st = geocoding.station_from_lat_lon(
                  lat, lon, stations, n_nearest=2)

            n_thing = nearest_st[0][av_key]
            st_name = location.text_to_speech(nearest_st[0]['stationName'])
            av_slice = slice(0, (-1 if n_thing == 1 else None))  # singular?
            phrase = ('%d %s at the %s station' %
                      (n_thing, av_name[av_slice], st_name))
            if first_phrase:
                verb = 'is' if n_thing == 1 else 'are'
                phrase = ('There %s ' % verb) + phrase
            utter.append(phrase)
            first_phrase = False

            if n_thing < 3:
                # If there's not many bikes/docks at the best station,
                # refer users to the next nearest station.
                n_thing = nearest_st[1][av_key]
                av_slice = slice(0, (-1 if n_thing == 1 else None))  # singular?
                st_name = location.text_to_speech(nearest_st[1]['stationName'])
                utter[-1] += (' with %d %s at the next nearest station, %s' %
                              (n_thing, av_name[av_slice], st_name))

    utter = '%s.' % ' and '.join(utter)
    return reply.build(utter, card_text=utter, is_end=True)


def remove_address(intent, session):
    """Allow users to delete stored addresses

    Parameters
    ----------
    intent : dict
        JSON following the Alexa "IntentRequest"
        schema with name "RemoveAddressIntent" or
        with a "remove_address" flag in the
        `session['attributes']` dictionary
    session : dict
        JSON following the Alexa "Session" schema

    Returns
    -------
    dict
        JSON following the Alexa reply schema
    """
    sess_data = session.setdefault('attributes', {})
    sess_data['remove_address'] = True

    # Retrieve stored data just to check if it exists or not.
    user_data = database.get_user_data(session['user']['userId'])
    if not user_data:
        return reply.build("I already don't remember any addresses for you.",
                           is_end=True)
    elif sess_data.get('awaiting_confirmation'):
        # The user has requested removal and
        # we requested confirmation
        if intent['name'] == 'AMAZON.NoIntent':
            return reply.build("Okay, keeping your stored addresses.",
                               is_end=True)
        elif intent['name'] == 'AMAZON.YesIntent':
            succ = database.delete_user(session['user']['userId'])
            if succ:
                return reply.build("Okay, I've forgotten all the addresses "
                                   "you told me.", is_end=True)
            else:
                # Only get here if the database interaction fails somehow
                return reply.build("Huh. Something went wrong.", is_end=True)
        else:
            # Shouldn't ever get here.
            return reply.build("Sorry, I don't know what you mean.",
                               is_end=False)
    else:
        # Prompt the user for confirmation of data removal.
        sess_data['awaiting_confirmation'] = True
        return reply.build("Do you really want me to forget the addresses "
                           "you gave me?",
                           reprompt='Say "yes" to delete all stored addresses '
                                    'or "no" to not change anything.',
                           persist=sess_data,
                           is_end=False)


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
            return reply.build("Okay, storing your home address. "
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
    This is the endpoint of the AddAddressIntent dialog
    """
    sess_data = session.setdefault('attributes', {})
    if not sess_data.get('add_address') and \
          not sess_data['next_step'] == 'store_address':
        raise RuntimeError('Something went wrong.')

    data = {sess_data['which']: dict(latitude=str(sess_data['lat']),
                                     longitude=str(sess_data['lon']),
                                     address=str(sess_data['full_address']))}
    success = database.update_user_data(session['user']['userId'], **data)
    if not success:
        return reply.build("I'm sorry, something went wrong and I could't "
                           "store the address.", is_end=True)
    else:
        return reply.build("Okay, I've saved your %s "
                           "address." % sess_data['which'],
                           is_end=True)


def check_address(intent, session):
    """Look up an address stored under this user's ID

    Parameters
    ----------
    intent : dict
        JSON following the Alexa "IntentRequest"
        schema with name "CheckAddressIntent"
    session : dict
        JSON following the Alexa "Session" schema

    Returns
    -------
    dict
        JSON following the Alexa reply schema
    """
    user_data = database.get_user_data(session['user']['userId'])
    if not user_data:
        return reply.build("I don't remember any of your addresses.",
                           is_end=True)

    which = intent.get('slots', {}).get('which_address', {}).get('value')
    addr = user_data.get(which)
    if not addr:
        return reply.build("I don't know your %s address." % which)
    else:
        return reply.build("Your %s address is set to %s." %
                           (which, location.text_to_speech(addr['address'])))


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
        return reply.build(err.message,
                           card_text=err.message,
                           is_end=True)
    except:  # NOQA
        log.exception('Failed to get a station.')
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

    verb = 'is' if n_things == 1 else 'are'
    b_or_d = b_or_d[:-1] if n_things == 1 else b_or_d  # singular?
    text = ("There %s %d %s available at the %s station%s"
            % (verb, n_things, b_or_d,
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
        return reply.build(err.message,
                           card_text=err.message,
                           is_end=True)
    except:  # NOQA
        log.exception('Failed to get a station.')
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
    text = ("There %s %d bike%s and %d dock%s "
            "at the %s station."
            % ("is" if n_bike == 1 else "are",
               n_bike, "" if n_bike == 1 else "s",
               n_dock, "" if n_dock == 1 else "s",
               sta_name))
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
    possible = location.matching_station_list(stations, street_name,
                                              exact=True)

    if len(possible) == 0:
        return reply.build("I didn't find any stations on %s." % street_name)
    elif len(possible) == 1:
        sta_name = location.text_to_speech(possible[0]['stationName'])
        return reply.build("There's only one: the %s "
                           "station." % sta_name,
                           card_text="One station on %s: %s" % (street_name,
                                                                sta_name),
                           is_end=False)
    else:
        last_name = location.text_to_speech(possible[-1]['stationName'])
        speech = "There are %d stations on %s: " % (len(possible),
                                                    street_name)
        speech += (', '.join([location.text_to_speech(p['stationName'])
                              for p in possible[:-1]]) +
                   ', and %s' % last_name)
        return reply.build(speech, card_text=speech, is_end=False)
