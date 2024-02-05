"""
Module to import and display data from ics (Icalendar) files.
Used for friends in USMB-ACY-IUT-INFO-BUT.
Target destination : Discord Bot.
"""



import os
import json
import calendar
from edt_calendar import *
from edt_event import *
from datetime import datetime as dt
from datetime import timedelta as td



EDT = "edt.json"
DATA = []



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



def hours_of_day(time: any, start: int, end: int, offset: float) -> list:
    """Returns a list of all hours of the day between [start;end[ + offset (all args are hour)."""
    assert 0 <= start <= end <= 24
    t = return_dt(time)
    t = t.replace(hour = 0, minute = 0, second = 0, microsecond = 0)
    output = []
    for i in range(start, end + 1):
        hour = t + td(hours = i + offset)
        output.append(hour)
    return output



def days_of_week(time: any, start: int, end: int, offset: float) -> list:
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