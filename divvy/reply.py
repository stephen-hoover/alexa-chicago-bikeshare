"""Construct the Alexa reply schema

https://developer.amazon.com/public/solutions/alexa/alexa-skills-kit/docs/alexa-skills-kit-interface-reference
Alexa expects a response in the following format:

{
  "version": "string",
  "sessionAttributes": {
    "string": object
  },
  "response": {
    "outputSpeech": {
      "type": "string",
      "text": "string",
      "ssml": "string"
    },
    "card": {
      "type": "string",
      "title": "string",
      "content": "string",
      "text": "string",
      "image": {
        "smallImageUrl": "string",
        "largeImageUrl": "string"
      }
    },
    "reprompt": {
      "outputSpeech": {
        "type": "string",
        "text": "string",
        "ssml": "string"
      }
    },
    "shouldEndSession": boolean
  }
}

"""


def build(speech, reprompt=None,
          card_text=None, card_title=None,
          is_end=False, persist=None):
    """Construct an Alexa reply schema v1.0

    Format all output speech as SSML.

    Parameters
    ----------
    speech: str
        The response which Alexa should speak. This will
        be wrapped in "<speak>" tags and labeled as SSML
        in the reply schema.
    reprompt: str, optional
        If provided, Alexa will speak this text if the user
        waits too long before replying. This will
        be wrapped in "<speak>" tags and labeled as SSML
        in the reply schema.
    card_text: str, optional
        If provided, the response will generate a "simple"
        card in the Alexa app with this text.
    card_title: str, optional
        If provided, and if the `card_text` is also provided,
        the card in the Alexa app will have this title.
        The default is no title on the card.
        Note that the card will always have the skill name.
    is_end: bool, optional
        If False (the default), the skill will remain open
        for new inputs after this reply. If True, the
        skill will close immediately after replying.
    persist: dict, optional
        If provided, this dictionary will be returned
        to the skill as session attributes on the next call
        within the same session.

    Returns
    -------
    dict
        JSON following the Alexa reply schema
    """
    output = {
        "version": "1.0",
        "response": {
            "outputSpeech": {
                "type": "SSML",
                "ssml": "<speak>%s</speak>" % speech
            },
            "shouldEndSession": is_end
        }
    }
    if persist:
        output["sessionAttributes"] = persist
    if card_text:
        # Provide a card in the Alexa app
        output["response"]["card"] = {"type": "Simple",
                                      "title": card_title,
                                      "content": card_text}
    if reprompt:
        output["response"]["reprompt"] = {
            "outputSpeech": {
                "type": "SSML",
                "ssml": "<speak>%s</speak>" % reprompt
                }
            }

    return output
