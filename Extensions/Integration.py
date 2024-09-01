"""
Commands and listeners likely on all bots.
Contains generic setup and managing functions.
"""



##################################################
# IMPORTS
##################################################



import discord as DSC
from discord.ext import commands as CMDS
from discord.ext.commands.bot import Bot
from discord.ext.commands.context import Context as CTX

from os import listdir, path
from inspect import getmembers, isclass
from re import compile

from Modules.basic import mixmatch, plural, remove_punct, least_one
from Modules.reactech import Reactech



async def setup(bot: Bot):
    await bot.add_cog(Plugins(bot))
    await bot.add_cog(Plugins_plus(bot))
    await bot.add_cog(Plugins_shorthand(bot))



##################################################
# GLOBALS
##################################################




_PLUGINS = {
    "cogs": ["c", "cog", "cogs"],
    "exts": ["e", "x", "xt", "xts", "ext", "exts", "extension", "extensions"],
    "plugins": ["plugin", "plugins"],
    "list": ["l", "list", "show", "display"],
    "load":  ["a", "load", "add", "append"],
    "reload": ["r", "reload", "reset", "restart"],
    "unload": ["u", "remove", "unload"]
}



##################################################
# FUNCTIONS
##################################################



def detect_exts(plugins: tuple) -> tuple:
        """Detects the list of exts to access. Returns {exts}, {not_exts}."""
        regex = compile(f"^[A-Z].*\.py$") # Regex for ext filename
        exts = set() ; not_exts = set() # Sets to avoid duplicates
        plugins = set([remove_punct(i.capitalize()) for i in plugins])
        print(plugins)
        all_exts = set([i.removesuffix(".py") for i in listdir(path.dirname(__file__)) if regex.match(i)])
        if not plugins or "*" in plugins or "All" in plugins:
            exts = all_exts.copy() ; not_exts.add("*")
            plugins.discard("*") ; plugins.discard("All")
        for p in plugins:
            if p in _PLUGINS["exts"]: exts = exts.union(all_exts)
            elif p in all_exts: exts.add(p)
            else:
                if p in _PLUGINS["cogs"]: not_exts.add("*")
                else: not_exts.add(p)
        return exts, not_exts



def get_all_cogs(bot: Bot) -> dict:
    """
    Returns a set of all cogs (loaded or not) available to the bot.
    This means cogs from unloaded extensions will not be included.
    """
    all_exts = set(bot.extensions.values()) ; all_cogs = {}
    for ext in all_exts:
        for name, clss in getmembers(ext, isclass):
            if issubclass(clss, CMDS.Cog):  
                all_cogs[name] = clss
    return all_cogs



def detect_cogs(bot: Bot, not_exts: set) -> tuple:
    """Detects the list of cogs to access. Returns {cogs}, {unknown}."""
    cogs = {} ; unknown = set()
    all_cogs = get_all_cogs(bot)
    if "*" in not_exts:
        cogs = all_cogs.copy() ; not_exts.remove("*")
    for i in not_exts:
        if i in all_cogs.keys(): cogs[i] = all_cogs[i]
        else: unknown.add(i)
    return cogs, unknown



##################################################
# PLUGINS
##################################################



class Plugins(CMDS.Cog):
    """Manage (load, unload and reload) plugins (cogs and exts)."""
    def __init__(self, bot: Bot):
        self.bot = bot
        self.Reactech = Reactech(bot)


    def __unload(self):
        if self.bot.get_cog("Plugins_plus"):
            self.bot.remove_cog("Plugins_plus")
        if self.bot.get_cog("Plugins_shorthand"):
            self.bot.remove_cog("Plugins_shorthand")
    


    @CMDS.command(name = "plugins", aliases = mixmatch(["manage", ""],
            _PLUGINS["plugins"], keeporder = True, remove = "plugins"))
    @CMDS.is_owner()
    async def plugins(self, ctx: CTX, action: str = "list", *plugins: str) -> None:
        """Manage plugins in relation to the current bot instance."""
        action = action.lower() ; txt = ""
        if not action or action in _PLUGINS["cogs"] + _PLUGINS["exts"] + ["*", "all"]:
            plugins = set(plugins).union(set([action]))
            action = "list"

        # LIST
        if action in _PLUGINS["list"]:
            cogs = self.bot.cogs ; exts = self.bot.extensions
            _exts = [i.removeprefix("Extensions.") for i in exts]
            
            if not plugins or least_one(["*", "all"] + _PLUGINS["cogs"], plugins):
                if len(cogs) == 0: txt += "0 cogs currently loaded.\n" # On 0
                else: txt += f"{len(cogs)} cog{plural(cogs)} currently loaded: `" + "`, `".join(cogs) +"`\n"
            
            if not plugins or least_one(["*", "all"] + _PLUGINS["exts"], plugins):
                if len(_exts) == 0: txt += f"0 extensions currently loaded.\n" # On 0
                else: txt += f"{len(_exts)} extension{plural(_exts)} currently loaded: `" + "`, `".join(_exts) +"`\n"
            
            txt.removesuffix("\n")
            if ctx: await ctx.send(txt)
            return txt
        
        feedback = {i: {"cogs": set(), "exts": set()} for i in ["ok", "nochange"]}
        feedback["unknown"] = set() ; feedback["errors"] = {"cogs": {}, "exts": {}}

        # LOAD
        if action in _PLUGINS["load"]:
            exts, not_exts = detect_exts(plugins)
            
            for ext in exts: # Extensions
                try: await self.bot.load_extension("Extensions." + ext)
                except CMDS.ExtensionAlreadyLoaded: feedback["nochange"]["exts"].add(ext)
                except CMDS.ExtensionNotFound: feedback["unknown"].add(ext)
                except Exception as e: feedback["errors"]["exts"][ext] = e.__class__.__name__
                else: feedback["ok"]["exts"].add(ext)
            
            cogs, unknown = detect_cogs(self.bot, not_exts)
            feedback["unknown"] = feedback["unknown"].union(unknown)

            for name, cog in cogs.items(): # Cogs
                try: await self.bot.add_cog(cog(self.bot))
                except DSC.ClientException: feedback["nochange"]["cogs"].add(name)
                except NameError: feedback["unknown"].add(name)
                except Exception as e: feedback["errors"]["cogs"][name] = e.__class__.__name__
                else: feedback["ok"]["cogs"].add(name)
            
            print(feedback)







