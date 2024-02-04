"""
Module to import and display data from ics (Icalendar) files.
Used for friends in USMB-ACY-IUT-INFO-BUT.
Target destination : Discord Bot (made to accomodate other scripts).
"""



import os
import icalendar
import json
from datetime import datetime as dt
from datetime import timedelta as td
import calendar
import requests



EDT = "edt.json"
TEMP = "edt.ics"
DATA = {}
# {<name1>:(url,[{event1},{event2},{event3}])
#  <name2>:(url,[{event1},{event2},{event3}])}



def load(path: str) -> None:
    path += EDT
    if not os.path.exists(path): return
    global DATA
    with open(path, 'r', encoding = 'UTF-8') as file:
        DATA = json.load(file)



def save(path: str) -> None:
    if len(DATA) == 0: return
    path += EDT
    with open(path, 'w', encoding = 'UTF-8') as file:
        json.dump(DATA, file)



def get_time(event: any, attrib: str) -> dt:
    """Get a time attribute ('start' or 'end') of an event."""
    if  isinstance(event, dt): return event
    elif isinstance(event, icalendar.Event):
        return event['dt' + attrib].dt
    elif isinstance(event, dict):
        return str_to_dt(event[attrib])
    elif isinstance(event, str):
        return str_to_dt(event)
    else: raise TypeError("Invalid or Unsupported type")



def sort_by_time(events: list) -> list:
    """Sort list by start time."""
    return sorted(events, key = lambda e: get_time(e, "start"))



def get_from_file(file: str) -> list:
    """Retreive events in the specified file (path must be absolute)."""
    if not os.path.exists(file):
        raise FileNotFoundError(f"The specified file does not exist or was not found ({file}).")
    with open(file, 'r', encoding = 'UTF-8') as f:
        cal = icalendar.Calendar.from_ical(f.read())
    events = [e for e in cal.walk() if isinstance(e, icalendar.Event)]
    events = sort_by_time(events)
    return events



def get_from_url(url: str) -> list:
    """Download ics file from url and extract data from temp file."""
    response = requests.get(url)
    if os.path.exists(TEMP):
        os.remove(TEMP)
    with open(TEMP, 'xb') as file:
        file.write(response.content)
    return get_from_file(TEMP)



def extract_enseignant(description: str) -> list:
    """Get professors from the event description."""
    # Remove extra '\n' from description
    while "\n\n" in description:
        description = description.replace("\n\n", "\n")

    description = description.split("\n")
    if len(description) < 3: return []

    enseignants = []
    for i in description:
        if not i.isupper(): continue
        allow = "ABCDEFGHIJKLMNOPQRSTUVWXYZ É"
        if not all([c in allow for c in i]): continue
        cut = i.split(" ")
        if not all([len(seg) > 1 for seg in cut]): continue
        enseignants.append(i)
        
    return enseignants



def format_event(event: icalendar.Event) -> dict:
    """Format an Event object into a dictionary."""
    summary = event.get('summary', "")
    start = event.get('dtstart', "")
    end = event.get('dtend', "")
    location = event.get('location', "")
    description = event.get('description', "")

    output = {"summary": str(summary),
              "start": str(start.dt),
              "end": str(end.dt),
              "location": str(location),
              "description": str(description)}
    return output



def update_everything(name: str, source: str) -> str:
    """Update all events from the given iCal file to DATA[name]."""
    if source.endswith(".ics"):
        url = ""
        events = get_from_file(source)
    else:
        url = source
        events = get_from_url(source)
    formatted = [format_event(e) for e in events]
    DATA[name] = (url, formatted)
    return f"Updated {len(formatted)} events."



def update_self(name: str) -> str:
    """Update the calendar if it has a url to anchor to."""
    if DATA[name][0] != "":
        return update_everything(name, DATA[name][0])
    else:
        return "No URL provided; cannot update this calendar automatically."



def str_to_dt(text: str) -> dt:
    """Convert str(dt) to datetime object."""
    return dt.strptime(text, "%Y-%m-%d %H:%M:%S%z")



def is_within(time: any, range_start: any, range_end: any) -> bool:
    """Check if an event's start or end time is within a specified time frame."""
    range_start = get_time(range_start, "start")
    range_end = get_time(range_end, "end")
    assert range_start < range_end
    if isinstance(time, str):
        time = str_to_dt(time)
    return range_start <= time <= range_end



def get_all_within(all: list, range_start: any, range_end: any) -> list:
    """Returns all events in range (keeps order)."""
    events = []
    for event in all:
        if is_within(event["start"], range_start, range_end) \
            or is_within(event["end"], range_start, range_end):
            events.append(event)
    return events



def is_during(time: any, event: dict) -> bool:
    """Check if current time falls during event occurrence."""
    if isinstance(time, str):
        time = str_to_dt(time)
    return is_within(time, event["start"], event["end"])
    


def get_all_during(all: list, time: any) -> list:
    """Get all the events that are happening at the given time (keeps order)."""
    events = [e for e in all if is_during(time, e)]
    return events



