"""
Manage extensions and cogs on the bot instance.
Might hold command control too in the future.
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
from asyncio import gather

from Modules.basic import *
from Modules.reactech import Reactech



async def setup(bot: Bot):
    await bot.add_cog(Plugins(bot))
    await bot.add_cog(Plugins_plus(bot))
    await bot.add_cog(Plugins_shorthand(bot))



##################################################
# GLOBALS
##################################################



_PLUGINS = {
    "all": ["*", "all", "All", "ALL"],
    "cogs": ["c", "cog", "cogs"],
    "exts": ["e", "x", "xt", "xts", "ext", "exts", "extension", "extensions"],
    "plugins": ["plugin", "plugins"],
    "list": ["l", "list", "show", "display"],
    "load":  ["a", "load", "add", "append"],
    "reload": ["r", "rl", "reload", "reset", "restart"],
    "unload": ["u", "remove", "unload"]
}

_FEEDBACK = {
    "ok": (" has been ", " have been "),
    "nochange": (" is ", " are "), 
    "unknown": (" was not found: `", " were not found: `"),
    "errors": (" raised an error:\n`", " raised an error:\n`"),
    "load": {"ok": "loaded: `", "nochange": "already loaded: `"},
    "reload": {"ok": "reloaded: `", "nochange": "not loaded: `"},
    "unload": {"ok": "unloaded: `", "nochange": "already unloaded: `"},
}



##################################################
# FUNCTIONS
##################################################



def detect_exts(plugins: tuple) -> tuple:
        """Detects the list of exts to access. Returns {exts}, {not_exts}."""
        regex = compile(f"^[A-Z].*\.py$") # Regex for ext filename
        exts = set() ; not_exts = set() # Sets to avoid duplicates
        plugins = set([remove_punct(i.capitalize()) for i in plugins])
        all_exts = set([i.removesuffix(".py") for i in listdir(path.dirname(__file__)) if regex.match(i)])
        if not plugins or least_one(_PLUGINS["all"], plugins):
            exts = all_exts.copy() ; not_exts.add(_PLUGINS["all"][0])
            for i in _PLUGINS["all"]:
                plugins.discard(i)
        for p in plugins:
            if p.lower() in _PLUGINS["exts"]: exts = exts.union(all_exts)
            elif p in all_exts: exts.add(p)
            else:
                if p.lower() in _PLUGINS["cogs"]: not_exts.add(_PLUGINS["all"][0])
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
    if _PLUGINS["all"][0] in not_exts:
        cogs = all_cogs.copy() ; not_exts.remove("*")
    for i in not_exts:
        if i in all_cogs.keys(): cogs[i] = all_cogs[i]
        else: unknown.add(i)
    return cogs, unknown



async def format_feedback(feedback: dict, action: str, ctx: CTX) -> str:
    """Returns a feedback message based on the action performed on plugins."""
    # {ok:{cogs:(),exts:()},nochange:{cogs:(),exts:()},notfound:(),errors:{cogs:{},exts:{}}}
    txt = [feedback_line(action, "ok", "cog", feedback["ok"]["cogs"]) + 
           feedback_line(action, "ok", "extension", feedback["ok"]["exts"]),
           feedback_line(action, "nochange", "cog", feedback["nochange"]["cogs"]) +
           feedback_line(action, "nochange", "extension", feedback["nochange"]["exts"]),
           feedback_line(action, "unknown", "object", feedback["unknown"]),
           feedback_line(action, "errors", "cog", feedback["errors"]["cogs"]) +
           feedback_line(action, "errors", "extension", feedback["errors"]["exts"])]
    for i in range(4): # Remove trailing '\n'
        while txt[i].endswith("\n"): txt[i] = txt[i].removesuffix("\n")
    if ctx: # Send user feedback
        gatherer = [] ; react = Reactech(ctx.bot) ; e = "ℹ️" if action != "reload" else "⚠️"
        if txt[0]: gatherer.append(react.reactech_channel(ctx, "✅", txt[0]))
        if txt[1]: gatherer.append(react.reactech_channel(ctx, e, txt[1]))
        if txt[2]: gatherer.append(react.reactech_channel(ctx, "❓", txt[2]))
        if txt[3]: gatherer.append(react.reactech_channel(ctx, "❌", txt[3]))
        if not gatherer: gatherer.append(react.reactech_channel(ctx, "ℹ️", "Nothing changed."))
        gather(*gatherer)
    return "\n\n".join([i for i in txt if i]).replace("`", "'")



def feedback_line(action: str, status: str, type: str, input: set) -> str:
    """Returns a formatted line for the feedback function."""
    if len(input) == 0: return ""
    input = sorted(input)

    txt = f"{len(input)} {type}{plural(input)}" # X thing(s)
    txt += _FEEDBACK[status][plural(input,0,1,0,1)] # has/have been [+ simple action descriptor]
    if status in ["ok", "nochange"]: # requires more complex action descriptor (loaded...)
        txt += _FEEDBACK[action][status] # custom descriptor
    
    if status != "errors": txt += "`, `".join(input) + "`\n"
    else: txt += "`,\n`".join([f"{k}: {v}" for k,v in input.items()]) + "`\n\n"
    return txt



async def call_plugins(self, ctx, action, plugins) -> str:
    """Calls plugins with the given arguments and returns the feedback message."""
    cmd = self.bot.get_command("plugins")
    if cmd: return await cmd.callback(self, ctx, action, *plugins)
    else: self.Reactech.reactech_user(ctx, "❌",
        "The `Plugins` cog was unloaded or its command removed.")



##################################################
# PLUGINS
##################################################



class Plugins(CMDS.Cog):
    """Manage (load, unload and reload) plugins (cogs and exts)."""
    def __init__(self, bot: Bot):
        self.bot = bot
        self.Reactech = Reactech(bot)


    async def cog_unload(self):
        await self.bot.remove_cog("Plugins_plus")
        await self.bot.remove_cog("Plugins_shorthand")
    


    @CMDS.command(name = "plugins", aliases = mixmatch(["manage", ""],
            _PLUGINS["plugins"], keeporder = True, remove = "plugins"))
    @CMDS.is_owner()
    async def plugins(self, ctx: CTX, action: str = "list", *plugins: str) -> str:
        """Manage plugins in relation to the current bot instance."""
        action = action.lower() ; txt = ""
        if not action or action in _PLUGINS["cogs"] + _PLUGINS["exts"] + _PLUGINS["all"]:
            plugins = set(plugins).union(set([action]))
            action = "list"
        globalscope = not plugins or least_one(_PLUGINS["all"], plugins)

        # LIST
        if action in _PLUGINS["list"]:
            cogs = sorted(self.bot.cogs) ; exts = self.bot.extensions
            _exts = sorted([i.removeprefix("Extensions.") for i in exts])
            showexts = least_one(_PLUGINS["exts"], plugins) or globalscope
            showcogs = least_one(_PLUGINS["cogs"], plugins) or globalscope
            
            if showcogs or not showexts:
                if len(cogs) == 0: txt += "0 cogs currently loaded.\n" # On 0
                else: txt += f"{len(cogs)} cog{plural(cogs)} currently loaded: `" + "`, `".join(cogs) +"`\n"
            
            if showexts or not showcogs:
                if len(_exts) == 0: txt += f"0 extensions currently loaded.\n" # On 0
                else: txt += f"{len(_exts)} extension{plural(_exts)} currently loaded: `" + "`, `".join(_exts) +"`\n"
            
            txt.removesuffix("\n")
            if ctx: await ctx.send(txt)
            return txt.replace("`", "'")
        
        feedback = {i: {"cogs": set(), "exts": set()} for i in ["ok", "nochange"]}
        feedback["unknown"] = set() ; feedback["errors"] = {"cogs": {}, "exts": {}}
        exts, not_exts = detect_exts(plugins)

        # LOAD
        if action in _PLUGINS["load"]:
            action = "load"
            for ext in exts: # Extensions
                try: await self.bot.load_extension("Extensions." + ext)
                except CMDS.ExtensionAlreadyLoaded: # Already loaded
                    if not globalscope: # Ignore exception if all wildcard is used
                        feedback["nochange"]["exts"].add(ext)
                except CMDS.ExtensionNotFound: feedback["unknown"].add(ext) # Not found
                except Exception as e: feedback["errors"]["exts"][ext] = e
                else: feedback["ok"]["exts"].add(ext)
            
            cogs, unknown = detect_cogs(self.bot, not_exts)
            feedback["unknown"] = feedback["unknown"].union(unknown)

            for name, cog in cogs.items(): # Cogs
                try: await self.bot.add_cog(cog(self.bot))
                except DSC.ClientException:
                    if not cog.__module__.removeprefix("Extensions.") in exts: # If not added during ext loading
                        if not globalscope: # Ignore exception if all wildcard is used
                            feedback["nochange"]["cogs"].add(name) # Already loaded
                except Exception as e: feedback["errors"]["cogs"][name] = e
                else: feedback["ok"]["cogs"].add(name)
            
        # RELOAD
        elif action in _PLUGINS["reload"]:
            action = "reload"
            cogs, unknown = detect_cogs(self.bot, not_exts)
            feedback["unknown"] = feedback["unknown"].union(unknown)
            
            for name, cog in cogs.items(): # Also reload the cog's extension
                if cog.__module__ in self.bot.extensions:
                    exts.add(cog.__module__.removeprefix("Extensions."))
            
            for ext in exts: # Extensions
                try: await self.bot.reload_extension("Extensions." + ext)
                except CMDS.ExtensionNotLoaded:
                    if not globalscope: # Ignore exception if all wildcard is used
                        feedback["nochange"]["exts"].add(ext) # Not loaded
                except CMDS.ExtensionNotFound: feedback["unknown"].add(ext) # Not found
                except Exception as e: feedback["errors"]["exts"][ext] = e
                else: feedback["ok"]["exts"].add(ext)
        
        elif action in _PLUGINS["unload"]: # UNLOAD
            action = "unload" ; choice = None
            cogs, unknown = detect_cogs(self.bot, not_exts)
            feedback["unknown"] = feedback["unknown"].union(unknown)

            for ext in exts: # Extensions
                if ext == path.basename(__file__).removesuffix(".py") and ctx:
                    choice = await self.Reactech.react_confirm(ctx, "❌", "✅",
                        f"Unloading `{ext}` will disable Plugins management. Proceed anyway?")
                    if not choice: continue
                try: await self.bot.unload_extension("Extensions." + ext)
                except CMDS.ExtensionNotLoaded:
                    if not globalscope: # Ignore exception if all wildcard is used
                        feedback["nochange"]["exts"].add(ext) # Already unloaded
                except CMDS.ExtensionNotFound: feedback["unknown"].add(ext) # Not found
                except Exception as e: feedback["errors"]["exts"][ext] = e
                else: feedback["ok"]["exts"].add(ext)

            for name, cog in cogs.items(): # Cogs
                if name == "Plugins" and ctx:
                    if choice is None: choice = await self.Reactech.react_confirm(ctx, "❌", "✅",
                            f"Removing `{name}` will disable Plugins management. Proceed anyway?")
                    if not choice: continue
                try: await self.bot.remove_cog(name)
                except Exception as e: feedback["errors"]["cogs"][name] = e
                else: feedback["ok"]["cogs"].add(name)
        
        elif ctx: await self.Reactech.reactech_user(ctx, "⁉️", f"Action `{action}` is not recognized.")
        for e in feedback["errors"]["exts"].items(): print(e)
        for e in feedback["errors"]["cogs"].items(): print(e)
        return await format_feedback(feedback, action, ctx)



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
            _PLUGINS["plugins"] + ["all", ""], keeporder = True, remove = "loadplugins"))
    async def loadplugins(self, ctx: CTX, *plugins: str) -> str:
        """Loads plugins to the current bot instance."""
        return await call_plugins(self, ctx, "load", plugins)



    @CMDS.command(name = "reloadplugins", aliases = mixmatch(_PLUGINS["reload"][1:],
            _PLUGINS["plugins"] + ["all", ""], keeporder = True, remove = "reloadplugins"))
    async def reloadplugins(self, ctx: CTX, *plugins: str) -> str:
        """Reloads plugins in the current bot instance."""
        return await call_plugins(self, ctx, "reload", plugins)



    @CMDS.command(name = "unloadplugins", aliases = mixmatch(_PLUGINS["unload"][1:],
            _PLUGINS["plugins"] + ["all", ""], keeporder = True, remove = "unloadplugins"))
    async def unloadplugins(self, ctx: CTX, *plugins: str) -> str:
        """Unloads plugins from the current bot instance."""
        return await call_plugins(self, ctx, "unload", plugins)
    


    @CMDS.command(name = "listplugins", aliases = mixmatch(_PLUGINS["list"][1:],
            _PLUGINS["plugins"], keeporder = True, remove = "listplugins"))
    async def listplugins(self, ctx: CTX, *plugins: str) -> str:
        """Lists plugins in the current bot instance."""
        return await call_plugins(self, ctx, "list", plugins)
            


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
        return await call_plugins(self, ctx, "load", ["cogs"])



    @CMDS.command(name = "loadexts", aliases = mixmatch(_PLUGINS["load"][1:],
            _PLUGINS["exts"][2:], keeporder = True, remove = "loadexts"))
    async def loadexts(self, ctx: CTX) -> str:
        """Loads all exts to the current bot instance."""
        return await call_plugins(self, ctx, "load", ["exts"])



    @CMDS.command(name = "unloadcogs", aliases = mixmatch(_PLUGINS["unload"][1:],
            _PLUGINS["cogs"][1:], keeporder = True, remove = "unloadcogs"))
    async def unloadcogs(self, ctx: CTX) -> str:
        """Unloads all cogs from the current bot instance."""
        return await call_plugins(self, ctx, "unload", ["cogs"])



    @CMDS.command(name = "unloadexts", aliases = mixmatch(_PLUGINS["unload"][1:],
            _PLUGINS["exts"][2:], keeporder = True, remove = "unloadexts"))
    async def unloadexts(self, ctx: CTX) -> str:
        """Unloads all exts from the current bot instance."""
        return await call_plugins(self, ctx, "unload", ["exts"])



    @CMDS.command(name = "listcogs", aliases = mixmatch(_PLUGINS["list"][1:],
            _PLUGINS["cogs"][1:], keeporder = True, remove = "listcogs"))
    async def unloadcogs(self, ctx: CTX) -> str:
        """Lists all cogs in the current bot instance."""
        return await call_plugins(self, ctx, "list", ["cogs"])



    @CMDS.command(name = "listexts", aliases = mixmatch(_PLUGINS["list"][1:],
            _PLUGINS["exts"][2:], keeporder = True, remove = "listexts"))
    async def unloadexts(self, ctx: CTX) -> str:
        """Lists all exts in the current bot instance."""
        return await call_plugins(self, ctx, "list", ["exts"])

