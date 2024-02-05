"""
Module to import events from an ics file or an url
"""



import icalendar
import json
from datetime import datetime as dt



def return_dt(time: any) -> dt:
    """Convert any to dt attribute."""
    if  isinstance(time, dt): return time
    elif isinstance(time, icalendar.Event):
        return event['dt' + attrib].dt
    elif isinstance(time, dict):
        return str_to_dt(event[attrib])
    elif isinstance(time, str):
        return dt.strptime(time, "%Y-%m-%d %H:%M:%S%z")
    else: raise TypeError("Invalid or Unsupported type")



class Event:
    def __init__(self, summary: str, start: any, end: any, location: str, description: str):
        self.summary = summary
        self.start = return_dt(start)
        self.end = return_dt(end)
        self.location = location
        self.description = description
        self.professor = self.get_prof()
        self.subject = self.get_subject()



    def get_prof(self) -> list:
        """Get professors from the event description."""        
        desc = self.description
        while "\n\n" in desc:
            desc = desc.replace("\n\n", "\n")
        desc = desc.split("\n")
        if len(desc) < 3: return []
        profs = []
        for i in desc:
            if not i.isupper(): continue
            allow = "ABCDEFGHIJKLMNOPQRSTUVWXYZ -ÉÂÇÈÊÔÙÀÍÎÏÙÚÑÖÜ"
            if not all([c in allow for c in i]): continue
            cut = i.split(" ")
            if not all([1 < len(seg) < 5 for seg in cut]): continue
            profs.append(i)
        return profs



    def is_within(self, arg: any) -> bool:
        """Check if an event's start or end time is within a specified time frame."""
        time = return_dt(arg)
        return self.start <= time <= self.end
        


    def get_subject(self) -> str:
        """Get color of an event (based of the display on website)."""
        color = "white"
        
        subjects = {"green": ["dev", "prog", "C#", "code"],
                    "yellow": ["sys", "os", "reseau"],
                    "blue": ["bd", "sql", "donnees"],
                    "purple": ["math", "outil", "phys", "graph"],
                    "orange": ["web", "html", "css", "php"],
                    "brown": ["econ", "gestion", "entrep"],
                    "light_blue": ["comm", "droit"],
                    "pink": ["angl", "engl", "lang", "ppp", "perso"],
                    "red": ["eval", "note"]}
        
        professors = {"green": ['GRUSON NATHALIE', 'AYARI TAKOUA', 'BHANOT ARGHEESH', 'BARRY GUILLAUME', ],
                    "yellow": ['DIARD BENOIT', 'ARFAOUI KHADIJA', ],
                    "blue": ['COLIN PASCAL', 'MEGER NICOLAS', 'GILBERT NICOLAS', 'GAUDIN THIBAUT', 'RIPOCHE TEDDY', 'LAISSARD GÉRARD', ],
                    "purple": ['VOIRON NICOLAS', 'MARTIN UGO', 'MARTELET VALERIE', 'MORTREUX FABIENNE', 'KOSSAKOWSKI ROMAN', 'THERY HERVÉ', ],
                    "orange": ['DAMAS LUC', 'CHANET THOMAS', ],
                    "brown": ['GAILLARD YOHANN', 'COUTURIER VINCENT', 'LIDONE DA SILVA FERNANDA', ],
                    "light_blue": ['GRAZIANO EMMANUELLE', 'THABUIS PIERRE', ],
                    "pink": ['ZUSCHLAG CODY', 'VIBRAC STÉPHANIE', ]}

        prof = self.professor
        desc = self.description.lower().replace("é", "e")
        sum = self.summary.lower().replace("é", "e")

        if not prof: return "grey"

        for k, v in subjects.items():
            for i in v:
                if i in desc or i in sum:
                    color = k

        if color != "white": return color

        for k, v in professors.items():
            for p in prof:
                if p in v:
                    return k
                
        return color