def get_color(event: dict) -> str:
    """Get color of an event (based of the display on website)."""
    color = "white"
    
    subjects = {"green": ["dev", "prog", "C#", "code"],
                "yellow": ["sys", "os", "reseau"],
                "blue": ["bd", "sql", "donnees"],
                "purple": ["math", "outil", "phys", "graph"],
                "orange": ["web", "html", "css", "php"],
                "brown": ["econ", "gestion", "entrep"],
                "light_blue": ["comm", "droit"],
                "pink": ["angl", "engl", "lang", "ppp", "perso"],
                "red": ["eval", "note"]}
    
    professors = {"green": ['GRUSON NATHALIE', 'AYARI TAKOUA', 'BHANOT ARGHEESH', 'BARRY GUILLAUME', ],
                  "yellow": ['DIARD BENOIT', 'ARFAOUI KHADIJA', ],
                  "blue": ['COLIN PASCAL', 'MEGER NICOLAS', 'GILBERT NICOLAS', 'GAUDIN THIBAUT', 'RIPOCHE TEDDY', 'LAISSARD GÉRARD', ],
                  "purple": ['VOIRON NICOLAS', 'MARTIN UGO', 'MARTELET VALERIE', 'MORTREUX FABIENNE', 'KOSSAKOWSKI ROMAN', 'THERY HERVÉ', ],
                  "orange": ['DAMAS LUC', 'CHANET THOMAS', ],
                  "brown": ['GAILLARD YOHANN', 'COUTURIER VINCENT', 'LIDONE DA SILVA FERNANDA', ],
                  "light_blue": ['GRAZIANO EMMANUELLE', 'THABUIS PIERRE', ],
                  "pink": ['ZUSCHLAG CODY', 'VIBRAC STÉPHANIE', ]}

    prof = extract_enseignant(event["description"])
    desc = event["description"].lower().replace("é", "e")
    sum = event["summary"].lower().replace("é", "e")

    if not prof: return "grey"

    for k, v in subjects.items():
        for i in v:
            if i in desc or i in sum:
                color = k

    if color != "white": return color

    for k, v in professors.items():
        for p in prof:
            if p in v:
                return k
            
    return color



def hours_of_day(time: any, start: int, end: int, offset: float) -> list:
    """Returns a list of all hours of the day between [start;end[ + offset (all args are hour)."""
    assert 0 <= start <= end <= 24
    if isinstance(time, str):
        time = str_to_dt(time)
    time = time.replace(hour = 0, minute = 0, second = 0, microsecond = 0)
    output = []
    for i in range(start, end + 1):
        hour = time + td(hours = i + offset)
        output.append(hour)
    return output



def days_of_week(time: any, start: int, end: int, offset: float) -> list:
    """Returns a list of all days of the week between [start;end[ + offset (all args are day)."""
    assert 1 <= start <= end <= 7
    if isinstance(time, str):
        time = str_to_dt(time)
    time = time.replace(hour = 0, minute = 0, second = 0, microsecond = 0) - td(days = time.weekday())
    output = []
    for i in range(start - 1, end):
        day = time + td(days = i + offset)
        output.append(day)
    return output



def find_day(time: any, offset: int) -> dt:
    """Find the day relative to offset 0 (time.day)."""
    if isinstance(time, str):
        time = str_to_dt(time)
    time += td(days = offset)
    return dt(time.year, time.month, time.day)



def find_day_month(time: any, nb: int) -> dt:
    """
    Find the absolute day dt object from an input day nb, returns 00:00.
    <time> can be either dt (any in month) or str (of dt).
    """
    if isinstance(time, str):
        time = str_to_dt(time)
    if isinstance(time, dt):
        time = dt(time.year, time.month, 1)
    assert 1 <= nb <= calendar.monthrange(time.year, time.month)[1]
    return time.replace(day = nb)



def find_day_year(time: any, nb: int) -> dt:
    """
    Find the absolute day dt object from an input day nb relative to year, returns 00:00.
    <time> can be either dt (any in year), str (of dt), or int (year nb).
    """
    if isinstance(time, str):
        time = str_to_dt(time)
    if isinstance(time, dt):
        time = dt(time.year, 1, 1)
    elif isinstance(time, int):
        time = dt(time, 1, 1)
    assert 1 <= nb <= 365 + calendar.isleap(time.year)
    return  (time + td(days = nb - 1))



def find_week(time: any, offset: int) -> dt:
    """Find the week relative to offset 0 (time.week)."""
    if isinstance(time, str):
        time = str_to_dt(time)
    time += td(weeks = offset)
    return dt(time.year, time.month, time.day) - td(days = time.weekday())



def find_week_year(time: any, nb: int) -> dt:
    """
    Find the absolute week dt object from an input week nb, returns monday 00:00.
    <time> can be either dt (any in year), str (of dt), or int (year nb).
    """
    if isinstance(time, str):
        time = str_to_dt(time)
    if isinstance(time, dt):
        time = dt(time.year, 1, 4)
    elif isinstance(time, int):
        time = dt(time, 1, 4)
    assert 1 <= nb <= dt(time.year, 12, 28).isocalendar()[1]
    return time + td(weeks = nb - 1) - td(days = time.weekday())



def find_next(time: any, events: list) -> dict:
    """Returns next event (relative to <time>) in list."""
    if isinstance(time, str):
        time = str_to_dt(time)
    sort_by_time(events)
    for event in events:
        if str_to_dt(event["start"]) > time:
            return event



if __name__ == "__main__":

    path = os.path.dirname(os.path.realpath(__file__)) + "/"
    load(path)
    print("REMINDER : data entered through here will not be saved !")

    name = input("Name of the calendar: ")
    if name == "": exit()

    source = input("Source: ")
    if source.endswith(".ics"):
        try:
            print(update_everything(name, path + source))
        except FileNotFoundError:
            print("That file doesn't exist in the CWD.")
            exit()
    else:
        print(update_everything(name, source))