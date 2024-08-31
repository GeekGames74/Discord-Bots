"""
Commands and listeners likely on all bots.
Contains generic setup and managing functions.
"""



##################################################
# IMPORTS
##################################################


import discord as DSC
from discord import Status, Activity
from discord.ext import commands as CMDS
from discord.ext.commands.bot import Bot
from discord.ext.commands.context import Context as CTX

from copy import copy

from Modules.basic import least_one, mixmatch, remove_punct, plural
from Modules.reactech import Reactech



async def setup(bot: Bot):
    await bot.add_cog(Setup(bot))
    await bot.add_cog(System(bot))
    await bot.add_cog(Plugins(bot))



##################################################
# GLOBALS
##################################################



_STATUSES = {
    Status.do_not_disturb: ["dnd", "donotdisturb", "red"],
    Status.idle: ["idle", "idling", "absent", "yellow", "orange"],
    Status.online: ["online", "on", "green", "lime"],
    Status.offline: ["offline", "invisible", "off", "gray", "grey"],
}

_PLUGINS_KW = {
    "cogs": ["c", "cog", "cogs"], "exts": ["e", "x", "xt", "ext", "exts", "extension", "extensions"],
    "list": ["l", "list", "show", "display"]
}
_PLUGINS_ACTS = [
    ("loaded", ("add_cog", "load_extension"), ["load", "a", "add", "append"]),
    ("reloaded", (None, "reload_extension"), ["reload", "r", "reset", "restart"]),
    ("unloaded", ("remove_cog", "unload_extension"), ["remove", "u", "unload"])
]



##################################################
# SETUP
##################################################



class Setup(CMDS.Cog):
    """Basic commands and listeners for all bots"""
    def __init__(self, bot: Bot):
        self.bot = bot
        self.Reactech = Reactech(bot)

    
    @CMDS.command(name = "activity", aliases = ["status"])
    @CMDS.is_owner()
    async def activity(self, ctx: CTX, action: str = "", *, txt: str = "") -> Activity:
        """
        Changes current bot activity or status message.
        Activity and Status are designated with generic keywords.
        """
        action = action.lower()
        me = ctx.me if ctx else self.bot.guilds[0].me
        status = None ; activity = None

        for k,v in _STATUSES.items():
            if remove_punct(action + txt) in v:
                status = k ; break

        if status: # Only if status is recognized (otherwise set activity)
            if status.value != me.status.value:
                await self.bot.change_presence(status = status, activity = me.activity)
                if ctx: await self.Reactech.reactech_valid(ctx, f"Status changed to `{status.name}`")
            elif ctx: # Do not change if not needed
                await self.Reactech.reactech_user(ctx, "ℹ️", f"Status is already `{status.name}`")
            return # End function early

        url = "twitch.tv/" # Default url
        # Does not work with www.
        if 'twitch.tv/' in action:
            url = action.replace("www.", "")
        # Does not work without https://
        if not url.startswith("https://"): 
            url = "https://" + url

        if least_one(action, ['gam', 'play']):
            activity = DSC.Game(name = txt)
        if least_one(action, ['stream', 'twitch']):
            activity = DSC.Streaming(name = txt, url = url)
        if least_one(action, ['listen']):
            activity = Activity(type = DSC.ActivityType.listening, name = txt)
        if least_one(action, ['watch', 'video']):
            activity = Activity(type = DSC.ActivityType.watching, name = txt)
        if least_one(action, ['def', 'serv', 'bas', 'main']):
            activity = "Default"
        
        if activity is None: # Void
            activity = "Set activity to None"
            await self.bot.change_presence(activity = None, status = me.status)
        else: # Anything but the void
            if txt is None or activity == "Default":
                txt = str(len(self.bot.guilds)) + " servers" # Default message
                activity = Activity(type = DSC.ActivityType.watching, name = txt)
            await self.bot.change_presence(activity = activity, status = me.status)
        if ctx: await self.Reactech.reactech_valid(ctx, activity) # Feedback
        return activity
    


    @CMDS.command(name = "rename", aliases = mixmatch(
            ["change", "edit", "modify", "set", "reset"],
            ["name", "username"], keeporder = True))
    async def rename(self, ctx: CTX, *, name: str) -> None:
        """
        Change the client nickname on the server.
        If executed outside a guild, permanently sets the username (bot owner only).
        """
        if ctx and ctx.guild: # First use (change nick)
            if not ctx.author.guild_permissions.manage_nicknames:
                await self.Reactech.reactech_user(ctx, "⛔",
                        "You need the [Manage nicknames] permission to use this command.")
            elif ctx.guild.me.display_name != name: # Only change if needed
                await ctx.guild.me.edit(nick = name)
                await self.Reactech.reactech_valid(ctx, f"Nick set to `{name}`")
            else: await self.Reactech.reactech_user(ctx, "ℹ️", f"Nick is already `{name}`")
        
        elif ctx and not await self.bot.is_owner(ctx.author): # Restrict further usage to owner
            await self.Reactech.reactech_user(ctx, "🚫", "This command is reserved for the bot owner.")

        elif self.bot.user.name != name: # Only change if needed
                try: # Test for Discord ratelimit
                    await self.bot.user.edit(username = name)
                    if ctx: await self.Reactech.reactech_valid(ctx, f"Name set to `{name}`")
                except DSC.errors.HTTPException as e: # If ratelimited
                    if e.status == 400 and e.code == 50035 and ctx:
                        await self.Reactech.reactech_user(
                            ctx, "🚫", "Could not set name; Too many name changes.")
        elif ctx: await self.Reactech.reactech_user(ctx, "ℹ️", f"Name is already `{name}`")



    @CMDS.Cog.listener()
    async def on_ready(self):
        await self.activity(None, "Online")
        await self.activity(None, "Default")



