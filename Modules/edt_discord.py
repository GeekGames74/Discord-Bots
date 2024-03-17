"""
Link between edt code and discord bot
"""


##########################################################################
# IMPORTS
##########################################################################



import discord as DSC
from discord.ext import commands as CMDS
from discord.ext.commands import Context as CTX
from discord.ext.commands import cog as COG
from discord import Embed as EMBED
from edt_usmb import *
import calendar
import json
from reactech import *
from dsc_converter import dsc_obj
from basic import mixmatch
import asyncio



##########################################################################
# GLOBALS
##########################################################################



PROFILES_FILE = "profiles_file.json"
PROFILES = []
SCHEDULES_FILE = "schedules_file.json"
SCHEDULES = []

NO_EVENT = "No event to display for this time frame."
SURROUND = "```"

DEFAULT_OFFSET = 0
DEFAULT_LANG = "en"
VALID_LANG = ["en", "fr"]

NAME_LEN = (3, 10)
NAME_RE = re.compile(f"^(?=.*[a-zA-Z])[a-zA-Z0-9]{{{NAME_LEN[0]},{NAME_LEN[1]}}}$")
DELETE_KEYWORDS = ["!", "X", "x", "rm", "/"]
DEFAULT_COLOR = "0xffffff"

CMD_EDT = ["edt", "schedule", "sked"]
CMD_EDIT = ["edit", "mod", "modify"]
CMD_REM = ["remove", "delete", "del", "rem", "rm"]
CMD_NEW = ["new", "add", "create", "make"]

class NoNameException(Exception): pass
class IsNameException(Exception): pass



##########################################################################
# DATA
##########################################################################



def is_url(url: str) -> bool:
    """Check if inout is an url."""
    if not url.startswith("http"): return False
    return "://" in url



##########################################################################
# RELATIVE DT FINDER
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
# SCHEDULE CLASS
##########################################################################



class Schedule:
    def __init__(self, names, url: str = "", file_path: str = None,
                 events: list[UsmbEvent] = None) -> None:
        if isinstance(names, str): self.names = [names.lower()]
        else: self.names = [n.lower() for n in names]
        self.names.sort()
        self.events = []
        if events and all([isinstance(e, dict) for e in events]):
            events = [Event(**e) for e in events]
        self.events = convert_to_usmb(events)
        self.url = url
        if file_path: self.populate_events(file_path)
        else: self.populate_events()
        self.date = dt_now()


    def has_name(self, name: str) -> bool:
        """Checks if name is one of schedule's name."""
        return any(n == name.lower() for n in self.name)


    def change_names(self, names) -> None:
        """
        Change the names of the schedule.
        Add names that are not present and remove those which are.
        """
        if isinstance(names, str): names = [names.lower]
        else: names = [n.lower for n in names]
        if sorted(names) == self.names:
            raise NoNameException()
        for n in names:
            if self.has_name(n): names.remove(n)
            else: names.add(n)
        self.names.sort()


    def populate_events(self, sources = None) -> None:
        """Fill object events using its object sources."""
        if not sources: sources = []
        elif isinstance(sources, str): sources = [sources]
        # Here a ConnectionError will happen if the website is offline
        # (during the night) -> Remember to handle in the caller !
        self.events = convert_to_usmb(
            merge_events(self.url, sources, self.events))
        self.date = dt_now()
    

    def to_json(self) -> dict:
        """Return a JSON representation."""
        return {"names": self.names,
                "url": self.url,
                "events": [e.to_json() for e in self.events]}
    

    def get_display(self, time, is_week, offset, lang = None) -> list[list[str]]:
        """Get the timetable display."""
        if is_week: return main_week(self.events, time, offset, lang)
        else: return main_day(self.events, time, offset)


def is_schedule(name: str) -> bool:
    """Returns if there is a schedule with the name <name>."""
    return any([s.has_name(name) for s in SCHEDULES])


def get_schedule(names) -> Schedule:
    """Find and returns first schedule that contains any name."""
    if isinstance(names, str): names = [names]
    for n in names:
        for s in SCHEDULES:
            if s.has_name(n): return s
    raise ValueError("No schedule found.")


