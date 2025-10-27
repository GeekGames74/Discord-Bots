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

from asyncpg import Pool
from io import StringIO

from Modules.basic import least_one, mixmatch, removepunct
from Modules.reactech import Reactech
from Modules.data import data
from Modules.Twitch.eventsub import EventSubManager


async def setup(bot: Bot):
    await bot.add_cog(Setup(bot))
    await bot.add_cog(Core(bot))
    await bot.add_cog(Database(bot))



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


    @CMDS.Cog.listener()
    async def on_ready(self):
        print(f"{self.bot.name} is ready.")
        

    @CMDS.command(name = "kill", aliases = mixmatch(["kill", "end", "destroy", "exit", "terminate"],
            ["", "bot", "task", "script", "instance", "yourself"], keeporder = True, remove = "kill"))
    @CMDS.is_owner() # /kill-yourself is now a valid command (yipee ..?)
    async def kill(self, ctx: CTX) -> None:
        """Save and quit the bot instance."""
        # Logging and user response
        if ctx: await ctx.message.add_reaction("✅")
        print(f"{self.bot.name} is shutting down.")
        # Disconnect from voicechannels
        for vc in self.bot.voice_clients:
            vc.playing = None
            if vc.is_playing(): vc.stop()
            await vc.disconnect(force = True)
        manager = EventSubManager.get(self.bot)
        if manager is not None:
            await manager.stop()
        # Save cog: [async] def cog_unload(self):
        # Save ext: [async] def teardown(bot):
        self.bot.shutdown.set()



##################################################
# Database
##################################################



class Database(CMDS.Cog):
    """Database management commands."""
    def __init__(self, bot: Bot):
        self.bot = bot
        self.Reactech = Reactech(bot)
        self.db: Pool = bot.db


    @CMDS.command(name = "sql", aliases = ["postgres", "query", "db", "database"])
    @CMDS.is_owner()
    async def sql(self, ctx: CTX, *, query: str) -> None:
        """Execute an SQL query on the connected database."""
        if ctx.guild is not None:
            return await self.Reactech.reactech_user(ctx, "🚫", "This command can only be used in DMs.")
        query = query.strip("` ") # Remove code block formatting
        try: # Acquire a connection from the pool and start a transaction
            async with self.db.acquire() as conn:
                # Handle SELECT queries (fetch results)
                if query.lower().startswith("select"):
                    records = await conn.fetch(query)
                    if not records: # No results found
                        return await self.Reactech.reactech_valid(ctx, "Query executed successfully (no results).")
                    headers = records[0].keys()
                    rows = [list(map(str, record.values())) for record in records]
                    # Format results as a simple table
                    result = " | ".join(headers) + "\n" + "\n".join([" | ".join(row) for row in rows])
                else: # Handle non-SELECT queries (INSERT, UPDATE, DELETE, etc.)
                    result = await conn.execute(query)
        except Exception as e: # Error handling and feedback
            result = e
        # Prepare response based on success or failure
        emoji = "✅" if not isinstance(result, Exception) else "❌"
        file = None if len(str(result)) <= 1950 else DSC.File(
            StringIO(str(result)), filename="result.txt" if emoji == "✅" else "error.txt")
        # Response depends on success and length of result
        match (emoji, file is None):
            case ("✅", True):
                await ctx.reply(f"✅ Query executed successfully:\n```\n{result}\n```")
                await self.Reactech.reactech_valid(ctx, f"Query executed successfully.")
            case ("✅", False):
                await ctx.reply(f"✅ Query executed successfully.", file=file)
                await self.Reactech.reactech_valid(ctx, f"Query executed successfully. Result saved to file.")
            case ("❌", True):
                await ctx.reply(f"❌ Error executing query:\n```\n{result}\n```")
                await self.Reactech.reactech_user(ctx, emoji, f"Error executing query.")
            case ("❌", False):
                await ctx.reply(f"❌ Error executing query.", file=file)
                await self.Reactech.reactech_user(ctx, emoji, f"Error executing query. Details saved to file.")