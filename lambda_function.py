from __future__ import print_function, division

import divvy
import handle
import reply

import requests
import yaml


# --------------------------- Lambda Function ----------------------------------
def lambda_handler(event, context):
    """ Route the incoming request based on type (LaunchRequest, IntentRequest,
    etc.) The JSON body of the request is provided in the event parameter.
    """
    print("event.session.application.applicationId=" +
          event['session']['application']['applicationId'])

    """
    Uncomment this if statement and populate with your skill's application ID to
    prevent someone else from configuring a skill that sends requests to this
    function.
    """
    conf = get_conf()
    if (event['session']['application']['applicationId'] != conf['app']['APP_ID']):
         raise ValueError("Invalid Application ID")

    stations = divvy.get_stations(conf['divvy_api'])
    #n_bike, n_dock = get_local_bikes(conf['app']['divvy_api'])

    if event['request']['type'] == "IntentRequest":
        return handle.intent(event['request'], event['session'], stations)
    
    return reply.build("<speak>There are %d bikes available at the Wells and Concord station.</speak>" % n_bike, is_end=True)
    
    if event['session']['new']:
        on_session_started({'requestId': event['request']['requestId']},
                           event['session'])

    if event['request']['type'] == "LaunchRequest":
        return on_launch(event['request'], event['session'])
    elif event['request']['type'] == "IntentRequest":
        return on_intent(event['request'], event['session'])
    elif event['request']['type'] == "SessionEndedRequest":
        return on_session_ended(event['request'], event['session'])


def get_conf():
    with open('config.yaml', 'r') as _fin:
        return yaml.load(_fin)


def get_local_bikes(address, divvy_api):

    adddress = format_address(address)
    sta = get_stations(divvy_api)
    my_sta = [val for val in sta if val['stAddress1'].lower() == address][0]

    return my_sta['availableBikes'], my_sta['availableDocks']

