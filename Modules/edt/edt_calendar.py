"""
Aggregate edt_event.Event in a calendar structure.
"""


from edt_event import *
from edt_table import *



class Calendar:
    def __init__(self, name: str, source: str = ""):
        self.aliases = [name]
        self.url = source if source.startswith("http") else ""
        self.events = get_from_source(source)



    def sort_by_time(self) -> None:
        """Sort list by start time."""
        self.events = sort_by_time(self.events)



    def get_from_source(self, source: str) -> None:
        """Get events from the given URL or file."""
        self.events = get_from_source(source)



    def update(self) -> str:
        """Update the calendar if it has a url to anchor to."""
        if self.url != "":
            self.get_from_source(self.url)



    def get_all_during(self, time: any) -> list[Event]:
        """Returns all events that surround the time(keeps order)."""
        return get_all_during(self.events, time)



    def get_all_intersect(self, start: any, end: any) -> list[Event]:
        """Returns all events that share the time range (keeps order)."""
        return get_all_intersect(self.events, start, end)



    def get_all_within(self, start: any, end: any) -> list[Event]:
        """Returns all events contained within the time range (keeps order)."""
        return get_all_within(self.events, start, end)



    def find_next(self, time: any) -> Event:
        """Returns next event (relative to <time>)."""
        return find_next(self.events, time)