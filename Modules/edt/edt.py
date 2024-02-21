"""
Saving and displaying of edt_event.Event objects.
Includes USMB-Specific information (profs)
"""



from edt_event import *
from discord.embeds import Embed
import re


MAXLENTOTAL = 41
SUBJECTLEN = 4
MAXTEXTLEN = MAXLENTOTAL - SUBJECTLEN - 6
# 00 |R000| .......
# 00 |R000|R000|R000|

EVALKEYWORDS = ["eval", "note", "moodle", "oral", "test", "ds", "devoir", "surv", "contr"]
MAINSEPS = " |'-_\n/([{&#?!;:,."
TABLESEPS = (" |", "|", "| ")
SUBJECTSEPS = ("_", "\u0305_", "\u0305 ")

MISSINGSUBJECT = SUBJECTLEN * "?"
FILLSUBJECT = " " + (SUBJECTLEN-2) * "." + " "
EMPTYSUBJECT = SUBJECTLEN * " "



##########################################################################
# Data Calculation
##########################################################################



def get_profs(event: Event) -> list[str]:
    """Get professors from the event description."""        
    desc = event.description
    while "\n\n" in desc:
        desc = desc.replace("\n\n", "\n")
    desc = desc.split("\n")
    profs = []
    for i in desc:
        if "(prov)" not in i:
            if not i.isupper(): continue
            allow = "ABCDEFGHIJKLMNOPQRSTUVWXYZ -ÉÂÇÈÊÔÙÀÍÎÏÙÚÑÖÜ"
            if not all([c in allow for c in i]): continue
        profs.append(i)
    return profs
    


def get_subject(event: Event) -> str:
    """Get subject from event summary"""
    summary = event.summary.upper()
    res = re.compile("[R][0-9][-|_|.][0-9]{2}")
    sae = re.compile("[S](A[É|E])?[0-9][-|_|.][0-9]{2}")
    match = res.search(summary) or sae.search(summary)
    if match: 
        txt = match.group()
        return "".join([c for c in txt if c in "RS0123456789"])
    else: return MISSINGSUBJECT



def event_equals(e1: Event, e2: Event) -> bool:
    """
    Test if events are equivalent in nature.
    Inequality means events shouldn't be concatenated.
    """
    if not (e1 and e2): return e1 is None and e2 is None
    return e1.location == e2.location and \
           get_profs(e1) == get_profs(e2) and \
           get_subject(e1) == get_subject(e2)



def is_eval(event: Event) -> bool:
    """Check if an event is evaluated / graded."""
    txt = event.summary + event.description
    txt = txt.lower().replace("é", "e")
    return any([kwd in txt for kwd in EVALKEYWORDS])



def get_added_duration(events: list[Event], i: int) -> int:
    """Obtain concatenated event duration."""
    if i >= len(events): return 0
    if not events[i]: return 0
    if i > len(events) - 1: return 1
    if not event_equals(events[i], events[i+1]): return 1
    return 1 + get_added_duration(events, i+1)



def get_heights(events: list[Event]) -> list[int]:
    """
    Obtain table cell height on a timetable based on event duration.
    0 is void, a value is an occupied time.
    The first is positive, subsequents are negative.
    """
    heights = []
    for i in range(len(events)):
        if events[i]:
            d = get_added_duration(events, i)
            if i != 0 and heights[i-1] not in [0, -1]:
                heights.append(-d)
            else:
                heights.append(d)
        else:
            heights.append(0)
    return heights



##########################################################################
# Short Formatting
##########################################################################



def get_event_priority(event: Event) -> float:
    """
    Get the priority of an event.
    Higher number is better priority.
    """
    prio = 1
    if is_eval(event): prio *= 5
    prio /= event.get_duration().seconds/3600
    prio *= len(event.location) * 0.25 + 0.1
    prio *= len(get_profs(event)) * 0.25 + 0.1
    return prio



def prioritize(events: list) -> any:
    """
    Find the most important event among the list.
    Applied recursively to the list if required 
    (will reduce indentation, not return the priorit-est).
    """
    if not events: return None
    if all([isinstance(e, Event) for e in events]):
        events = sorted(events, key=get_event_priority)
        return events[0]
    elif all([isinstance(e, list) for e in events]):
        return [prioritize(e) for e in events]
    else: raise TypeError("Expected only Events in nested list.")



def get_char_len(msg: list[str]) -> int:
    """Return the string length of a list."""
    return sum([len(i) for i in msg]) if msg else 0



