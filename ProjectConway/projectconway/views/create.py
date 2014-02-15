from datetime import datetime
from pyramid.httpexceptions import HTTPBadRequest
from pyramid.view import view_config
from sqlalchemy.exc import ArgumentError
from projectconway.models.run import Run
from game_of_life import TIME_LIMIT, TIME_DELAY
from game.game_controllers.game_controllers import GameOfLifeController


@view_config(route_name='create', renderer="pattern_input.mako")
def create_view(request):
    '''
    Executes the logic for the Pattern Input web page, allowing the user
    to input a pattern to the website - the application must then input
    that pattern to a session for persistance across pages.

    The method also checks for a pattern already existing in the session, so
    that the user can go back and edit it at any point.
    
    '''
    data = {}
    data["page"] = "patternpage"
    page_keys = [
        "pattern_input",
        "scheduler",
        "confirmation"
    ]
    pages = {
        page_keys[0]: "pattern_input.mako",
        page_keys[1]: "scheduler.mako",
        page_keys[2]: "confirmation.mako"
    }

    page = ""
    if "create_page" in request.POST:
        req_page = request.POST["create_page"]
        if req_page in pages:
            page = req_page
    elif "create_page" in request.session:
        page = request.session["create_page"]
    if not page:
        page = page_keys[0]
    request.override_renderer = pages[page]

    # scheduler page
    if page == page_keys[1]:
        request.session["create_page"] = page_keys[1]
        data["title"] = "Scheduler"

        if "viewing_date" in request.session:
            viewing_date = request.session["viewing_date"]
        else:
            viewing_date = datetime.today().strftime("%d/%m/%Y")
        data["viewing_date"] = viewing_date

        if "viewing_hour" in request.session:
            viewing_hour = request.session["viewing_hour"]
        else:
            viewing_hour = datetime.now().hour
        data["viewing_hour"] = viewing_hour

        if "viewing_slot" in request.session:
            viewing_slot = request.session["viewing_slow"]
        else:
            viewing_slot = 0
        data["viewing_slot"] = viewing_slot

    # confirmation page
    elif page == page_keys[2]:
        request.session["create_page"] = page_keys[2]

    # pattern input page
    else:
        request.session["create_page"] = page_keys[0]
        data["title"] = "Create Pattern"

    # Work out if a pattern is already in the session
    if 'pattern' in request.session:
        data['pattern'] = request.session['pattern'].replace('\n', "\\n")

    return data


@view_config(route_name="pattern_input_receiver", renderer='json')
def pattern_input_receiver_JSON(request):
    '''
    This view receives a customers pattern input in the form of a JSON 
    string. We then run a gameoflife for that pattern and return the number 
    of seconds and turns it will run for, taking into consideration the 5 minute
    run time and delays. 
    '''
    # Retrieve pattern from request
    pattern = request.json_body
    request.session["pattern"] = pattern

    golcontroller = GameOfLifeController()
    golcontroller.set_up_game(pattern)

    while(golcontroller.get_turn_count() < (TIME_LIMIT / TIME_DELAY) and not
          golcontroller.get_game().is_game_forsaken()):
        golcontroller.play_next_turn()


    return {"turns": golcontroller.get_turn_count(),
            "runtime": golcontroller.get_turn_count() * TIME_DELAY}

@view_config(route_name="pattern_input_clearer", renderer='json')
def pattern_input_clearer_JSON(request):
    '''
    This view receives a user's pattern input in the form of a JSON string and
    removes it from the session.
    '''
    if 'pattern' in request.session:
        del request.session["pattern"]
    return request.session

@view_config(route_name="time_slot_receiver", renderer='json')
def time_slot_reciever_JSON(request):
    """
    This view receives the user's time slot choice, checks that it is viable,
    and adds it to the user's session if so.
    """
    time_format = '%Y-%m-%dT%H:%M:%S.000Z'
    try:
        time_slot = datetime.strptime(request.json_body, time_format)
    except:
        raise HTTPBadRequest("Timestring was not formatted correctly!")

    try:
        aval_slots = Run.get_time_slots_for_hour(time_slot)
    except ArgumentError:
        raise HTTPBadRequest("Time given is in the past")

    return {"time_slots": aval_slots}