##################################################
# SYSTEM
##################################################



class System(CMDS.Cog):
    """System commands, used to manage bot instances."""
    def __init__(self, bot: Bot):
        self.bot = bot
        self.Reactech = Reactech(bot)



    @CMDS.command(name = "ping", aliases = ["test", "!", "latency"])
    async def ping(self, ctx: CTX) -> None:
        """Returns the current latency (in ms)."""
        await ctx.send("pong! " + str(int(self.bot.latency*1000)) + "ms")
    


    @CMDS.command(name = "kill", aliases = mixmatch(["kill", "end", "destroy", "exit", "stop", "terminate"],
            ["", "bot", "task", "script", "instance", "yourself"], keeporder = True, remove = "kill"))
    @CMDS.is_owner() # /kill-yourself is now a valid command (yipee ..?)
    async def kill(self, ctx: CTX) -> None:
        """Save and quit the bot instance."""
        cogs = list(self.bot.cogs.keys())
        exts = list(self.bot.extensions.keys())
        for cog in cogs: # Save cog-related data using   def __unload(self):
            await self.bot.remove_cog(cog)
        for ext in exts: # Save ext-related data using   [async] def teardown(bot):
            await self.bot.unload_extension(ext)
        await ctx.message.add_reaction("✅")
        await self.bot.close()



##################################################
# PLUGINS
##################################################



class Plugins(CMDS.Cog):
    """Manage (load, unload and reload) plugins (cogs and exts)."""
    def __init__(self, bot: Bot):
        self.bot = bot
        self.Reactech = Reactech(bot)
    

    @CMDS.command(name = "plugins", aliases = mixmatch(["manage", ""],
            ["plugin", "plugins"], keeporder = True, remove = "plugins"))
    @CMDS.is_owner()
    async def plugins(self, ctx: CTX, action: str = None, *plugins: tuple) -> str:
        """Manage plugins in relation to the current bot instance."""
        ok = [] ; already = [] ; notfound = [] ; errors = [] ; txt = ""
        cogs = set() ; exts = set() ; all_cogs = False ; all_exts = False
        both = set(plugins)
        if action: both.add(action)

        if not both or "*" in both or \
                least_one(both, _PLUGINS_KW["cogs"]): # all cogs
            cogs = set(self.bot.cogs.keys())
            all_cogs = True
        else: cogs = set([i for i in self.bot.cogs.keys() if i in both])

        if not both or "*" in both or \
                least_one(both, _PLUGINS_KW["exts"]): # all exts
            exts = set(self.bot.extensions.keys())
            all_exts = True
        else: exts = set([i for i in self.bot.extensions.keys() if i in both])
        _exts = [i.removeprefix("Extensions.") for i in exts]

        if not action or any([i for i in _PLUGINS_KW.values() if action in i]):
            if all_cogs or not all_exts:
                if len(cogs) == 0: txt += "0 cogs currently loaded.\n" # On 0
                else: txt += f"{len(cogs)} cog{plural(cogs)} currently loaded: `" + "`, `".join(cogs) +"`\n"
            if all_exts or not all_cogs:
                if len(_exts) == 0: txt += f"0 extensions currently loaded.\n" # On 0
                else: txt += f"{len(_exts)} extension{plural(_exts)} currently loaded: `" + "`, `".join(_exts) +"`\n"
            txt.removesuffix("\n")
            if ctx:
                msg = await ctx.send(txt)
                if not action or not exts: return txt
                # TODO: Find a way to check if reaction-er is allowed to reload
                #await self.Reactech.reactech(msg, "🔃", True, 0, 300, None,
                        #"self.bot.get_cog('Plugins').plugins(msg, 'reload', *args[0])", _exts)
            return txt