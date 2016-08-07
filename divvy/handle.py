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
import stations
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
    slots = intent['slots']
    try:
        sta = stations.find_station(stations,
                                    slots['first_street'],
                                    slots.get('second_street'))
    except stations.AmbiguousStationError as err:
        return reply.build("<speak>%s</speak>" % err.msg, is_end=True)

    n_bike = sta['availableBikes']

    return reply.build("<speak>There are %d bikes available "
                       "at the %s station.</speak>"
                       % (n_bike, sta['stationName']),
                       is_end=True)