def is_same_schedule(names) -> Schedule:
    """
    Check if all names point to the same Schedule.
    If so, return said schedule.
    """
    if isinstance(names, str): names = [names]
    schedules = {get_schedule(n) for n in names}
    if len(schedules) == 1: return schedules[0]
    return None


def save_schedules(file_path: str) -> None:
    """Save all schedules into json file."""
    all_schedules = [s.to_json() for s in SCHEDULES]
    with open(file_path, 'w') as file:
        json.dump(all_schedules, file)


def load_schedules(file_path: str) -> None:
    """Load schedules from a json file (path must be absolute)."""
    global SCHEDULES
    with open(file_path, 'r') as file:
        data = json.load(file)
        SCHEDULES = [Schedule(**d) for d in data]



##########################################################################
# PROFILES
##########################################################################



class EdtProfile():
    def __init__(self, id, schedule: str = "",offset: int = DEFAULT_OFFSET,
                 lang: str = DEFAULT_LANG) -> None:
        self.id = str(id)
        self.schedule = schedule
        self.offset = offset
        self.lang = lang
    

    def to_json(self) -> dict:
        """Return a JSON representation."""
        return {"id": self.id, "schedule": self.schedule,
                "offset": self.offset, "lang": self.lang}


def is_profile(id) -> bool:
    """Check if the given id belongs to an existing profile."""
    return any([p.id == str(id) for p in PROFILES])


def get_profile(id) -> EdtProfile:
    """Get the profile corresponding to the given id."""
    for p in PROFILES:
        if p.id == str(id): return p
    raise ValueError(f"No profile for {id}.")


def save_profiles(file_path: str) -> None:
    """Save all profiles into json file."""
    all_profiles = [p.to_json() for p in PROFILES]
    with open(file_path, 'w') as file:
        json.dump(all_profiles, file)


def load_profiles(file_path: str) -> None:
    """Load profiles from a json file (path must be absolute)."""
    global PROFILES
    with open(file_path, 'r') as file:
        data = json.load(file)
        PROFILES = [EdtProfile(**d) for d in data]



##########################################################################
# FINAL FORMATTING
##########################################################################



def start_end(time: any, is_week: bool) -> (dt, dt):
    """Return start and end of the timetable."""
    t = return_dt(time)
    if is_week:
        weekdays = days_of_week(t)
        table = create_table(weekdays)
        return (table[0][0], table[-1][-1])
    else:
        hours = hours_of_day(t)
        return (hours[0], hours[-1])


def dt_to_timestamp(time: any, mode: str = "") -> str:
    """Format the time to a discord-compatible string timestamp."""
    t = return_dt(time)
    t_in_sec = t.timestamp()
    format_mode = f":{mode}" if mode else ""
    return f"<t:{t_in_sec}{format_mode}>"


def surround(txt: str, sep: str = SURROUND) -> str:
    """Surround string with another string."""
    return f"{sep}{txt}{sep}"


def create_embed(title: str, url: str, description: str, content: str) -> EMBED:
    """Create an embed object from parameters."""
    embed = EMBED(title = title, url = url,
                  color = DEFAULT_COLOR,
                  description = description)
    embed.add_field(name = "", value = content, inline = False)



##########################################################################
# COG
##########################################################################



