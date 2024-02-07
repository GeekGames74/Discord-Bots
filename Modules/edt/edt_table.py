"""
Module to import and display data from ics (Icalendar) files.
Used for friends in USMB-ACY-IUT-INFO-BUT.
Target destination : Discord Bot.
"""



from edt_event import *
import calendar
from datetime import datetime as dt
from datetime import timedelta as td



def return_dt(time: any) -> dt:
    """Convert any to dt attribute."""
    if  isinstance(time, dt): return time
    elif isinstance(time, str):
        return dt.strptime(time, "%Y-%m-%d %H:%M:%S%z")
    else: raise TypeError(f"Invalid or Unsupported type : '{type(time)}'")



def hours_of_day(time: any, start: int, end: int, offset: float) -> list[dt]:
    """Returns a list of all hours of the day between [start;end[ + offset (all args are hour)."""
    assert 0 <= start <= end <= 24
    t = return_dt(time)
    t = t.replace(hour = 0, minute = 0, second = 0, microsecond = 0)
    output = []
    for i in range(start, end + 1):
        hour = t + td(hours = i + offset)
        output.append(hour)
    return output



def days_of_week(time: any, start: int, end: int, offset: float) -> list[dt]:
    """Returns a list of all days of the week between [start;end[ + offset (all args are day)."""
    assert 1 <= start <= end <= 7
    t = return_dt(time)
    t = t.replace(hour = 0, minute = 0, second = 0, microsecond = 0) - td(days = t.weekday())
    output = []
    for i in range(start - 1, end):
        day = t + td(days = i + offset)
        output.append(day)
    return output



def find_day(time: any, offset: int) -> dt:
    """Find the day relative to offset 0 (time.day)."""
    t = return_dt(time)
    t += td(days = offset)
    return dt(t.year, t.month, t.day)



def find_day_month(time: any, nb: int) -> dt:
    """
    Find the absolute day dt object from an input day nb, returns 00:00.
    <time> can be either dt (any in month) or str (of dt).
    """
    time = return_dt(time)
    t = dt(time.year, time.month, 1)
    assert 1 <= nb <= calendar.monthrange(t.year, t.month)[1]
    return t.replace(day = nb)



def find_day_year(time: any, nb: int) -> dt:
    """
    Find the absolute day dt object from an input day nb relative to year, returns 00:00.
    <time> can be either dt (any in year), str (of dt), or int (year nb).
    """
    if isinstance(time, int):
        time = dt(time, 1, 1)
    time = return_dt(time)
    t = dt(time.year, 1, 1)
    assert 1 <= nb <= 365 + calendar.isleap(t.year)
    return  (t + td(days = nb - 1))



def find_week(time: any, offset: int) -> dt:
    """Find the week relative to offset 0 (time.week)."""
    time = return_dt(time)
    time += td(weeks = offset)
    return dt(time.year, time.month, time.day) - td(days = time.weekday())



def find_week_year(time: any, nb: int) -> dt:
    """
    Find the absolute week dt object from an input week nb, returns monday 00:00.
    <time> can be either dt (any in year), str (of dt), or int (year nb).
    """
    if isinstance(time, int):
        time = dt(time, 1, 4)
    time = return_dt(time)
    t = dt(time.year, 1, 4)
    assert 1 <= nb <= dt(t.year, 12, 28).isocalendar()[1]
    return t + td(weeks = nb - 1) - td(days = t.weekday())



def create_table(week: list[dt], start: int, end: int, offset: float) -> list[list[dt]]:
    """Create the week timetable from weekdays dt and using hours_of_day function."""
    return [hours_of_day(d, start, end, offset) for d in week]



def cross_time_day(table: list[dt], events: list[Event]) -> list[list[Event]]:
    """Generate timetable made from a list of times and a list of events."""
    table2d = []
    for t in table:
        table2d.append(get_all_during(events, t))
    return table2d



def cross_time_week(table: list[list[dt]], events: list[Event]) -> list[list[list[Event]]]:
    """Generate timetable made from a list of times and a list of events."""
    table3d = []
    for t1 in table:
        table3d.append([get_all_during(events, t2) for t2 in t1])
    return table3d