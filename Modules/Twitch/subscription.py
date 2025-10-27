"""
Twitch EventSub subscription management.
"""



##################################################
# IMPORTS
##################################################



from discord.ext.commands import Bot
from time import time
from Modules.data import data
from Modules.Twitch.action import Action, check_requirements
from Modules.Twitch.handler import Handler



##################################################
# GLOBALS
##################################################



_SUBSCRIPTIONS = data("Resources/Files/Twitch/events.json", filenotfound = False)



##################################################
# SUBSCRIPTION
##################################################



class Subscription:
    """Represent a Twitch EventSub subscription."""
    def __init__(self, name: str, conditions: dict = None,
            info: dict = None, twitch_id: str = None,
            helix_id: str = None, key: str = None, created: float = None,
            handlers: Handler|list = None) -> None:

        self.name = name
        # Unique identifier for this subscription
        self.key = key or str(int(time() * 1000))
        self.helix_id = helix_id # Helix ID assigned by Twitch (if any)
        self.info = info or {} # Open field for use-case info
        self.created = created or time()

        if name not in _SUBSCRIPTIONS: # Check type validity
            raise ValueError(f"Invalid subscription type '{name}'"
                f"Expected one of: {list(_SUBSCRIPTIONS.keys())}")
        self.type = _SUBSCRIPTIONS[name]["type"] # Type of subscription

        self.twitch_id = twitch_id
        
        # Check conditions validity (names and types)
        self.conditions = check_requirements(
            conditions or {}, _SUBSCRIPTIONS[name].get("conditions", {})
        )

        if isinstance(handlers, Handler):
            self.handlers = [handlers]
        elif isinstance(handlers, list):
            self.handlers = handlers
        else: self.handlers = []


    @classmethod
    def from_dict(cls, data: dict):
        """Create a Subscription from a dictionary."""
        return cls(
            name = data["name"],
            info = data.get("info", {}),
            twitch_id = data.get("twitch_id"),
            helix_id = data.get("helix_id"),
            conditions = data.get("conditions", {}),
            handlers = [Handler.from_dict(h) for h in data.get("handlers", [])],
            key = data.get("key"),
            created = data.get("created")
        )
    

    def to_dict(self, recursive: bool = True) -> dict:
        """Convert the subscription to a dictionary."""
        return {
            "name": self.name,
            "key": self.key,
            "info": self.info,
            "twitch_id": self.twitch_id,
            "helix_id": self.helix_id,
            "conditions": self.conditions,
            "handlers": [h.to_dict() for h in self.handlers] if recursive else None,
            "created": self.created
        }


    def get_action(self, session_id: str) -> Action:
        """Get the Action associated with this subscription, if any."""
        json = { # Create the JSON payload for the subscription
            "type": self.type,
            "condition": self.conditions,
            "transport": {
                "method": "websocket",
                "session_id": session_id
            }
        }
        return Action(
            type = "eventsub_add",
            json = json,
            user = self.twitch_id
        )


    async def handle(self, bot: Bot, event: dict) -> None:
        """Handle an incoming event."""
        for handler in self.handlers:
            await handler.call(bot, self.to_dict(recursive = False), event)



##################################################
# MAIN
##################################################



if __name__ == "__main__":
    pass