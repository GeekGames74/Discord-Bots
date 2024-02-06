"""
Module to import events from an ics file or an url
"""



import os
import requests
import icalendar
import json
from datetime import datetime as dt



TEMP = "edt.ics"



def return_dt(time: any, attrib: str = "start") -> dt:
    """Convert any to dt attribute."""
    if  isinstance(time, dt): return time
    elif isinstance(time, icalendar.Event):
        return time['dt' + attrib].dt
    elif isinstance(time, str):
        return dt.strptime(time, "%Y-%m-%d %H:%M:%S%z")
    elif isinstance(time, icalendar.vDDDTypes):
        return time.dt
    else: raise TypeError(f"Invalid or Unsupported type : '{type(time)}'")



def get_location(loc: str) -> list[str]:
    """Get lesson location."""
    location = loc.split(",")
    empty = icalendar.vText("")
    location = [i for i in location if i != empty]
    return location



class Event:
    def __init__(self, summary: str, start: any, end: any, location: str, description: str) -> None:
        self.summary = summary
        self.start = return_dt(start, "start")
        self.end = return_dt(end, "end")
        self.location = get_location(location)
        self.description = description
        self.professor = self.get_prof()
        self.subject = self.get_subject()



    def to_string(self) -> str:
        """Return a string representation of the event."""
        return f"{self.summary}\n" \
            f"Start: {self.start}\n" \
            f"End: {self.end}\n" \
            f"Location: {self.location}\n" \
            f"Professor: {self.professor}\n" \
            f"Subject: {self.subject}\n"



    def print_self(self) -> None:
        """Print all attributes of the object in a formatted manner."""
        print(self.to_string())



    def get_prof(self) -> list[str]:
        """Get professors from the event description."""        
        desc = self.description
        while "\n\n" in desc:
            desc = desc.replace("\n\n", "\n")
        desc = desc.split("\n")
        profs = []
        for i in desc:
            if not i.isupper(): continue
            allow = "ABCDEFGHIJKLMNOPQRSTUVWXYZ -ÉÂÇÈÊÔÙÀÍÎÏÙÚÑÖÜ"
            if not all([c in allow for c in i]): continue
            profs.append(i)
        return profs



    def is_during(self, time: any) -> bool:
        """Check if an event's start and end time surronds a time."""
        t = return_dt(time)
        return self.start <= t <= self.end
    


    def is_intersect(self, time1: any, time2: any) -> bool:
        """Check if event's duration is shared with a time range."""
        t1 = return_dt(time1)
        t2 = return_dt(time2)
        assert t1 < t2
        return not (t2 < self.start and self.end < t1)
    


    def is_within(self, time1: any, time2: any) -> bool:
        """Check if event's duration is contained within a time range."""
        t1 = return_dt(time1)
        t2 = return_dt(time2)
        assert t1 < t2
        return t1 <= self.start and self.end <= t2
        


    def get_subject(self) -> str:
        """Get school subject of the event."""
        return ""



def create_event(event: icalendar.Event) -> Event:
    """Create an Event object using an ICAL event."""
    attribs = ["summary", "dtstart", "dtend", "location", "description"]
    attribs = [event[i] for i in attribs]
    return Event(*attribs)



def sort_by_time(events: list[Event]) -> list[Event]:
    """Sort list by start time."""
    return sorted(events, key = lambda e: e.start)



def find_next(events: list[Event], time: any) -> Event:
        """Returns next event (relative to <time>)."""
        t = return_dt(time)
        es = sort_by_time(events)
        for e in es:
            if e > t:
                return e



def get_from_ics(path: str) -> list[Event]:
        """Retreive events in the specified ics file (path must be absolute)."""
        with open(path, 'r', encoding = 'UTF-8') as file:
            cal = icalendar.Calendar.from_ical(file.read())
        events = [create_event(e) for e in cal.walk()
                  if isinstance(e, icalendar.Event)]
        return events



def get_from_json(path: str) -> list[Event]:
    """Get a list of Events from a JSON file."""
    with open(path, 'r', encoding = 'UTF-8') as file:
        return json.load(file)



def get_from_url(url: str) -> list[Event]:
    """Download ics file from url and extract data from temp file."""
    response = requests.get(url)
    if os.path.exists(TEMP):
        os.remove(TEMP)
    with open(TEMP, 'xb') as file:
        file.write(response.content)
    return get_from_ics(TEMP)



def get_from_source(source: str) -> list[Event]:
    """Get load function corresponding to source type."""
    path = os.path.dirname(os.path.realpath(__file__)) + "/"
    if source.endswith(".ics"):
        return get_from_ics(path + source)
    elif source.endswith(".json"):
        return get_from_json(path + source)
    elif source.startswith("http"):
        return get_from_url(source)
    else:
        raise NotImplementedError(f"Source '{source}' has unsupported format.")



def input_events() -> list[Event]:
    """Ask user to enter a URL or local path of .ics file."""
    source = input("Source of the data : ")
    return get_from_source(source)



if __name__ == "__main__":
    DATA = input_events()
    DATA = sort_by_time(DATA)
    start = input("start : ")
    end = input("end : ")
    i1 = int(start) if start.isdigit() else 0
    i2 = int(end) if end.isdigit() else len(DATA)-1
    [e.print_self() for e in DATA[i1:i2+1]]