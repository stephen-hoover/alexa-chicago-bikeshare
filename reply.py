"""
https://developer.amazon.com/public/solutions/alexa/alexa-skills-kit/docs/alexa-skills-kit-interface-reference
The Echo expects a response in the following format:

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

def build(speech, reprompt=None, is_end=False, persist=None):
    output = {
        "version": "1.0",
        "response": {
            "outputSpeech": {
                "type": "SSML",
                "ssml": speech
            },
            "shouldEndSession": is_end
        }
    }
    if persist:
        output["sessionAttributes"] = persist
    if reprompt:
        output["response"]["reprompt"] = {
            "outputSpeech": {
                "type": "SSML",
                "ssml": reprompt
                }
            }
               
    return output
