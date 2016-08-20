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
import location
import reply


def intent(req, session, stations):
    """Identify and handle IntentRequest objects

    Parameters
    ----------
    req : dict
        JSON following the Alexa "IntentRequest" schema
    session : dict
        JSON following the Alexa "Session" schema
    stations : dict
        JSON following the Divvy "stationBeanList" schema

    Returns
    -------
    dict
        JSON following the Alexa reply schema
    """
    intent = req['intent']
    if intent['name'] == 'CheckBikeIntent':
        return check_bikes(intent, stations)
    elif intent['name'] == 'CheckStatusIntent':
        return check_status(intent, stations)
    elif intent['name'] == 'ListStationIntent':
        return list_stations(intent, stations)
    elif intent['name'] == 'AMAZON.HelpIntent':
        return reply.build("You can ask me how many bikes or docks are "
                           "at a specific station, or else just ask the status of a "
                           "station. Use the Divvy station name, such as "
                           "\"Milwaukee Avenue and Rockwell Street\". If you only "
                           "remember one cross-street, you can ask me to list all "
                           "stations on a particular street.")
    else:
        return reply.build("I didn't understand that.", is_end=True)


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
                           is_end=True)

    if not sta['is_renting']:
        postamble = ", but the station isn't renting right now."
    else:
        postamble = "."

    n_bike = sta['availableBikes']
    n_dock = sta['availableDocks']
    b_or_d = intent['slots']['bikes_or_docks']['value']
    n_things = n_bike if b_or_d == 'bikes' else n_dock

    return reply.build("There are %d %s available "
                       "at the %s station%s"
                       % (n_things, b_or_d,
                          location.text_to_speech(sta['stationName']),
                          postamble),
                       is_end=True)


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
                           is_end=True)

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
    return reply.build("There are %d bikes and %d docks "
                       "at the %s station."
                       % (n_bike, n_dock, sta_name),
                       is_end=True)


def list_stations(intent, stations):

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
