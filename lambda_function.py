from __future__ import print_function, division

from divvy import location
from divvy import handle
from divvy import reply

import yaml


# --------------------------- Lambda Function ----------------------------------
def lambda_handler(event, context):
    """ Route the incoming request based on type (LaunchRequest, IntentRequest,
    etc.) The JSON body of the request is provided in the event parameter.
    """
    print("event.session.application.applicationId=" +
          event['session']['application']['applicationId'])

    conf = get_conf()
    # This `if` prevents other Skills from using this Lambda
    if event['session']['application']['applicationId'] != conf['app']['APP_ID']:
        raise ValueError("Invalid Application ID")

    st_list = location.get_stations(conf['app']['divvy_api'])

    if event['request']['type'] == "IntentRequest":
        return handle.intent(event['request'], event['session'], st_list)
    else:
        # This could be a "LaunchRequest"
        return reply.build("<speak>Ask me a question about a Divvy station.</speak>")


def get_conf():
    with open('config.yaml', 'r') as _fin:
        return yaml.load(_fin)