class EdtCog(COG):
    def __init__(self, bot: CMDS.Bot):
        self.BOT = bot
    

    @CMDS.command(name = "edtprofile", aliases =
                  mixmatch(CMD_EDT + ["default", "def"], ["profile", "prof"]))
    async def edtprofile(self, ctx: CTX, *args) -> None:
        """Set user's offset and/or default schedule to use."""
        id = str(ctx.author.id)
        if len(args) > 3:
            await rt_err(self.BOT, ctx, "⁉️", "Too many arguments provided."); return
        
        # Profile deletion
        elif len(args) == 1 and args[0] in DELETE_KEYWORDS:
            if not is_profile(id):
                await rt_err(self.BOT, ctx, "🚫", "No profile found for your Uid."); return
            else:
                PROFILES.remove(get_profile(id))
                await rt_ok(self.BOT, ctx, "Profile deleted successfully."); return
        
        # Detect arguments
        detect = {"offset": False, "lang": False, "schedule": False}
        modify = is_profile(id)
        profile = get_profile(id) if modify else EdtProfile(id)
        is_an_offset = re.compile("^[+|-]?[0-9]{1-2}$")
        unrecognized, msg = [], []
        for a in args:
            if is_an_offset.match(a):
                profile.offset = int(a.strip('+').strip('-'))
                if a.startswith('-'): profile.offset *= -1
                detect["offset"] = True
            elif a.lower() in VALID_LANG:
                profile.lang = a.lower()
                detect["lang"] = True
            elif is_schedule(a.lower()):
                profile.schedule = a.lower()
                detect["schedule"] = True
            else: unrecognized.append(a)

        new_schedule = f"'`{profile.schedule}`'" if profile.schedule else "None"
        if unrecognized: # If one or more arguments are not resolved
            msg += [rt_warn(self.BOT, ctx, f"Some arguments could not be resolved :`{'`, `'.join(unrecognized)}`.")]
        if modify and not any(detect.values()): # Nothing to change
            msg += [rt_ok(self.BOT, ctx, "Profile did not change.")]
        else: # Main reactech message
            start = "Updated" if modify else "Created"
            msg += [rt_ok(self.BOT, ctx, f"{start} profile with offset `{format_offset(profile.offset)}`
                    , schedule {new_schedule} and language `{profile.lang}`.")]
        asyncio.gather(*msg)



    @CMDS.command(name = "modifyedt", aliases =
                  mixmatch(CMD_EDIT + CMD_NEW + CMD_REM, CMD_EDT))
    async def modifyedt(self, ctx: CTX, *args) -> None:
        """Create, modify or delete a schedule."""
        if len(args) < 2: await rt_err(self.BOT, ctx, "⁉️", f"Not enough arguments."); return
        if await self.try_delete_schedule(ctx, args): return
        names = [a for a in args if is_schedule(a)]
        # need to handle creation
        schedule = is_same_schedule(names)
        if not schedule: rt_warn(self.BOT, ctx, "Must specify exactly one schedule."); return
        self.try_mod_schedule(ctx, schedule, *args)



    async def try_mod_schedule(self, ctx: CTX, schedule: Schedule, *args) -> None:
        """Try modifying the given schedule."""
        urls = [a for a in args if is_url(a)]
        if len(urls) > 1: rt_warn(self.BOT, ctx, "Must specify at most one url."); return
        others = [a for a in args if a not in urls and not is_schedule(a)]
        files = self.download_ics(ctx, "")
        msg = []
        if others: msg += [rt_warn(self.BOT, ctx, f"Argument(s) `{'`, `'.join(others)}` could not be resolved.")]
        if urls: msg += [rt_ok(self.BOT, ctx, f"URL successfully changed.")]
        try: schedule.populate_events(*files)
        except Exception as e: rt_warn(self.BOT, ctx, f"Events did not import correctly :\n{e}"); return
        if urls or files: msg += [rt_ok(self.BOT, ctx, f"Events updated.")]
        if urls: schedule.url = urls[0]
        asyncio.gather(*msg)



    async def try_delete_schedule(self, ctx: CTX, *args) -> bool:
        """Handling for deletion of schedules."""
        nb_del = len([a for a in args if a in DELETE_KEYWORDS])
        if not nb_del: return False
        if len(args) - nb_del >= 1:
            scheds = [a for a in args if a not in DELETE_KEYWORDS]
            success, failures, msg = [], [], []
            for s in scheds:
                if is_schedule(s):
                    SCHEDULES.remove(get_schedule(s))
                    success += [s]
                else: failures += [s]
            if success : msg += [rt_ok(self.BOT, ctx, f"Schedule(s) `{'`, `'.join(success)}` have been deleted.")]
            if failures: msg += [rt_warn(self.BOT, ctx, f"Argument(s) `{'`, `'.join(failures)}` could not be resolved.")]
            asyncio.gather(*msg); return True
        else: await rt_err(self.BOT, ctx, "❓", f"No schedules were specified."); return True



    async def download_ics(self, source, path: str) -> list[str]:
        """
        Download .ics attachments and save them.
        Returns path of saved files.
        """
        msg = dsc_obj(self.BOT, source, "message")
        files = []
        for att in msg.attachments:
            if att.filename.lower().endswith(".ics"):
                with open(path + "/" + att.filename, 'x') as file:
                    await att.save(file)
                    files += [path + "/" + att.filename]
        return files
    