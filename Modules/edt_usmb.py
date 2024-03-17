"""
Saving and displaying of edt_event.Event objects.
Includes USMB-Specific information, in the UsmbEvent class
"""


##########################################################################
# IMPORTS
##########################################################################



from edt_event import *
import re



##########################################################################
# GLOBALS
##########################################################################



MAXLENTOTAL = 41
SUBJECTLEN = 4
MAXTEXTLEN = MAXLENTOTAL - SUBJECTLEN - 6
# |1       |10       |20       |30       |40
# 00 |R000| ...............................
# 00 |R000|R000|R000|R000|R000|R000|R000| _
WEEKDAYS_LANG = {
    "fr": ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"] ,
    "en": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"] }

EVALKEYWORDS = ["eval", "note", "moodle", "oral", "test", "ds", "devoir", "surv", "contr"]
MAINSEPS = " |'-_\n/([{&#?!;:,."
TABLESEPS = (" |", "|", "| ", " _")
SUBJECTSEPS = ("_", "\u0305_", "\u0305 ")

MISSINGSUBJECT = SUBJECTLEN * "?"
FILLSUBJECT = " " + (SUBJECTLEN-2) * "." + " "
EMPTYSUBJECT = SUBJECTLEN * " "


class NoEventException(Exception): pass



##########################################################################
# DATA CALCULATION
##########################################################################



def get_profs(desc: str) -> list[str]:
    """Get professors from the event description."""
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
    

def get_subject(summary: str) -> str:
    """Get subject from summary"""
    summary = summary.upper()
    res = re.compile("[R][0-9][-|_|.][0-9]{2}")
    sae = re.compile("[S](A[É|E])?[0-9][-|_|.][0-9]{2}")
    match = res.search(summary) or sae.search(summary)
    if match: 
        txt = match.group()
        return "".join([c for c in txt if c in "RS0123456789"])
    else: return MISSINGSUBJECT


def has_event(events: list) -> bool:
    """Check if there is at least one event within the day."""
    for i in range(len(events)):
        if isinstance(events[i], str):
            if events[i] and not events[i].isspace():
                return True
        if isinstance(events[i], Event):
            if events[i]: return True
    return False


def is_eval(event: Event) -> bool:
    """Check if an event is evaluated / graded."""
    txt = event.summary + event.description
    txt = txt.lower().replace("é", "e")
    return any([kwd in txt for kwd in EVALKEYWORDS])



##########################################################################
# USMBEVENT CLASS
##########################################################################



class UsmbEvent(Event):
    def __init__(self, event: Event) -> None:
        self.__dict__.update(event.__dict__)
        self.get_profs()
        self.get_subject()
        self.get_priority()
    

    def get_profs(self) -> None:
        """Generate list of professors from description."""
        self.profs = get_profs(self.description) or []
    

    def get_subject(self) -> None:
        """Get subject name from summary."""
        self.subject = get_subject(self.summary) or ""


    def get_priority(self) -> None:
        """Get the priority of an event.
        Higher number is better priority."""
        self.prio = 5 if is_eval(self) else 1
        self.prio /= self.get_duration().seconds/3600
        self.prio *= len(self.location) * 0.25 + 0.1
        self.prio *= len(self.profs) * 0.25 + 0.1


    def similar(self, other: "UsmbEvent") -> bool:
        """Check if two events should be fused."""
        return self.location == other.location and \
           self.profs == other.profs and \
           self.subject == other.subject
    

    def to_json(self) -> dict:
        """Convert the UsmbEvent object into a JSON serializable dictionary."""
        return  {"summary": self.summary,
                 "description": self.description,
                 "start": str(self.start),
                 "end": str(self.end),
                 "location": self.location}


def convert_to_usmb(event: any) -> UsmbEvent:
    """Converts an Event object to a UsmbEvent object."""
    if isinstance(event, UsmbEvent): return event
    if isinstance(event, Event): return UsmbEvent(event)
    if isinstance(event, list): return [convert_to_usmb(e) for e in event]
    raise TypeError("Input must be type Event or list.")


def similar(a: UsmbEvent, b: UsmbEvent) -> bool:
    if isinstance(a, UsmbEvent)  and isinstance(b, UsmbEvent):
        return a.similar(b)
    return a is None and b is None


def get_added_duration(events: list[UsmbEvent], i: int) -> int:
    """Obtain concatenated event duration."""
    if i >= len(events): return 0
    if not events[i]: return 0
    if i > len(events) - 1: return 1
    if not similar(events[i], events[i+1]): return 1
    return 1 + get_added_duration(events, i+1)


def get_heights(events: list[UsmbEvent]) -> list[int]:
    """
    Obtain table cell height on a timetable based on event duration.
    0 is void, a value is an occupied time.
    The first is positive, subsequents are negative.
    """
    heights = []
    for i in range(len(events)):
        if events[i]:
            d = get_added_duration(events, i)
            if i != 0 and heights[i-1] > 1:
                heights.append(-d)
            else: heights.append(d)
        else: heights.append(0)
    return heights


def prioritize(events: list) -> any:
    """
    Find the most important event among the list.
    Applied recursively to the list if required 
    (will reduce indentation, not return the priorit-est).
    """
    if not events: return None
    if all([isinstance(e, UsmbEvent) for e in events]):
        events = sorted(events, key = lambda x: x.prio)
        return events[-1]
    elif all([isinstance(e, list) for e in events]):
        return [prioritize(e) for e in events]
    else: raise TypeError("Expected only UsmbEvents in nested list.")



##########################################################################
# SHORT FORMATTING
##########################################################################



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


def format_by_line(event: UsmbEvent, lines: int) -> list[str]:
    """Format Event to be displayed on a number of lines."""
    assert lines > 0
    summ = event.summary
    locs = event.location
    profs = event.profs
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


def format_offset(offset: int) -> str:
    """Return a formatted time offset."""
    time = str(abs(offset)).zfill(2)
    return "-" + time if offset < 0 else "+" + time



##########################################################################
# GENERAL FORMATTING
##########################################################################



def format_times(times: list[dt], offset: int = 0) -> list[str]:
    """Format list of times by the hour, with added offset."""
    return [str((t + td(hours = offset)).hour).zfill(2) for t in times]


def format_subjects(events: list[UsmbEvent], heights: list[int]) -> list[str]:
    """Get a list of the event subjects, formatted as needed."""
    subjects = [EMPTYSUBJECT] * len(heights)
    for i in range(len(events)):
        first, last = i <= 0, i >= len(events)-1
        if heights[i] < 0:
            if heights[i] < -1:
                subjects[i] = FILLSUBJECT
            else: subjects[i] = SUBJECTSEPS[0]
        elif heights[i] > 0:
            subjects[i] = events[i].subject
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


def format_details(events: list[UsmbEvent], heights: list[int]) -> list[str]:
    """Format details using format_by_line and a heights list."""
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
# CONCATENATION FORMATTING
##########################################################################



def format_day(events: list[UsmbEvent], sep: str = None) -> list[list]:
    """Generate timetable for the day (with generic parameters)."""
    heights = get_heights(events)
    subjects = format_subjects(events, heights)
    details = format_details(events, heights)
    return [subjects, sep, details] if sep else [subjects + details]


def format_week(events: list[list[UsmbEvent]]) -> list[list[str]]:
    """Generate timetable for the week (with generic parameters)."""
    heights = [get_heights(day) for day in events]
    subjects = [format_subjects(day, h) for day, h in zip(events, heights)]
    return subjects


def interject(anyList: list, sep: any) -> list:
    """Insert `sep` between each element of `l`, returning the modified list."""
    l = anyList.copy()
    for  i in range(len(l)-1):
        l.insert(i*2+1, sep)
    return l
    

def format_lists(*args: any) -> list[list]:
    """Format the lists in preparation for displaying."""
    output = []
    height = max([len(a) if isinstance(a, list) else 0 for a in args])
    for y in range(height):
        output.append([])
        for x in range(len(args)):
            if isinstance(args[x], list):
                output[y].append(args[x][y])
            else: output[y].append(args[x])
    return output


def truncate_one(subjects: list[str]) -> (int, int):
    """Return index at which a corresponding timetable should be truncated (by slicing)."""
    early, late = 0, len(subjects)
    if not has_event(subjects): return (late, early)
    for i in range(len(subjects)):
        if subjects[i] and not subjects[i].isspace():
            early = i
            break
    for i in range(len(subjects)-1, -1, -1):
        if subjects[i] and not subjects[i].isspace():
            late = i+1
            break
    return (early, late)


def truncate_all(*args: list[str]) -> (int, int):
    """Return min and max truncating to include all information in the timetable."""
    mins = [truncate_one(arg)[0] for arg in args if has_event(arg)]
    maxs = [truncate_one(arg)[1] for arg in args if has_event(arg)]
    return (min(mins), max(maxs))


def change_truncation(trunc: (int, int), length: int, max_trunc: int = 0) -> (int, int):
    """Change truncation based on maximum allowed."""
    low, high = trunc[0], trunc[1]
    while high-low <= max_trunc:
        if low > 0: low -= 1
        if high < length: high += 1
    return (low, high)


def empty_indexes(subjects: list[list[str]]) -> list[int]:
    """Find all empty subjects and keep their indexes."""
    return [i for i in range(len(subjects)) if not has_event(subjects[i])]


def limit_empty(indexes: list[int], length: int) -> list[int]:
    """Ensure week truncation does not create holes."""
    def can_be_empty(indexes: list[int], index: int, length: int) -> bool:
        if index not in indexes: return False
        if index == 0 or index == length-1: return True
        return can_be_empty(indexes, index-1, length) \
            or can_be_empty(indexes, index+1, length)
    return [i for i in indexes if can_be_empty(indexes, i, length)]


def create_header(offset: int = 0, txt: str = "") -> list[str]:
    """
    Create header row of a table.
    If txt is a lang code, will display weekdays.
    """
    time = format_offset(offset) if offset else "   "
    days = WEEKDAYS_LANG[txt] if txt in WEEKDAYS_LANG else [txt]
    return [time] + days


def timetable_tostring(table: list[list], ySep: str = "\n", xSep: str = "") -> str:
    """Convert timetable into string representation."""
    return ySep.join([xSep.join(row) for row in table])



##########################################################################
# MAIN
##########################################################################



def main_day(events: list[UsmbEvent], time: any = dt_now(),
         offset: int = 0, max_trunc: int = 5) -> list[list[str]]:
    if not events: events = main()
    t = return_dt(time)
    hours = hours_of_day(t)
    table = cross_time_day(hours, events)
    usmb = convert_to_usmb(table)
    prio = prioritize(usmb)
    day = format_day(prio, TABLESEPS[2])
    if not has_event(prio): raise NoEventException
    times = format_times(hours, offset)
    format = format_lists(times, TABLESEPS[0], *day)
    trunc = truncate_one(day[0])
    trunc = change_truncation(trunc, len(times), max_trunc)
    formatted = format[trunc[0]:trunc[1]]
    return formatted


def main_week(events: list[UsmbEvent], time: any = dt_now(),
         offset: int = 0, lang: str = "", max_trunc: int = 5) -> list[list[str]]:
    if not events: events = main()
    t = return_dt(time)
    days = days_of_week(t)
    hours = create_table(days)
    table = cross_time_week(hours, events)
    usmb = convert_to_usmb(table)
    prio = prioritize(usmb)
    week = format_week(prio)
    empty = empty_indexes(week)
    empty = limit_empty(empty, len(week))
    week = [week[i] for i in range(len(week)) if i not in empty]
    if not week: raise NoEventException
    display = interject(week, TABLESEPS[1])
    times = format_times(hours[0], offset)
    format = format_lists(times, TABLESEPS[0], *display, TABLESEPS[1])
    trunc = truncate_all(*week)
    trunc = change_truncation(trunc, len(times), max_trunc)
    formatted = format[trunc[0]:trunc[1]]
    header = create_header(offset, lang)
    header = [header[i] for i in range(len(header)) if i-1 not in empty]
    new_header = interject(header, "  ")
    return [new_header] + formatted


if __name__ == '__main__':
    EVENTS = main()
    time = dt_now()

    week = main_week(EVENTS, time, 1, "fr")
    print("\n" + timetable_tostring(week) + "\n")

    day = main_day(EVENTS, time, 1)
    print(timetable_tostring(day) + "\n")



