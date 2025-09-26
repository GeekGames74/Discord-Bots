"""
Generic commands for basic functionnality.
"""



##################################################
# IMPORTS
##################################################



import discord as DSC
from discord.ext import commands as CMDS
from discord.ext.commands.bot import Bot
from discord.ext.commands.context import Context as CTX

from Modules.basic import mixmatch
from Modules.reactech import Reactech
from Modules.data import data



async def setup(bot: Bot):
    await bot.add_cog(Info(bot))
    await bot.add_cog(Custom(bot))



##################################################
# GLOBALS
##################################################



def get_prefix(bot_ctx: Bot|CTX, message: DSC.Message = None) -> str:
    """Return the bot prefix for the given message."""
    # Optionally extract the bot from the context
    bot = bot_ctx if isinstance(bot_ctx, Bot) else bot_ctx.bot
    # If bot_ctx is a Bot, guild must be given by message
    if isinstance(bot_ctx, Bot):
        guild = message.guild if message else None
    else: guild = bot_ctx.guild # Guild is given by context
    if not guild: return [bot.prefix, bot.user.mention] # DMs
    # If in guild, retreive the custom prefix by guild id
    prefix = data("Data/servers.json", bot.prefix, str(guild.id),
        "bots", str(bot.user.id), "prefix", keynotfound=None)
    # Just in case, accept a bot ping to invoke commands
    return [prefix, bot.user.mention]




##################################################
# Info
##################################################



class Info(CMDS.Cog):
    """Interface for all users to gain information about the bot."""
    def __init__(self, bot: Bot):
        self.bot = bot
        self.Reactech = Reactech(bot)
    

    @CMDS.command(name = "ping", aliases = ["!", "latency"])
    async def ping(self, ctx: CTX) -> int:
        """Returns the current latency (in ms)."""
        latency = int(self.bot.latency*1000)
        # Only send a message if invoked in a context
        if ctx: await ctx.send("pong! " + str(latency) + "ms")
        return latency

    
    @CMDS.command(name = "url", aliases = mixmatch(["join", "invite", ""],
            ["url", "link"], remove="url"))
    async def url(self, ctx: CTX) -> str:
        """Get the invite url for the bot."""
        url = f"https://discord.com/oauth2/authorize?client_id={self.bot.user.id}&permissions=0&scope=bot%20applications.commands"
        # Only send a message if invoked in a context
        if ctx: await ctx.send(f"[Add this bot to your server]({url})")
        return url



##################################################
# CUSTOM
##################################################



class Custom(CMDS.Cog):
    """Features to allow users and server owners to customize the bot."""
    def __init__(self, bot: Bot):
        self.bot = bot
        self.Reactech = Reactech(bot)


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
                else: raise e # Re-raise unknown exceptions
        elif ctx: await self.Reactech.reactech_user(ctx, "ℹ️", f"Name is already `{name}`")


    @CMDS.command(name = "prefix", aliases = mixmatch(
            ["set", "change", "edit"],
            ["prefix"], keeporder = True))
    async def prefix(self, ctx: CTX, *, prefix: str = "") -> None:
        """Change the bot prefix for the server."""
        if not ctx.guild: return await self.Reactech.reactech_user(
            ctx, "🚫", "This command can only be used in a server.")
        if not ctx.author.guild_permissions.administrator:
            return await self.Reactech.reactech_user(ctx, "⛔",
                "You must have `administrator` permissions to use this command.")
        
        prefix = prefix.strip() # Validate the prefix
        if not prefix: return await self.Reactech.reactech_user(
            ctx, "❌", "Prefix cannot be empty.")
        if not (1 <= len(prefix) <= 3): return await self.Reactech.reactech_user(
            ctx, "❌", "Prefix must be between 1 and 3 characters.")

        # Save the new prefix under guild/bots/"prefix"
        data("Data/servers.json", prefix, str(ctx.guild.id),
            "bots", str(self.bot.user.id), "prefix", read_only=False)
        # If prefix contains backticks, escape them and use different enclosing
        sep = "" if "`" in prefix else '`'
        if "`" in prefix: prefix = prefix.replace("`", "\`")
        await self.Reactech.reactech_valid(ctx, f"Bot prefix set to {sep}{prefix}{sep}")
