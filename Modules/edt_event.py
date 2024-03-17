"""
Import events from .ics file or a download url.
Includes edt_event.Event custom class.
Does not include displaying or saving.
"""


##########################################################################
# IMPORTS
##########################################################################



import os
import requests
import icalendar
from datetime import datetime as dt
from datetime import timedelta as td
from datetime import timezone as tz



##########################################################################
# GLOBAL AND FUNCTIONS
##########################################################################



def dt_now() -> dt:
    """Return current dt in a tz-aware format."""
    return dt.now(tz.utc)


def return_dt(time: any, attrib: str = "start") -> dt:
    """Convert any to dt attribute."""
    if  isinstance(time, dt): return time
    elif isinstance(time, icalendar.Event):
        return time['dt' + attrib].dt
    elif isinstance(time, str):
        return dt.strptime(time, "%Y-%m-%d %H:%M:%S%z")
    elif isinstance(time, icalendar.vDDDTypes):
        return time.dt
    elif isinstance(time, Event):
        return getattr(time, attrib)
    else: raise TypeError(f"Invalid or Unsupported type : '{type(time)}'")


def get_location(loc: str) -> list[str]:
    """Get lesson location."""
    location = loc.split(",")
    empty = icalendar.vText("")
    location = [i for i in location if i != empty]
    return location



##########################################################################
# EVENT CLASS
##########################################################################



class Event:
    def __init__(self, summary: str, start: any, end: any, location: str, description: str) -> None:
        self.summary = summary or ""
        if not start: raise ValueError('Cannot create Event with no start')
        if not end: raise ValueError('Cannot create Event with no end')
        self.start = return_dt(start, "start")
        self.end = return_dt(end, "end")
        self.location = get_location(location) or []
        self.description = description or ""


    def to_string(self, sep: str = "\n") -> str:
        """Return a string representation of the event."""
        return sep.join([self.summary,
            f"Start: {self.start}",
            f"End: {self.end}{sep}",
            f"Location: {self.location}"])


    def print_self(self, sep: str = "\n") -> None:
        """Print all attributes of the object in a formatted manner."""
        print(self.to_string(sep) + "\n")


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
    

    def get_duration(self) -> td:
        """Return the duration of the Event as a timedelta object."""
        return self.end - self.start
    

    def to_json(self) -> dict:
        """Convert the Event object into a JSON serializable dictionary."""
        return  {"summary": self.summary,
                 "description": self.description,
                 "start": str(self.start),
                 "end": str(self.end),
                 "location": self.location}


def convert_event(event: icalendar.Event) -> Event:
    """Create an Event object using an ICAL event."""
    attribs = ["summary", "dtstart", "dtend", "location", "description"]
    attribs = [event.get(i, None) for i in attribs]
    if not attribs["dtstart"] or not attribs["dtend"]:
        raise ValueError("Start and End time are non-optionnal")
    return Event(*attribs)



##########################################################################
# LIST[EVENT] FUNCTIONS
##########################################################################



def get_all_during(events: list[Event], time: any) -> list[Event]:
    """Returns all events that surround the time (keeps order)."""
    return [e for e in events if e.is_during(time)]


def get_all_intersect(events: list[Event], start: any, end: any) -> list[Event]:
    """Returns all events that share the time range (keeps order)."""
    return [e for e in events if e.is_intersect(start, end)]


def get_all_within(events: list[Event], start: any, end: any) -> list[Event]:
    """Returns all events contained within the time range (keeps order)."""
    return [e for e in events if e.is_within(start, end)]


def sort_by_time(events: list[Event]) -> list[Event]:
    """Sort list by start time."""
    return sorted(events, key = lambda e: e.start)


def find_next(events: list[Event], time: any) -> Event:
        """Returns next event (relative to <time>), or None"""
        t = return_dt(time)
        events_sorted = sort_by_time(events)
        for event in events_sorted:
            if event.start > t:
                return event
        return None


def get_from_ics(path: str) -> list[Event]:
    """Retreive events in the specified ics file (path must be absolute)."""
    with open(path, 'r', encoding = 'UTF-8') as file:
        cal = icalendar.Calendar.from_ical(file.read())
    events = []
    for e in cal.walk():
        if isinstance(e, icalendar.Event):
            try: events.append(convert_event(e))
            except ValueError: pass
    return sort_by_time(events)


