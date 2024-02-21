"""
Import events from .ics file or a download url.
Includes edt_event.Event custom class.
Includes finding dates relative to a dt position.
Does not include displaying.
"""



import os
import requests
import icalendar
import calendar
from datetime import datetime as dt
from datetime import timedelta as td
from datetime import timezone as tz



TEMPFILENAME = "edt_temp.ics"



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
# Event Class
##########################################################################



class Event:
    def __init__(self, summary: str, start: any, end: any, location: str, description: str) -> None:
        self.summary = summary
        self.start = return_dt(start, "start")
        self.end = return_dt(end, "end")
        self.location = get_location(location)
        self.description = description



    def to_string(self, sep: str = "\n") -> str:
        """Return a string representation of the event."""
        return f"{self.summary}{sep}" \
            f"Start: {self.start}{sep}" \
            f"End: {self.end}{sep}" \
            f"Location: {self.location}"



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



def convert_event(event: icalendar.Event) -> Event:
    """Create an Event object using an ICAL event."""
    attribs = ["summary", "dtstart", "dtend", "location", "description"]
    attribs = [event[i] for i in attribs]
    return Event(*attribs)



##########################################################################
# list[Event] Functions
##########################################################################



def get_all_during(events: list[Event], time: any) -> list[Event]:
    """Returns all events that surround the time(keeps order)."""
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
        events = [convert_event(e) for e in cal.walk()
                  if isinstance(e, icalendar.Event)]
        return events



def get_from_url(url: str) -> list[Event]:
    """Download ics file from url and extract data from temp file."""
    response = requests.get(url)
    if os.path.exists(TEMPFILENAME):
        os.remove(TEMPFILENAME)
    with open(TEMPFILENAME, 'xb') as file:
        file.write(response.content)
    events = get_from_ics(TEMPFILENAME)
    if os.path.exists(TEMPFILENAME):
        os.remove(TEMPFILENAME)
    return events



def get_from_source(source: str) -> list[Event]:
    """Get load function corresponding to source type."""
    path = os.path.dirname(os.path.realpath(__file__)) + "/"
    if source.endswith(".ics"):
        return get_from_ics(path + source)
    elif source.startswith("http"):
        return get_from_url(source)
    else:
        raise NotImplementedError(f"Source '{source}' has unsupported format.")



##########################################################################
# Relative DT Finder
##########################################################################



def find_day(time: any, offset: int) -> dt:
    """Find the day relative to offset 0 (time.day)."""
    time = return_dt(time)
    time += td(days = offset)
    return dt(time.year, time.month, time.day, second = 1, tzinfo = time.tzinfo)



def find_day_month(time: any, nb: int) -> dt:
    """
    Find the absolute day dt object from an input day nb, returns 00:00.
    <time> can be either dt (any in month) or str (of dt).
    """
    time = return_dt(time)
    t = dt(time.year, time.month, 1).replace(second = 1)
    assert 1 <= nb <= calendar.monthrange(t.year, t.month)[1]
    return t.replace(day = nb, tzinfo = time.tzinfo)



def find_day_year(time: any, nb: int) -> dt:
    """
    Find the absolute day dt object from an input day nb relative to year, returns 00:00.
    <time> can be either dt (any in year), str (of dt), or int (year nb).
    """
    if isinstance(time, int):
        time = dt(time, 1, 1)
    time = return_dt(time)
    t = dt(time.year, 1, 1).replace(second = 1, tzinfo = time.tzinfo)
    assert 1 <= nb <= 365 + calendar.isleap(t.year)
    return t + td(days = nb - 1)



def find_week(time: any, offset: int) -> dt:
    """Find the week relative to offset 0 (time.week)."""
    time = return_dt(time)
    time += td(weeks = offset)
    return dt(time.year, time.month, time.day, second = 1, tzinfo = time.tzinfo) - td(days = time.weekday())



def find_week_year(time: any, nb: int) -> dt:
    """
    Find the absolute week dt object from an input week nb, returns monday 00:00.
    <time> can be either dt (any in year), str (of dt), or int (year nb).
    """
    if isinstance(time, int):
        time = dt(time, 1, 4)
    time = return_dt(time)
    t = dt(time.year, 1, 4).replace(second = 1, tzinfo = time.tzinfo)
    assert 1 <= nb <= dt(t.year, 12, 28).isocalendar()[1]
    return t + td(weeks = nb - 1) - td(days = t.weekday())



def find_any(msg: str, time: any) -> (dt, bool):
    """
    Return a datetime [0] following user demand.
    'w' or 'd' for what to find.
    'm' or 'y' for absolute reference.
    otherwise will use relative reference.
    (can specify plus or minus with '+' or '-').
    All of the above can be in any order.
    Returned [1] bool is if data required is week.
    """
    t = return_dt(time)
    msg = msg.lower()
    n = "".join([c for c in msg if c.isdigit()])
    nb = int(n) if n else 0
    if "-" in msg: nb *= -1
    absn = abs(nb) if nb != 0 else 1
    d, w, m, y = "d" in msg, "w" in msg, "m" in msg, "y" in msg

    if m: return (find_day_month(t, absn), False)
    if y: return (find_day_year(t, absn), False) if d else (find_week_year(t, absn), True)
    return (find_week(t, nb), True) if w else (find_day(t, nb), False)



##########################################################################
# Table Initialisation
##########################################################################



def hours_of_day(time: any, start: int = 6, end: int = 18, offset: float = 0) -> list[dt]:
    """Returns a list of all hours of the day between ]start;end] + offset (all args are hour)."""
    assert 0 <= start <= end <= 24
    t = return_dt(time)
    t = t.replace(hour = 0, minute = 0, second = 1, microsecond = 0)
    output = []
    for i in range(start, end):
        hour = t + td(hours = i + offset)
        output.append(hour)
    return output



def days_of_week(time: any, start: int = 1, end: int = 5, offset: float = 0) -> list[dt]:
    """Returns a list of all days of the week between [start;end] + offset (all args are day)."""
    assert 1 <= start <= end <= 7
    t = return_dt(time)
    t = t.replace(hour = 0, minute = 0, second = 1, microsecond = 0) - td(days = t.weekday())
    output = []
    for i in range(start - 1, end):
        day = t + td(days = i + offset)
        output.append(day)
    return output



def create_table(week: list[dt], start: int = 6, end: int = 18, offset: float = 0) -> list[list[dt]]:
    """Create the week timetable from weekdays dt and using hours_of_day function."""
    return [hours_of_day(d, start, end, offset) for d in week]



##########################################################################
# Timetable Creation
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
# Main
##########################################################################



def main(source: str = None) -> list[Event]:
    if not source: source = input("Filename or url : ")
    EVENTS = get_from_source(source)
    return sort_by_time(EVENTS)



if __name__ == "__main__":
    EVENTS = main()
    cmd = input("cmd : ")
    now = dt_now()

    # Display next event
    if cmd == "nxt":
        event = find_next(EVENTS, now)
        if event: event.print_self()
    
    # Display timetable
    else:
        t = find_any(cmd, now)
        if t[1]:
            week = days_of_week(t[0])
            table = create_table(week, 6, 19, 0)
            events = cross_time_week(table, EVENTS)
            for d in events:
                [e[0].print_self("    ") if e else print("//\n") for e in d]
                print("\n")
        else:
            day = hours_of_day(t[0])
            events = cross_time_day(day, EVENTS)
            [e[0].print_self("\n") if e else print("//\n") for e in events]
    
