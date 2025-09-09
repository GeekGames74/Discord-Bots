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

from Modules.basic import least_one, mixmatch, removepunct
from Modules.reactech import Reactech



async def setup(bot: Bot):
    await bot.add_cog(Setup(bot))
    await bot.add_cog(System(bot))



##################################################
# GLOBALS
##################################################



_STATUSES = {
    Status.do_not_disturb: ["dnd", "donotdisturb", "red"],
    Status.idle: ["idle", "idling", "absent", "yellow", "orange"],
    Status.online: ["online", "on", "green", "lime"],
    Status.offline: ["offline", "invisible", "off", "gray", "grey"],
}



##################################################
# SETUP
##################################################



class Setup(CMDS.Cog):
    """Basic commands and listeners for all bots."""
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
        me = self.bot.guilds[0].me
        status = None ; activity = None

        for k,v in _STATUSES.items():
            if removepunct(action + txt) in v:
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
                        "You need the `Manage nicknames` permission to use this command.")
            elif ctx.guild.me.display_name != name: # Only change if needed
                await ctx.guild.me.edit(nick = name)
                await self.Reactech.reactech_valid(ctx, f"Nick set to `{name}`")
            else: await self.Reactech.reactech_user(ctx, "ℹ️", f"Nick is already `{name}`")
        
        elif ctx and not await self.bot.is_owner(ctx.author): # Restrict further usage to owner
            await self.Reactech.reactech_user(ctx, "📛", "This command is reserved for the bot owner.")

        elif self.bot.user.name != name: # Only change if needed
                if not await self.Reactech.react_confirm(ctx, "❌", "✅",
                    "This will rename the bot globally. Are you sure?"): return
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
        print(f"{self.bot.user.name.capitalize()} is ready")
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


    @CMDS.command(name = "ping", aliases = ["!", "latency"])
    async def ping(self, ctx: CTX) -> int:
        """Returns the current latency (in ms)."""
        latency = int(self.bot.latency*1000)
        if ctx: await ctx.send("pong! " + str(latency) + "ms")
        return latency

    
    @CMDS.command(name = "url", aliases = mixmatch(["join", "invite", ""],
            ["url", "link"], remove="url"))
    async def url(self, ctx: CTX) -> str:
        """Get the invite url for the bot."""
        url = f"https://discord.com/oauth2/authorize?client_id={self.bot.user.id}&permissions=0&scope=bot%20applications.commands"
        if ctx: await ctx.send(f"[Add this bot to your server]({url})")
        return url


    @CMDS.command(name = "kill", aliases = mixmatch(["kill", "end", "destroy", "exit", "terminate"],
            ["", "bot", "task", "script", "instance", "yourself"], keeporder = True, remove = "kill"))
    @CMDS.is_owner() # /kill-yourself is now a valid command (yipee ..?)
    async def kill(self, ctx: CTX) -> None:
        """Save and quit the bot instance."""
        # Logging and user response
        if ctx: await ctx.message.add_reaction("✅")
        print(f"{self.bot.user.name.capitalize()} is shutting down")
        # Disconnect from voicechannels
        for vc in self.bot.voice_clients:
            vc.playing = None
            if vc.is_playing(): vc.stop()
            await vc.disconnect(force = True)
        # Save cog: [async] def cog_unload(self):
        # Save ext: [async] def teardown(bot):
        self.bot.shutdown.set()
