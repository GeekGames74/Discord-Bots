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
from asyncio import TimeoutError, CancelledError

from asyncio import gather
from datetime import datetime as dt
from datetime import timedelta as td
from traceback import TracebackException
import string

from Modules.reactech import Reactech
from Modules.data import data


async def setup(bot: Bot):
    await bot.add_cog(Temp(bot))



##################################################
# COG
##################################################


_SCHEDULE_DAYS = {
    "en": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
    "fr": ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"],
}

_SCHEDULE_WAIT_TIMEOUT = 600 # seconds
_SCHEDULE_EMOJIS = [
    '🇦', '🇧', '🇨', '🇩', '🇪', '🇫', '🇬',
    '🇭', '🇮', '🇯', '🇰', '🇱', '🇲', '🇳',
    '🇴', '🇵', '🇶', '🇷', '🇸', '🇹', '🇺',
    '🇻', '🇼', '🇽', '🇾', '🇿'
]


def generate_schedule(args: list, amount: int = 1, offset: int = 0,
        include: list = None, days: list = "en") -> (list, list):
    """
    Generate the schedule text with <args> as lines and <n> columns/days (0 is now)
    Return the message list as well as the reactions to add
    """
    if include is None: include = [True for i in range(len(args)*(amount))]
    if isinstance(days, str): days = _SCHEDULE_DAYS[days]
    weekday = (dt.today().weekday() + offset) % 7 ; emojis = []
    
    max_arg_len = max([len(a) for a in args])
    lines = [[" `" + " "*max_arg_len] if i==0 else
            ["`" + args[i-1].ljust(max_arg_len) + "`"]
            for i in range(len(args)+1)]
    
    for i in range(amount):
        lines[0] += [" " +days[(i+weekday)%7][:2]]
        if (i+weekday)%7 == 6: lines[0][-1] += " "
        for j in range(len(args)):
            if include[i*len(args)+j]: 
                letter = string.ascii_lowercase[len(emojis)]
                lines[j+1] += [f" :regional_indicator_{letter}:"]
                emojis += [_SCHEDULE_EMOJIS[len(emojis)]]
            else: lines[j+1] += [f" :black_large_square:"]
    
    lines[0][-1] += "`"
    return lines, emojis



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
        except Exception as e: raise(e)


    @CMDS.command(name = "cornelius")
    @CMDS.is_owner()
    async def cornelius(self, ctx: CTX, amount: int, *, txt = "") -> None:
        msg = ""
        if amount >= 10: msg += f"- {amount//10*5} PV temporaires\n"
        if amount >= 20: msg += f"- {amount//20} prochaines offenses avec avantage\n"
        if amount >= 30: msg += f"- {amount//30} prochaines défenses avec avantage\n"
        if amount >= 40: msg += f"- multiattaque +{amount//40} ou sort lvl{amount//40*2} sans consommer d'incantation\n"
        if amount >= 50: msg += f"- Vitesses multipliées par {(amount//50)+1}\n"
        if amount >= 60: msg += f"- Dégâts multipliés par {(amount//60)+1}\n"
        if amount >= 70: msg += f"- Résistance aux dégâts\n"
        if amount%10: msg += f"{amount%10} points conservés pour le tour suivant\n"
        if msg: msg = "Jusqu'à la fin de votre prochain tour:\n" + msg + txt
        msg = msg.removesuffix("\n")
        if msg: await ctx.reply(msg, mention_author=False)


    @CMDS.command(name = "schedule", aliases = ["sked", "sched", "skedule"])
    async def schedule(self, ctx: CTX, *args: str) -> None:
        """
        Create a schedule query to check when people are available.
        As arguments, write the lines you wish to provide (ex: Morning Afternoon Evening),
        a positive integer x for the amount of days to provide (default 99),
        and a positive interger +x for the offset of the first day (default is +0 today).
        If the first argument is a language code, this sets the language for the message
        (currently supported: 'en', 'fr')
        Remember that discord does not allow for more than 20 emojis per message
        React with ✅ to finalize the schedule.
        """
        if args and args[0].lower() in _SCHEDULE_DAYS.keys():
            days = _SCHEDULE_DAYS[args[0].lower()]
            args = args[1:]
        else: days = _SCHEDULE_DAYS["en"]

        if not args: return await self.Reactech.reactech_user(ctx,
            "⁉️", "Insufficient number of arguments (minimum 1 excluding language)")
        args = [a.replace("`", "") for a in args]

        i = 0 ; amount = 99 ; offset = 0
        while i < len(args):
            if args[i].isdigit():
                amount = int(args[i])
                args = args[:i] + args[i+1:]
            elif args[i].startswith("+") and args[i][1:].isdigit():
                offset = int(args[i][1:])
                args = args[:i] + args[i+1:]
            else: i += 1

        if amount == 0: return await self.Reactech.reactech_user(ctx,
            "❌", "Could not display empty schedule.")
        if len(args)*(amount) > 19: amount = (19//len(args))
        if amount <= 0: return await self.Reactech.reactech_user(ctx,
            "❌", "Could not display schedule: too many lines")

        gather(self.Reactech.reactech(ctx, "ℹ️", timeout = _SCHEDULE_WAIT_TIMEOUT,
            method = "user.send('Schedule is being built')"))
        lines, emojis = generate_schedule(args, amount, offset, days = days)
        msg = await ctx.author.send("\n".join(["".join(i) for i in lines]))
        for e in emojis + ["✅"]: await msg.add_reaction(e)

        def check(reaction: DSC.Reaction, user: DSC.User) -> bool:
            return (reaction.message == msg and \
                    reaction.emoji == "✅"
                    and user == ctx.author)
        try: await self.bot.wait_for("reaction_add", timeout = _SCHEDULE_WAIT_TIMEOUT, check=check)
        except TimeoutError:
            await msg.delete()
            await ctx.message.remove_reaction("ℹ️", self.bot.user)
            mention = "" if ctx.guild is None else f" ({ctx.channel.mention})"
            return await self.Reactech.reactech_user(ctx, "⚠️",
                f"Schedule command timed out{mention}")
        except CancelledError: return
        except Exception as e: raise e
        
        message = await ctx.author.dm_channel.get_partial_message(msg.id).fetch()
        reactions_to_keep = [
            len([u async for u in r.users()]) >= 2
            for r in message.reactions if r.emoji in _SCHEDULE_EMOJIS
        ]

        await message.delete()
        await ctx.message.remove_reaction("ℹ️", self.bot.user)
        
        if any(reactions_to_keep):
            while not any(reactions_to_keep[:len(args)]):
                reactions_to_keep = reactions_to_keep[len(args):]
                offset += 1 ; amount -= 1
            while not any(reactions_to_keep[-len(args):]):
                reactions_to_keep = reactions_to_keep[:-len(args)]
                amount -= 1
        else: reactions_to_keep = None

        lines, emojis = generate_schedule(args, amount, offset, reactions_to_keep, days)
        start = dt.today() + td(days = offset)
        end = start + td(days = amount-1)
        lines.insert(0, f"<t:{int(start.timestamp())}:d> → <t:{int(end.timestamp())}:d>")
        msg = await ctx.reply("\n".join(["".join(i) for i in lines]))
        for e in emojis: await msg.add_reaction(e)



##################################################
# ERRORS
##################################################



    @CMDS.Cog.listener()
    async def on_command_error(self, ctx: CTX, error: Exception):
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
        print('\n'+'#'*50+'\n')
        print(''.join(TracebackException.from_exception(error).format()))
        print('\n'+'#'*50+'\n')
