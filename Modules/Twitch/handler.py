"""
Twitch EventSub subscription handler management.
"""



##################################################
# IMPORTS
##################################################



from discord.ext.commands import Bot
from discord.ext.commands.errors import CommandError
import asyncio



##################################################
# HANDLER
##################################################



class Handler:
    """Represent a Twitch EventSub subscription handler."""
    def __init__(self, cog: str, function: str, args: list = None,
                 ignore_missing: bool = False) -> None:
        self.cog = cog # Name of the cog containing the handler
        self.function = function # Name of the handler function
        self.args = args or [] # Additional arguments to pass to the handler
        self.ignore_missing = ignore_missing # Whether to ignore missing handlers


    @classmethod
    def from_dict(cls, data: dict):
        """Create a Handler from a dictionary."""
        return cls(
            cog = data["cog"],
            function = data["function"],
            args = data.get("args", []),
            ignore_missing = data.get("ignore_missing", False)
        )
    

    def to_dict(self) -> dict:
        """Convert the handler to a dictionary."""
        return {
            "cog": self.cog,
            "function": self.function,
            "args": self.args,
            "ignore_missing": self.ignore_missing
        }


    async def call(self, bot: Bot, subscription: dict, event: dict) -> None:
        """Call the handler function with the given data."""
        cog = bot.get_cog(self.cog) if bot else None
        if not cog: # Function can only be from a loaded cog
            if not self.ignore_missing:
                print(f"Cog '{self.cog}' not found in bot.")
            return
        # Get the handler function
        func = getattr(cog, self.function, None)
        if not func: # Function not found in cog
            if not self.ignore_missing:
                print(f"Handler '{self.function}' not found in cog '{self.cog}'.")
            return
        try:
            # Call the handler function
            if asyncio.iscoroutinefunction(func):
                # If the function is a coroutine, await it
                await func(subscription, event, self.args)
            else: func(subscription, event, self.args)
        except Exception as e:
            print(f"Error in handler '{self.function}' of cog '{self.cog}': {e}")
            return



##################################################
# MAIN
##################################################



if __name__ == "__main__":
    pass