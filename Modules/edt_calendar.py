"""
Aggregate edt_event.Event in a calendar structure.
"""


from edt_event import *



class Calendar:
    def __init__(self, name: str, source: str = ""):
        self._name = name
        if source.endswith(".ics"):
            self.get_from_file(source)
        else:
            self.url = source
            self.update()



    def sort_by_time(self) -> None:
        """Sort list by start time."""
        self.events = sort_by_time(self.events)



    def get_from_file(self, file: str) -> None:
        """Retreive events in the specified ics file (path must be absolute)."""
        self.events = get_from_file(file)



    def get_from_url(self, url: str) -> None:
        """Download ics file from url and extract data from temp file."""
        self.events = get_from_url(url)



    def update(self) -> str:
        """Update the calendar if it has a url to anchor to."""
        if self.url != "":
            self.get_from_url(self.url)



    def get_all_during(self, time: any) -> list[Event]:
        """Returns all events in range (keeps order)."""
        return [e for e in self.events if e.is_during(time)]



    def get_all_intersect(self, start: any, end: any) -> list[Event]:
        """Returns all events in range (keeps order)."""
        return [e for e in self.events if e.is_intersect(start, end)]



    def get_all_within(self, start: any, end: any) -> list[Event]:
        """Returns all events in range (keeps order)."""
        return [e for e in self.events if e.is_within(start, end)]



    def find_next(self, time: any) -> Event:
        """Returns next event (relative to <time>)."""
        events = self.events
        sort_by_time(events)
        for e in events:
            if e > time:
                return e