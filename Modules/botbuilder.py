"""
Creation and setup of the bot, with optionnal running.
"""



##################################################
# IMPORTS
##################################################



from discord.ext.commands.bot import Bot
from discord import Intents, Activity
from asyncio import run

from Modules.data import data_JSON, data_TXT
from Modules.basic import makeiterable
from Modules.reactech import Reactech



##################################################
# FUNCTIONS
##################################################



def build_bot(source: str) -> Bot:
    """
    Create the bot instance with the given source file.
    Location is given relative to /Resources/. directory.
    """
    data = data_JSON("/Resources/" + source)
    base_intent = getattr(Intents(), data["base_intent"])
    intents = toggle_intents(base_intent(), data["target_intents"])
    bot = Bot(data["prefix"], case_insensitive = True,
               strip_after_prefix = True, activity = Activity(),
               intents = intents) # Default activity and status are set in @on_ready()
    for ext in data["base_extensions"]: # No extension is load by default
        name = "Extensions." + ext.removesuffix(".py").capitalize()
        run(bot.load_extension(name)) # load is asynchronous
    location = "/Credentials/" + data["token_location"]
    TOKEN = data_TXT(location, "token")["token"]
    bot.run(TOKEN, reconnect = True)
    return bot



def toggle_intents(obj: Intents, intents: list) -> Intents:
    """Toggle the intents in the obj, then return it."""
    intents = makeiterable(intents)
    for name in intents:
        value = getattr(obj, name)
        if isinstance(value, bool):
            value = not value
        else: raise Exception()
        obj.__setattr__(name, value)
    return obj



##################################################
# MAIN
##################################################



if __name__ == "__main__":
    pass