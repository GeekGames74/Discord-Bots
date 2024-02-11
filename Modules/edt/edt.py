"""
Saving and displaying of edt_event.Event objects.
Includes USMB-Specific information (profs)
"""



from edt_event import *
from discord.embeds import Embed
import re


MAXLENTOTAL = 41
# 00| R000 |.......
# ---------- = 10
MAXTEXTLEN = MAXLENTOTAL - 10
EVALKEYWORDS = ["eval", "note", "moodle", "oral", "test", "ds", "devoir", "surv", "contr"]
MAINSEPS = " |'-_\n/([{&#?!;:,."



def get_profs(event: Event) -> list[str]:
    """Get professors from the event description."""        
    desc = event.description
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
    


def get_subject(event: Event) -> str:
    """Get subject from event summary"""
    summary = event.summary
    res = re.compile("[R|r][0-9][-|_|.][0-9]{2}")
    sae = re.compile("[S|s]([A|a][É|E|é|e])?[0-9][-|_|.][0-9]{2}")
    match = res.search(summary) or sae.search(summary)
    if match: 
        txt = match.group()
        return "".join([c for c in txt if c not in "AaÉEée"])
    else: return ""



def is_eval(event: Event) -> bool:
    """Check if an event is evaluated / graded."""
    txt = event.summary + event.description
    txt = txt.lower().replace("é", "e")
    return any([kwd in txt for kwd in EVALKEYWORDS])



def find_priority_event(events: list[Event]) -> Event:
    """
    Find the most important event among the list.
    Importance is defined like :
    [short graded > long graded > short > long]
    """
    if not events: return None
    if len(events) == 1: return events[0]
    events = sort_by_time(events)
    events = sorted(events, key = lambda e: e.get_duration())
    for event in events:
        if is_eval(event): return event
    return events[0]



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