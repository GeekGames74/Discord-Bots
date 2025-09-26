"""
Commands to implement on all bot instances,
providing basic utility functions for bot admins.
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
from Modules.data import data



async def setup(bot: Bot):
    await bot.add_cog(Setup(bot))
    await bot.add_cog(Core(bot))



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
    """Simple commands to administer the bot instance."""
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
        elif least_one(action, ['stream', 'twitch']):
            activity = DSC.Streaming(name = txt, url = url)
        elif least_one(action, ['listen']):
            activity = Activity(type = DSC.ActivityType.listening, name = txt)
        elif least_one(action, ['watch', 'video']):
            activity = Activity(type = DSC.ActivityType.watching, name = txt)
        elif least_one(action, ['def', 'serv', 'bas', 'main']):
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
    

    @CMDS.Cog.listener()
    async def on_ready(self):
        print(f"{self.bot.user.name.capitalize()} is ready")
        await self.activity(None, "Online")
        await self.activity(None, "Default")
    

    @CMDS.Cog.listener()
    async def on_guild_leave(self, guild: DSC.Guild):
        """Remove server data when the bot leaves a guild."""
        servers = data("Data/servers.json", read_only=True)
        if str(guild.id) in servers:
            del servers[str(guild.id)]
            data("Data/servers.json", servers, read_only=False)



##################################################
# Core
##################################################



class Core(CMDS.Cog):
    """Core commands, used to manage bot instances."""
    def __init__(self, bot: Bot):
        self.bot = bot
        self.Reactech = Reactech(bot)


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