def strip_string(txt: str) -> str:
    """Shortens the string by stripping its end using special characters."""
    if not txt: return ""
    for i in range(len(txt)):
        if txt[-i-1] in MAINSEPS:
            if len(txt) > 2 and txt[-i-2] in MAINSEPS: # if last is still a sep
                return strip_string(txt[:-i-1]) # then recursion
            return txt[:-i-1]
    return txt[:-1]



def format_by_line(event: Event, lines: int) -> list[str]:
    """Format Event to be displayed on a number of lines."""
    assert lines > 0
    summ = event.summary
    locs = event.location
    profs = get_profs(event)
    space = " "
    
    while True:
        sep = f",{space}"
        l = f"[{space}{sep.join(locs)}{space}] " if locs else ""
        p = f"{sep.join(profs)} " if profs else ""
        lens = (len(summ), get_char_len(locs), get_char_len(p))
        maxlen = max(lens)
        
        match lines:
            case 1:
                txt = [f"{summ} {l}{p}"]
            case 2:
                if len(summ) > len(p):
                    txt = [summ, f"{l}{p}"]
                else:
                    txt = [f"{summ} {l}", p]
            case _:
                txt = [summ, f"{l}", p]
        
        txt = [t for t in txt if t] # Remove blank lines

        if all([len(string) <= MAXTEXTLEN for string in txt]):
            return txt
        elif space == " ": # try with smaller spacing first
            space = ""
            continue
        
        match lens.index(maxlen): # Sacrifice part of the longest of the 3
            case 0: summ = strip_string(summ)
            case 1: locs = locs[:-1] if len(locs) > 1 else [strip_string(locs[0])]
            case 2: profs = profs[:-1] if len(profs) > 1 else [strip_string(profs[0])]



##########################################################################
# General Formatting
##########################################################################



def format_times(times: list[dt], offset: int = 0) -> list[str]:
    """Format list of times by the hour, with added offset."""
    return [str(t.hour + offset).zfill(2) for t in times]



def format_subjects(events: list[Event], heights: list[int]) -> list[str]:
    """Get a list of the event subjects, formatted as needed."""
    subjects = [EMPTYSUBJECT] * len(heights)
    for i in range(len(events)):
        first, last = i <= 0, i >= len(events)-1
        if heights[i] < 0:
            if heights[i] < -1:
                subjects[i] = FILLSUBJECT
            else: subjects[i] = SUBJECTSEPS[0]
        elif heights[i] > 0:
            subjects[i] = get_subject(events[i])
        else:
            prev = heights[i-1] > 0 if not first else False
            next = heights[i+1] > 0 if not last else False
            if prev:
                if next: subjects[i] = SUBJECTSEPS[1]
                else: subjects[i] = SUBJECTSEPS[2]
            else:
                if next: subjects[i] = SUBJECTSEPS[0]
                else: subjects[i] = EMPTYSUBJECT
        if subjects[i] in SUBJECTSEPS: subjects[i] *= SUBJECTLEN
    return subjects



def format_details(events: list[Event], heights: list[int]) -> list[str]:
    """Format details using format_by_line and  a heights list."""
    details = []
    for i in range(len(events)):
        if events[i] and heights[i] > 0:
            lines = format_by_line(events[i], heights[i])
            details += lines
            details += [""] * (heights[i] - len(lines))
        if heights[i] == 0:
            details.append("")
    return details



##########################################################################
# Concatenation Formatting
##########################################################################



def format_lists(*args):
    """Format the lists in preparation for displaying."""
    output = []
    height = max([len(args[x]) if isinstance(args[x], list) else 0 for x in range(len(args))])
    for y in range(height):
        output.append([])
        for x in range(len(args)):
            if isinstance(args[x], list):
                output[y].append(args[x][y])
            else: output[y].append(args[x])
    return output



##########################################################################
# Main
##########################################################################



if __name__ == '__main__':
    EVENTS = main()
    t = find_any("yw12", dt_now())[0] + td(3)
    #t = dt_now()
    table = hours_of_day(t)
    times = format_times(table, 1)
    day = cross_time_day(table, EVENTS)
    prio = prioritize(day)
    heights = get_heights(prio)
    subjects = format_subjects(prio, heights)
    details = format_details(prio, heights)
    format = format_lists(times, TABLESEPS[0], subjects, TABLESEPS[2], details)
    print("\n".join(["".join(line) for line in format]))