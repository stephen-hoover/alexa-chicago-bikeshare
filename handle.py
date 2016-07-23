import divvy
import reply


def intent(req, session, stations):
    intent = req['intent']
    if intent['name'] == 'CheckBikeIntent':
        return handle_check_bikes(intent['slots'])
    else:
        return reply.build("<speak>I didn't understand that.</speak>", is_end=True)


def check_bikes(slots, stations):
    #loc = divvy.build_location(slots['first_street'], slots.get('second_street'))
    try:
        sta = divvy.find_station(stations, slots['first_street'], slots.get('second_street'))
    except divvy.AmbiguousStationError as err:
        return reply.build("<speak>%s</speak>" % err.msg, is_end=True)
        
    n_bike = sta['availableBikes']

    return reply.build("<speak>There are %d bikes available at the %s station.</speak>" % (n_bike, loc), is_end=True)
