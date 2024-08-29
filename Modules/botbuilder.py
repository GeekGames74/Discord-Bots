"""
Creation and setup of the bot, with optionnal running.
"""



##################################################
# IMPORTS
##################################################



from discord.ext.commands.bot import Bot
from discord import Intents, Activity

from Modules.data import data_JSON
from Modules.basic import makeiterable


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
               intents = intents)
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