def get_from_url(url: str) -> list[Event]:
    """Download ics file from url and extract data."""
    try: response = requests.get(url)
    except requests.exceptions.InvalidURL: raise requests.exceptions.InvalidURL()
    except requests.exceptions.RequestException: raise requests.exceptions.RequestException()
    cal = icalendar.Calendar.from_ical(response.content)
    events = []
    for e in cal.walk():
        if isinstance(e, icalendar.Event):
            try: events.append(convert_event(e))
            except ValueError: pass
    return sort_by_time(events)


def get_from_source(source: str) -> list[Event]:
    """Get load function corresponding to source type."""
    if isinstance(source, list) \
        and all([isinstance(e, Event) for e in source]): return sort_by_time(source)
    path = os.path.dirname(os.path.realpath(__file__)) + "/"
    if source.endswith(".ics"):
        return get_from_ics(path + source)
    elif source.startswith("http"):
        return get_from_url(source)
    else:
        raise NotImplementedError(f"Source '{source}' has unsupported format.")


def merge_events(*sources) -> list[Event]:
    """
    Merge multiple event lists into one depending on their order
    (First one is the most accurate, then descending order).
    """
    all_events = [get_from_source(src) for src in sources if src]
    starts_ends = [(events[0].start, events[-1].end) for events in all_events]
    new_bounds = []
    for start, end in starts_ends:
        if not new_bounds:
            new_bounds.append((start, end))
            continue
        if start <= new_bounds[-1][1]:
            start = new_bounds[-1][1]
        if start > end: new_bounds.append(None)
        new_bounds.append((start, end))
    merged = []
    for events, bounds in zip(all_events, new_bounds):
        if not bounds: continue
        merged += get_all_within(events, *bounds)
    return sort_by_time(merged)



##########################################################################
# TABLE INITIALISATION
##########################################################################



def hours_of_day(time: any, start: int = 0, end: int = 24, offset: float = 0.5) -> list[dt]:
    """Returns a list of all hours of the day between [start;end[ + offset (all args are hour)."""
    assert 0 <= start <= end <= 24
    t = return_dt(time)
    t = t.replace(hour = 0, minute = 0, second = 1, microsecond = 0)
    output = []
    for i in range(start - 1, end - 1):
        hour = t + td(hours = i + offset)
        output.append(hour)
    return output


def days_of_week(time: any, start: int = 1, end: int = 7, offset: float = 0) -> list[dt]:
    """Returns a list of all days of the week between [start;end] + offset (all args are day)."""
    assert 1 <= start <= end <= 7
    t = return_dt(time)
    t = t.replace(hour = 0, minute = 0, second = 1, microsecond = 0) - td(days = t.weekday())
    output = []
    for i in range(start - 1, end):
        day = t + td(days = i + offset)
        output.append(day)
    return output


def create_table(week: list[dt], start: int = 0, end: int = 24, offset: float = 0.5) -> list[list[dt]]:
    """Create the week timetable from weekdays dt and using hours_of_day function."""
    return [hours_of_day(d, start, end, offset) for d in week]



##########################################################################
# TIMETABLE CREATION
##########################################################################



def cross_time_day(table: list[dt], events: list[Event]) -> list[list[Event]]:
    """Generate timetable made from a list of times and a list of events."""
    table2d = []
    for t in table:
        table2d.append(get_all_during(events, t))
    return table2d


def cross_time_week(table: list[list[dt]], events: list[Event]) -> list[list[list[Event]]]:
    """Generate timetable made from a 2d list of times and a list of events."""
    table3d = []
    for t1 in table:
        table3d.append([get_all_during(events, t2) for t2 in t1])
    return table3d



##########################################################################
# MAIN
##########################################################################



def main(source: str = None) -> list[Event]:
    if not source: source = input("Filename or url : ")
    EVENTS = get_from_source(source)
    return sort_by_time(EVENTS)


if __name__ == "__main__":
    EVENTS = main()
    time = dt_now() + td(8)
    
    days = days_of_week(time, 1, 5)
    table = create_table(days, 7, 18)
    week = cross_time_week(table, EVENTS)
    [print("".join([e[0].to_string("   ") + "\n" if e else "//\n" for e in d]) + "") for d in week]

    hours = hours_of_day(time, 7, 17)
    day = cross_time_day(hours, EVENTS)
    [h[0].print_self() if h else print("//\n") for h in day]

