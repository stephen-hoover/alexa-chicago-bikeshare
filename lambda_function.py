from __future__ import print_function, division
import logging
import sys

from divvy import config
from divvy import handle
from divvy import reply

log = logging.getLogger(__name__)

# --------------------------- Lambda Function ----------------------------------
def lambda_handler(event, context):
    """ Route the incoming request based on type (LaunchRequest, IntentRequest,
    etc.) The JSON body of the request is provided in the event parameter.
    """
    logging.basicConfig(level='INFO', stream=sys.stderr)

    # This `if` prevents other Skills from using this Lambda
    if event['session']['application']['applicationId'] != config.APP_ID:
        raise ValueError("Invalid Application ID")

    try:
        if event['request']['type'] == "IntentRequest":
            return handle.intent(event['request'], event['session'])
        elif event['request']['type'] == "LaunchRequest":
            return reply.build("Ask me a question about a Divvy station.",
                               is_end=False)
        elif event['request']['type'] == "SessionEndedRequest":
            return reply.build("Bike safe!", is_end=True)
        else:
            # I don't think there's any other kinds of requests.
            return reply.build("Ask me a question about a Divvy station.",
                               is_end=False)
    except Exception as err:  # NOQA
        log.exception('Unhandled exception for event\n%s\n' % str(event))
        return reply.build("Sorry, something went wrong. Please try again.")
