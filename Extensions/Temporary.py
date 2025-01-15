"""
Temporary place to hold commands and cogs that have yet to be reworked.
"""



##################################################
# IMPORTS
##################################################



import discord as DSC
from discord.ext import commands as CMDS
from discord.ext.commands.bot import Bot
from discord.ext.commands.context import Context as CTX

from dice import roll as ROLL

from Modules.basic import least_one
from Modules.reactech import Reactech



async def setup(bot: Bot):
    await bot.add_cog(Temp(bot))



##################################################
# COG
##################################################



class Temp(CMDS.Cog):
    """Temporary cog to hold commands and cogs that have yet to be reworked."""
    def __init__(self, bot: Bot):
        self.bot = bot
        self.Reactech = Reactech(bot)



    # Evaluates expression or runs code from Discord
    # Uses exec() : Be careful of input !
    @CMDS.command(name = "echo", aliases = ['console', 'send', 'exec', 'command',' cmd', 'execute'])
    @CMDS.is_owner()
    async def echo(self, ctx: CTX, *, txt: str) -> None:
        """
        Executes a command or evaluates an expression.
        Usage is reserved for bot developpers / admins, for testing purposes.
        Report any and every case of abuse to the bot support.
        """
        print(txt)
        try: await eval(txt)
        except SyntaxError:
            try: exec(txt)
            except Exception as e: raise e
        except Exception as e: print(e)



##################################################
# ERRORS
##################################################



    @CMDS.Cog.listener()
    async def on_command_error(self, ctx: CTX, error):
        # Message to display on error, along with react emoji
        a= ("⛔","This command requires a role or permission you do not posess.\nIf you think this is a mistake, contact server admins.")
        b= ("📛","This command can only be operated by a bot admin.\nIf you think this is a mistake, contact the developer(s).")
        c= ("🚫","This command cannot be utilized in the current context.\nRefer to the error name for more precision.")
        d= ("⁉️","This command was wrongfully formatted or does not exist.\nConsult proper usage using the HELP command.")
        e= ("❓","A required Discord Object could not be resolved.\nMake sure your object names or IDs are correct before trying again.")
        f= ("‼️","The bot could not execute this command.\nMake sure to setup the application properly.")
        # Link every (most) errors with its proper message
        errors=[
            (CMDS.MissingPermissions,a),
            (CMDS.NotOwner,b),
            (CMDS.MissingRole,a),
            (CMDS.MissingAnyRole,a),
            (CMDS.DisabledCommand,c),
            (CMDS.CommandOnCooldown,c),
            (CMDS.NSFWChannelRequired,c),
            (CMDS.MissingRequiredArgument,d),
            (CMDS.TooManyArguments,d),
            (CMDS.BadArgument,d),
            (CMDS.UnexpectedQuoteError,d),
            (CMDS.CommandNotFound,d),
            (CMDS.MessageNotFound,e),
            (CMDS.MemberNotFound,e),
            (CMDS.UserNotFound,e),
            (CMDS.ThreadNotFound,e),
            (CMDS.ChannelNotFound,e),
            (CMDS.RoleNotFound,e),
            (CMDS.GuildNotFound,e),
            (CMDS.EmojiNotFound,e),
            (CMDS.GuildStickerNotFound,e),
            (CMDS.ScheduledEventNotFound,e),
            (CMDS.BotMissingPermissions,f),
            (CMDS.BotMissingRole,f),
            (CMDS.BotMissingAnyRole,f),
            (CMDS.ChannelNotReadable,f)]
        for type_, i in errors:
            if isinstance(error, type_):
                print(type_, i)
                await self.Reactech.reactech_user(ctx, i[0], i[1])
                return
        print(error) # 'print()' or 'raise' depending on your needs