##################################################
# PLUGINS_PLUS
##################################################



class Plugins_plus(CMDS.Cog):
    """Aditionnal commands for general purpose."""
    def __init__(self, bot: Bot):
        self.bot = bot
        self.Reactech = Reactech(bot)
        if not bot.get_cog("Plugins"):
            bot.add_cog(Plugins(bot))



    @CMDS.command(name = "loadplugins", aliases = mixmatch(_PLUGINS["load"][1:],
            _PLUGINS["plugins"] + ["all"], keeporder = True, remove = "loadplugins"))
    async def loadplugins(self, ctx: CTX, *plugins: str) -> str:
        """Loads plugins to the current bot instance."""



    @CMDS.command(name = "reloadplugins", aliases = mixmatch(_PLUGINS["reload"][1:],
            _PLUGINS["plugins"] + ["all"], keeporder = True, remove = "reloadplugins"))
    async def reloadplugins(self, ctx: CTX, *plugins: str) -> str:
        """Reloads plugins in the current bot instance."""



    @CMDS.command(name = "unloadplugins", aliases = mixmatch(_PLUGINS["unload"][1:],
            _PLUGINS["plugins"] + ["all"], keeporder = True, remove = "unloadplugins"))
    async def unloadplugins(self, ctx: CTX, *plugins: str) -> str:
        """Unloads plugins from the current bot instance."""
    


    @CMDS.command(name = "listplugins", aliases = mixmatch(_PLUGINS["list"][1:],
            _PLUGINS["plugins"] + ["all"], keeporder = True, remove = "listplugins"))
    async def listplugins(self, ctx: CTX, plugins: str) -> str:
        """Lists plugins in the current bot instance."""
            


##################################################
# PLUGINS_SHORTHAND
##################################################



class Plugins_shorthand(CMDS.Cog):
    """Shorthand commands for specific use of Plugins."""
    def __init__(self, bot: Bot):
        self.bot = bot
        self.Reactech = Reactech(bot)
        if not bot.get_cog("Plugins"):
            bot.add_cog(Plugins(bot))



    @CMDS.command(name = "loadcogs", aliases = mixmatch(_PLUGINS["load"][1:],
            _PLUGINS["cogs"][1:], keeporder = True, remove = "loadcogs"))
    async def loadcogs(self, ctx: CTX) -> str:
        """Loads all cogs to the current bot instance."""



    @CMDS.command(name = "loadexts", aliases = mixmatch(_PLUGINS["load"][1:],
            _PLUGINS["exts"][2:], keeporder = True, remove = "loadexts"))
    async def loadexts(self, ctx: CTX) -> str:
        """Loads all exts to the current bot instance."""



    @CMDS.command(name = "reloadcogs", aliases = mixmatch(_PLUGINS["reload"][1:],
            _PLUGINS["cogs"][1:], keeporder = True, remove = "reloadcogs"))
    async def reloadcogs(self, ctx: CTX) -> str:
        """Reloads all cogs in the current bot instance."""



    @CMDS.command(name = "reloadexts", aliases = mixmatch(_PLUGINS["reload"][1:],
            _PLUGINS["exts"][2:], keeporder = True, remove = "reloadexts"))
    async def reloadexts(self, ctx: CTX) -> str:
        """Reloads all exts in the current bot instance."""



    @CMDS.command(name = "unloadcogs", aliases = mixmatch(_PLUGINS["unload"][1:],
            _PLUGINS["cogs"][1:], keeporder = True, remove = "unloadcogs"))
    async def unloadcogs(self, ctx: CTX) -> str:
        """Unloads all cogs from the current bot instance."""



    @CMDS.command(name = "unloadexts", aliases = mixmatch(_PLUGINS["unload"][1:],
            _PLUGINS["exts"][2:], keeporder = True, remove = "unloadexts"))
    async def unloadexts(self, ctx: CTX) -> str:
        """Unloads all exts from the current bot instance."""



    @CMDS.command(name = "listcogs", aliases = mixmatch(_PLUGINS["list"][1:],
            _PLUGINS["cogs"][1:], keeporder = True, remove = "listcogs"))
    async def unloadcogs(self, ctx: CTX) -> str:
        """Lists all cogs in the current bot instance."""



    @CMDS.command(name = "listexts", aliases = mixmatch(_PLUGINS["list"][1:],
            _PLUGINS["exts"][2:], keeporder = True, remove = "listexts"))
    async def unloadexts(self, ctx: CTX) -> str:
        """Lists all exts in the current bot instance."""

