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
import difflib
import logging
import os
import reply
import time

import location
from divvy import config, geocoding
if config.db_type == 's3':
    import s3_database as database
elif config.db_type == 'dynamo':
    import s3_database as database
else:
    raise ImportError("Unrecognized database type "
                      "in config: %s" % config.db_type)

log = logging.getLogger(__name__)

ORIGIN_NAMES = ['here', 'home', 'origin']
DEST_NAMES = ['there', 'work', 'school', 'destination']

# The following intents could be part of the AddAddress dialog.
ADD_ADDRESS_INTENTS = ['AddAddressIntent',
                       'AMAZON.NextIntent',
                       'AMAZON.YesIntent',
                       'AMAZON.NoIntent',
                       'AMAZON.StopIntent',
                       'AMAZON.CancelIntent']

# These intents might be part of the RemoveAddress dialog
REMOVE_ADDRESS_INTENTS = ['RemoveAddressIntent',
                          'AMAZON.YesIntent',
                          'AMAZON.NoIntent',
                          'AMAZON.StopIntent',
                          'AMAZON.CancelIntent']

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
    if session.setdefault('attributes', {}) is None:
        # Ensure that there's always a dictionary under "attributes".
        session['attributes'] = {}

    # If the user has already opened a dialog, handle incorrect
    # Intents from Alexa due to misunderstandings or user error.
    if session['attributes'].get('add_address') and \
            not intent['name'] in ADD_ADDRESS_INTENTS:
        # Try to recover if Alexa misunderstood
        # an address as a station name.
        if intent['name'] == 'CheckStatusIntent' and \
                intent['slots'].get('station_name', {}).get('value'):
            intent['name'] = 'AddAddressIntent'
            intent['slots'].setdefault('address_street', {})['value'] = \
                intent['slots']['station_name']['value']
        else:
            return reply.build("I didn't understand that as an address. "
                               "Please provide an address, such as "
                               "\"123 north State Street\".",
                               reprompt="What's the street number and name?",
                               persist=session['attributes'],
                               is_end=False)
    elif session['attributes'].get('remove_address') and \
            not intent['name'] in REMOVE_ADDRESS_INTENTS:
        # If the user wanted to remove an address, but didn't
        # give an intelligible response when we requested
        # confirmation, then assume the answer is no.
        intent['name'] = 'AMAZON.NoIntent'

    # Dispatch each Intent to the correct handler.
    if intent['name'] == 'CheckBikeIntent':
        if not intent['slots']['bikes_or_docks'].get('value'):
            # If something went wrong understanding the bike/dock
            # value, fall back on the status check.
            return check_status(intent, session)
        else:
            return check_bikes(intent, session)
    elif intent['name'] == 'CheckStatusIntent':
        return check_status(intent, session)
    elif intent['name'] == 'ListStationIntent':
        return list_stations(intent, session)
    elif intent['name'] == 'CheckCommuteIntent':
        return check_commute(intent, session)
    elif intent['name'] == 'AddAddressIntent':
        return add_address(intent, session)
    elif intent['name'] == 'CheckAddressIntent':
        return check_address(intent, session)
    elif intent['name'] == 'RemoveAddressIntent':
        return remove_address(intent, session)
    elif intent['name'] == 'AMAZON.NextIntent':
        return next_intent(intent, session)
    elif intent['name'] == 'AMAZON.YesIntent':
        return yes_intent(intent, session)
    elif intent['name'] == 'AMAZON.NoIntent':
        return no_intent(intent, session)
    elif intent['name'] in ['AMAZON.StopIntent', 'AMAZON.CancelIntent']:
        return reply.build("Okay, exiting.", is_end=True)
    elif intent['name'] == 'AMAZON.HelpIntent':
        return reply.build("You can ask me how many bikes or docks are "
                           "at a specific station, or else just ask the "
                           "status of a station. Use the %s station "
                           "name, such as \"%s\". "
                           "If you only remember one cross-street, you "
                           "can ask me to list all stations on a particular "
                           "street. If you've told me to \"add an address\", "
                           "I can remember that and use it when you "
                           "ask me to \"check my commute\". "
                           "What should I do?" %
                           (config.network_name, config.sample_station),
                           persist=session['attributes'],
                           is_end=False)
    else:
        return reply.build("I didn't understand that. Try again?",
                           persist=session['attributes'],
                           is_end=False)


