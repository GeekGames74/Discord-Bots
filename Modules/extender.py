"""
Base module to load, unload and reload extensions.
This does not include the commands, but the direct descending methods.
See in 'Extender' extension for those.
The Extender class and its function would fit better in an extension,
but they are needed to import said extensions, so we split the code.
Therefore, the probable uses are the linked cog and on_ready events.
"""



##################################################
# IMPORTS
##################################################



from discord.ext.commands import bot as BOT

from importlib import reload
from types import ModuleType

from basic import makeiterable



##################################################
# FUNCTIONS
##################################################



def reload_module(modules: any) -> (list, list):
    """
    Reload module (string or module element).
    Also accepts an iterable to reload several modules.
    """
    valid = []; invalid = [] # List of resolved or unresolved names (if strings)
    modules = makeiterable(modules)
    for name in modules:
        # If provided module is already a ModuleType
        if isinstance(name, ModuleType):
            mod = name # No nned to convert it
        # Else, resolve the name as string
        elif isinstance(name, str):
            try: # NOTE : will look for imported name, not original name
                mod = globals()[mod]
                name = mod.__name__
            # Can only reload modules by name if it is already imported
            except KeyError as e:
                invalid.append(e)
                continue
        else: raise TypeError(f"Given '{name}' of type '{type(name).__name__}';" +
                              " Expected str or ModuleType") # Generic error
        reload(mod) # Reload here
        valid.append(name) # Feedback
    return (valid, invalid)



##################################################
# CLASS
##################################################



class Extender:
    """
    Utility class for extension/cog management.
    Is neither extension nor cog in itself.
    """
    def __init__(self, bot: BOT, init: list = None):
        self.bot = bot
        self.load(init)


    async def load(self, names: list = None) -> None:
        """Load extension(s)"""
        names = makeiterable(names)
        for name in names:
            await self.bot.load_extension(name)
    

    async def reload(self, names: list = None) -> None:
        """Reload extension(s)"""
        names = makeiterable(names)
        for name in names:
            await self.bot.reload_extension(name)


    async def unload(self, names: list = None) -> None:
        """Unload extension(s)"""
        names = makeiterable(names)
        for name in names:
            await self.bot.unload_extension(name)