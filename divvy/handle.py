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
    else:
        return reply.build("<speak>I didn't understand that.</speak>",
                           is_end=True)


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
    """
    slots = intent['slots']
    if slots.get('special_name', {}).get('value'):
        first = slots['special_name']['value']
        second = None
    else:
        first = slots['first_street']['value']
        second = slots.get('second_street', {}).get('value')
    sta = location.find_station(
          stations,
          first,
          second)
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
        return reply.build("<speak>%s</speak>" % err.message, is_end=True)
    except:  # NOQA
        return reply.build("<speak>I'm sorry, I didn't understand that.</speak>",
                           is_end=True)

    if not sta['is_renting']:
        postamble = ", but the station isn't renting right now."
    else:
        postamble = "."

    n_bike = sta['availableBikes']
    n_dock = sta['availableDocks']
    b_or_d = intent['slots']['bikes_or_docks']['value']
    n_things = n_bike if b_or_d == 'bikes' else n_dock

    return reply.build("<speak>There are %d %s available "
                       "at the %s station%s</speak>"
                       % (n_things, b_or_d,
                          location.text_to_speech(sta['stationName']),
                          postamble),
                       is_end=True)