def _time_string():
    """Return a string representing local time"""
    os.environ['TZ'] = config.time_zone
    time.tzset()
    return time.asctime()


def _station_from_intent(intent, stations):
    """Given a request and a list of stations, find the desired station

    Parameters
    ----------
    intent : dict
        JSON following the Alexa "IntentRequest"
        schema with name "CheckBikeIntent"
    stations : list of dict
        JSON following the combined station_info and status GBFS schema

    Returns
    -------
    dict
        A single station information JSON from the bikeshare API response

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


def next_intent(intent, session):
    """Handle the AMAZON.NextIntent

    This should only come up as part of the AddAddressIntent dialog."""
    # This is part of the AddAddressIntent dialog
    if session.get('attributes', {}).get('add_address') and \
                session['attributes']['next_step'] == 'zip':
        session['attributes']['next_step'] = 'check_address'
        session['attributes']['zip_code'] = ''
        return add_address(intent, session)
    else:
        return reply.build("Sorry, I don't know what you mean. Try again?",
                           persist=session.get('attributes', {}),
                           is_end=False)


def yes_intent(intent, session):
    """Handle the AMAZON.YesIntent

    This is expected to be part of the AddAddressIntent
    or RemoveAddressIntent dialog"""
    if session.get('attributes', {}).get('add_address') and \
                session['attributes']['next_step'] == 'store_address':
        return store_address(intent, session)
    elif session.get('attributes', {}).get('remove_address'):
        return remove_address(intent, session)
    else:
        return reply.build("Sorry, I don't know what you mean. Try again?",
                           persist=session.get('attributes', {}),
                           is_end=False)


def no_intent(intent, session):
    """Handle the AMAZON.NoIntent

    This is expected to be part of the AddAddressIntent
    or RemoveAddressIntent dialog"""
    if session.get('attributes', {}).get('add_address') and \
                session['attributes']['next_step'] == 'store_address':
        session['attributes']['next_step'] = 'num_and_name'
        return reply.build("Okay, what street number and name do you want?",
                           reprompt="What's the street number and name?",
                           persist=session['attributes'],
                           is_end=False)
    elif session.get('attributes', {}).get('remove_address'):
        return remove_address(intent, session)
    else:
        return reply.build("Sorry, I don't know what you mean. Try again?",
                           persist=session.get('attributes', {}),
                           is_end=False)


def _get_bikes_available(sta):
    """Given a GBFS station status blob, return the number of bikes"""
    # 'num_ebikes_available" is not part of the GBFS spec, but it appears
    # in the Divvy API response
    return sta['num_bikes_available'] + sta.get('num_ebikes_available', 0)


def _get_docks_available(sta):
    """Given a GBFS station status blob, return the number of docks"""
    return sta['num_docks_available']


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
        return reply.build("I don't remember any of your addresses. "
                           "You can ask me to \"save an address\" "
                           "if you want me to be able to check "
                           "on your daily commute.",
                           is_end=True)
    stations = location.get_stations(config.bikes_api)
    utter = ''
    card_text = ['Checked at %s' % _time_string()]
    first_phrase = True
    for which, av_func, av_name in \
          [('origin', _get_bikes_available, 'bikes'),
           ('destination', _get_docks_available, 'docks')]:
        if user_data.get(which):
            lat = user_data[which]['latitude']
            lon = user_data[which]['longitude']
            nearest_st = geocoding.station_from_lat_lon(
                  lat, lon, stations, n_nearest=2)

            n_thing = av_func(nearest_st[0])
            st_name = location.text_to_speech(nearest_st[0]['name'])
            av_slice = slice(0, (-1 if n_thing == 1 else None))  # singular?
            phrase = ('%d %s at the %s station' %
                      (n_thing, av_name[av_slice], st_name))
            if first_phrase:
                verb = 'is' if n_thing == 1 else 'are'
                phrase = ('There %s ' % verb) + phrase
            else:
                phrase = ', and ' + phrase
            utter += phrase
            first_phrase = False
            card_text.append("%s: %d %s at %s" %
                             (which.capitalize(),
                              n_thing,
                              av_name[av_slice],
                              nearest_st[0]['name']))

            if n_thing < 3:
                # If there's not many bikes/docks at the best station,
                # refer users to the next nearest station.
                n_thing = av_func(nearest_st[1])
                av_slice = slice(0, (-1 if n_thing == 1 else None))  # singular?
                st_name = location.text_to_speech(nearest_st[1]['name'])
                utter += (', and %d %s at the next nearest station, %s. ' %
                          (n_thing, av_name[av_slice], st_name))
                first_phrase = True  # Start a new sentence next time
                card_text.append("Next Best %s: %d %s at %s" %
                                 (which.capitalize(),
                                  n_thing,
                                  av_name[av_slice],
                                  nearest_st[1]['name']))

    return reply.build(utter,
                       card_title=("Your %s Commute Status" %
                                   config.network_name),
                       card_text='\n'.join(card_text),
                       is_end=True)


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
            return reply.build("Sorry, I don't know what you mean. "
                               "Try again?", persist=sess_data, is_end=False)
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
        if slots['which_address'].get('value') in ORIGIN_NAMES:
            sess_data['which'] = 'origin'
            sess_data['next_step'] = 'num_and_name'
            return reply.build("Okay, storing your origin address. "
                               "What's the street number and name?",
                               reprompt="What's the street number and name?",
                               persist=sess_data,
                               is_end=False)
        elif slots['which_address'].get('value') in DEST_NAMES:
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
            num = slots.get('address_number', {}).get('value', '')
            direction = slots.get('direction', {}).get('value', '')
            st = slots.get('address_street', {}).get('value', '')
            sess_data['spoken_address'] = (('%s %s %s' %
                                            (num, direction, st))
                                           .replace('  ', ' ')
                                           .strip())
            sess_data['next_step'] = 'zip'
            return reply.build("Got it. Now what's the zip code? "
                               "You can tell me "
                               "to skip it if you don't know.",
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
            # Assume that network subscribers are always interested
            # in in-state addresses, but not necessarily in the city.
            addr = '%s, %s, %s' % (sess_data['spoken_address'],
                                   config.default_state,
                                   sess_data['zip_code'])
        else:
            # Without a zip code, assume the network's home city
            # to add necessary specificity.
            addr = '%s, %s, %s' % (sess_data['spoken_address'],
                                   config.default_city,
                                   config.default_state)
        lat, lon, full_address = geocoding.get_lat_lon(addr)
        if full_address.endswith(", USA"):
            # We don't need to keep the country name.
            full_address = full_address[:-5]

        if full_address.lower().startswith("%s, %s" %
                                           (config.default_city.lower(),
                                            config.default_state.lower())):
            # If the geocoding fails to find a specific address,
            # it will return a generic city location.
            sess_data['next_step'] = 'num_and_name'
            return reply.build("I'm sorry, I heard the address \"%s\", "
                               "but I can't figure out where that is. "
                               "Try a different address, something I can "
                               "look up on the map." % addr,
                               reprompt="What's the street number and name?",
                               persist=sess_data,
                               is_end=False)

        sess_data['latitude'], sess_data['longitude'] = lat, lon
        sess_data['full_address'] = full_address
        sess_data['next_step'] = 'store_address'
        return reply.build("Thanks! Do you want to set "
                           "your %s address to %s?" %
                           (sess_data['which'],
                            location.text_to_speech(full_address)),
                           reprompt="Is that the correct address?",
                           persist=sess_data,
                           is_end=False)
    elif sess_data['next_step'] == 'store_address':
        # The user should have said "yes" or "no" after
        # being asked if we should store the address.
        # Only get here if they didn't.
        full_address = sess_data['full_address']
        return reply.build("Sorry, I didn't understand that. "
                           "Do you want to set "
                           "your %s address to %s?" %
                           (sess_data['which'],
                            location.text_to_speech(full_address)),
                           reprompt="Is that the correct address?",
                           persist=sess_data,
                           is_end=False)
    else:
        return reply.build("I'm sorry, I got confused. What do you mean?",
                           persist=sess_data,
                           is_end=False)


def store_address(intent, session):
    """Permanently store this user's address in the database.
    This is the endpoint of the AddAddressIntent dialog
    """
    sess_data = session.setdefault('attributes', {})
    if not sess_data.get('add_address') and \
          not sess_data['next_step'] == 'store_address':
        raise RuntimeError('Something went wrong.')

    data = {sess_data['which']: dict(latitude=str(sess_data['latitude']),
                                     longitude=str(sess_data['longitude']),
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

    # Standardize the input address requester
    which_raw = intent.get('slots', {}).get('which_address', {}).get('value')
    if not which_raw:
        # We might not have gotten anything in the slot.
        which = None
    else:
        which = difflib.get_close_matches(which_raw.lower(),
                                          ORIGIN_NAMES + DEST_NAMES, n=1)
        which = which[0] if which else None

    if which in ORIGIN_NAMES:
        which_lab = 'origin'
    elif which in DEST_NAMES:
        which_lab = 'destination'
    else:
        # If nothing was filled in the slot,
        # give the user both addresses.
        both = [_speak_address(wh, user_data)
                for wh in ['origin', 'destination']
                if wh in user_data]
        return reply.build(" ".join(both), is_end=True)
    return reply.build(_speak_address(which_lab, user_data), is_end=True)


def _speak_address(which, user_data):
    """Assume that `which` is either "origin" or "destination"."""
    addr = user_data.get(which)
    if not addr:
        return "I don't know your %s address." % which
    else:
        return ("Your %s address is set to %s." %
                (which, location.text_to_speech(addr['address'])))


def check_bikes(intent, session):
    """Handle a CheckBikeIntent; return number of bikes at a station

    Parameters
    ----------
    intent : dict
        JSON following the Alexa "IntentRequest"
        schema with name "CheckBikeIntent"
    session : dict
        JSON following the Alexa "Session" schema

    Returns
    -------
    dict
        JSON following the Alexa reply schema
    """
    stations = location.get_stations(config.bikes_api)
    try:
        sta = _station_from_intent(intent, stations)
    except location.AmbiguousStationError as err:
        return reply.build(err.message, is_end=True)
    except:  # NOQA
        log.exception('Failed to get a station.')
        return reply.build("I'm sorry, I didn't understand that. Try again?",
                           persist=session.get('attributes', {}),
                           is_end=False)

    if not sta['is_renting']:
        postamble = ", but the station isn't renting right now."
    else:
        postamble = "."

    n_bike = _get_bikes_available(sta)
    n_dock = _get_docks_available(sta)
    b_or_d = intent['slots']['bikes_or_docks']['value']
    n_things = n_bike if b_or_d == 'bikes' else n_dock

    verb = 'is' if n_things == 1 else 'are'
    b_or_d = b_or_d[:-1] if n_things == 1 else b_or_d  # singular?
    text = ("There %s %d %s available at the %s station%s"
            % (verb, n_things, b_or_d,
               location.text_to_speech(sta['name']),
               postamble))
    return reply.build(text, is_end=True)


def check_status(intent, session):
    """Handle a CheckStatusIntent:
    return number of bikes and docks at a station

    Parameters
    ----------
    intent : dict
        JSON following the Alexa "IntentRequest"
        schema with name "CheckBikeIntent"
    session : dict
        JSON following the Alexa "Session" schema

    Returns
    -------
    dict
        JSON following the Alexa reply schema
    """
    stations = location.get_stations(config.bikes_api)
    try:
        sta = _station_from_intent(intent, stations)
    except location.AmbiguousStationError as err:
        return reply.build(err.message, is_end=True)
    except:  # NOQA
        log.exception('Failed to get a station.')
        return reply.build("I'm sorry, I didn't understand that. Try again?",
                           persist=session.get('attributes', {}),
                           is_end=False)

    sta_name = location.text_to_speech(sta['name'])
    if not sta['is_installed']:
        return reply.build("The %s station isn't "
                           "installed at this time." % sta_name,
                           card_title='%s Status' % sta['name'],
                           card_text='%s\nNot installed' % _time_string(),
                           is_end=True)
    if not sta['is_renting']:
        return reply.build("The %s station isn't "
                           "renting right now." % sta_name,
                           card_title='%s Status' % sta['name'],
                           card_text='%s\nNot renting' % _time_string(),
                           is_end=True)
    if not sta['is_returning']:
        return reply.build("The %s station isn't "
                           "accepting returned bikes right now." % sta_name,
                           card_title='%s Status' % sta['name'],
                           card_text='%s\nNot returning' % _time_string(),
                           is_end=True)

    n_bike = _get_bikes_available(sta)
    n_dock = _get_docks_available(sta)
    text = ("There %s %d bike%s and %d dock%s "
            "at the %s station."
            % ("is" if n_bike == 1 else "are",
               n_bike, "" if n_bike == 1 else "s",
               n_dock, "" if n_dock == 1 else "s",
               sta_name))
    return reply.build(text,
                       card_title='%s Status' % sta['name'],
                       card_text=("At %s:\n%d bike%s and %d dock%s" %
                                  (_time_string(),
                                   n_bike, "" if n_bike == 1 else "s",
                                   n_dock, "" if n_dock == 1 else "s")),
                       is_end=True)


def list_stations(intent, session):
    """Find all stations on a given street

    Parameters
    ----------
    intent : dict
        JSON following the Alexa "IntentRequest"
        schema with name "ListStationIntent"
    session : dict
        JSON following the Alexa "Session" schema

    Returns
    -------
    dict
        JSON following the Alexa reply schema
    """
    stations = location.get_stations(config.bikes_api)
    street_name = intent['slots']['street_name']['value']
    possible = location.matching_station_list(stations,
                                              street_name,
                                              exact=True)
    street_name = street_name.capitalize()

    if len(possible) == 0:
        return reply.build("I didn't find any stations on %s." % street_name,
                           is_end=True)
    elif len(possible) == 1:
        sta_name = location.text_to_speech(possible[0]['name'])
        return reply.build("There's only one: the %s "
                           "station." % sta_name,
                           card_title=("%s Stations on %s" %
                                       (config.network_name, street_name)),
                           card_text=("One station on %s: %s" %
                                      (street_name, possible[0]['name'])),
                           is_end=True)
    else:
        last_name = location.text_to_speech(possible[-1]['name'])
        speech = "There are %d stations on %s: " % (len(possible),
                                                    street_name)
        speech += (', '.join([location.text_to_speech(p['name'])
                              for p in possible[:-1]]) +
                   ', and %s' % last_name)
        card_text = ("The following %d stations are on %s:\n%s" %
                     (len(possible), street_name,
                      '\n'.join(p['name'] for p in possible)))
        return reply.build(speech,
                           card_title=("%s Stations on %s" %
                                       (config.network_name, street_name)),
                           card_text=card_text,
                           is_end=True)
