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
from math import factorial, pi
from asyncio import gather

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
# MATH
##################################################



    @CMDS.command(name = "roll", aliases = ["dice", "d", "r", "diceroll", "rolldice"])
    async def calculate(self, ctx: CTX, *, msg: str) -> None:
        """
        Allows mathematical evaluation of a simple expression (it's a calculator !)
        Can also dice.py notations (see https://pypi.org/project/dice/).
        Can also use factorial '!(5)', pi 'p', and comparisons '<=(5,10)'.
        """
        splitted = [i for i in (msg).split("#")]
        txt = "".join([splitted[i] for i in range(len(splitted)) if not i%2])
        comment = splitted[-1] if not len(splitted)%2 else ""
        comment = " #" + comment.rstrip() if comment else ""
        result = main_math(txt.replace(" ", ""))
        if result[1] == "error":
            if result[0] == "Mix":
                await self.Reactech.reactech_user(ctx, "🚫",
                "Cannot use complex math (factorial, power, comparison) and dice at the same time!"); return
            # If the error is not a mix, then simply log it to the user
            awaiter = [self.Reactech.reactech_user(ctx, "⁉️", result[0])]
            if "d" in txt: # Include dice documentation if relevant
                awaiter += [self.Reactech.reactech_user(ctx, "🆘", "Dice notation: https://pypi.org/project/dice/")]
            gather(*awaiter) # Send error(s) as reactions
        else: await ctx.message.reply(str(result[0]) + comment, mention_author = False) # Send result



    @CMDS.Cog.listener()
    async def on_message(self, msg: DSC.message) -> None:
        if msg.content.startswith(self.bot.command_prefix): return # If it's not a bot command
        if msg.author == self.bot.user: return # And not sent by itself
        await self.msg_math(msg)
        


    async def msg_math(self, msg: DSC.message) -> None:
        splitted = [i for i in (" " + msg.content).split("#") if i]
        txt = "".join([splitted[i] for i in range(len(splitted)) if not i%2])
        comment = splitted[-1] if not len(splitted)%2 else ""
        comment = " #" + comment.rstrip() if comment else ""
        result = main_math(txt.replace(" ", ""), True)
        if result[1] != "error": # Only send if it's not an error
            emote = {"math":"🧮", "dice":"🎲"}[result[1]]
            await self.Reactech.reactech(msg, emote, True, 0, 3600, None,
                f"msg.reply('{str(result[0]) + comment}', mention_author = False)")



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



##################################################
# FUNCTIONS
##################################################



def main_math(msg: str, auto: bool = False) -> (any,str):
    """
    Automatically detect and evaluate math and rolling expression from msg.
    <auto> makes it require more checks, used to filter msg_math().
    """
    msg = msg.lower()
    # If the user literally asks for pi
    if msg == "pi" : return (pi, "math")
    # Turn pi into p (after 'pi' check, we do not accept 'p')
    msg = msg.replace("pi", "p")
    # Does the request use dice notation ?
    isdice = True if "d" in msg else False
    # Default allowed characters list
    allow = "0123456789()+-*/!.,^<=>p"
    # Extended allowed characters list
    if isdice: allow += "%dtsefxahmovl"
    # Filter the message
    txt = "".join([i for i in msg if i in allow])
    
    _ = ("", "error") # Default error return
    if auto:
        if len(msg) > 50: return _ # Max 50 characters
        # At least 3 characters (1+1), or 2 if dice (d4)
        if len(txt) < 2 or (len(txt) < 3 and not isdice): return _
        # Less than 25% of the message is allowed (not counting spaces)
        if len(txt) < 0.75*len(msg.replace(" ", "")): return _
        # At least one number (or pi)
        if not least_one(txt, "0123456789p"): return _
        # Either dice or math (don't tell the user 123 = 123)
        if not isdice and not least_one(txt, "+-*/!^<>"): return _
        # Just in case, no IDs and not newlines
        if least_one(msg, ["<#","<@","<@&", "\n"]): return _

    # Cannot use both dice and complex math (technical limitation)
    if isdice and (least_one(txt, ["**", ">=", "<="]) or least_one(txt, "!><p")):
        return ("Mix", "error")
    
    if not isdice: # Define helper functions, then replace text
        def greater_than(left, right) -> int:
            return 1 if left > right else 0
        def lesser_than(left, right) -> int:
            return 1 if left < right else 0
        def greater_eq_than(left, right) -> int:
            return 1 if left >= right else 0
        def lesser_eq_than(left, right) -> int:
            return 1 if left <= right else 0

        txt = txt.replace("^", "**")
        txt = txt.replace("!", "factorial")
        txt = txt.replace(">=", "greater_eq_than")
        txt = txt.replace("<=", "lesser_eq_than")
        txt = txt.replace(">", "greater_than")
        txt = txt.replace("<", "lesser_than")
        txt = txt.replace("p", "pi")

    try: # Calculation
        if not isdice: # Complex (or default) math
            result = eval(txt)
        else: # Dice usage
            result = ROLL(txt)
    except Exception as e:
        return (e, "error")

    type_ = "dice" if isdice else "math"
    # (3d20) returns [1d20, 1d20, 1d20]. Most commonly, users want the sum
    if isinstance(result, list): result = sum(result)
    # If literally nothing has changed anyway (and we are in auto), forget it
    if auto and str(result) == txt: return _
    return (result, type_)