"""
Temporary place to hold commands and cogs that have yet to be reworked or don't have a specific file yet.
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


async def setup(bot: Bot):
    await bot.add_cog(Scheduling(bot))
    await bot.add_cog(Temp(bot))



##################################################
# SCHEDULING
##################################################



class Scheduling(CMDS.Cog):
    """Calendar and schedule related commands."""
    def __init__(self, bot: Bot):
        self.bot = bot
        self.Reactech = Reactech(bot)

        self._SCHEDULE_DAYS = {
            "en": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
            "fr": ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"],
            "es": ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"],
            "de": ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"],
            "it": ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"],
        }
        self._SCHEDULE_WAIT_TIMEOUT = 600 # seconds
        self._SCHEDULE_EMOJIS = [
            '🇦', '🇧', '🇨', '🇩', '🇪', '🇫', '🇬',
            '🇭', '🇮', '🇯', '🇰', '🇱', '🇲', '🇳',
            '🇴', '🇵', '🇶', '🇷', '🇸', '🇹', '🇺',
            '🇻', '🇼', '🇽', '🇾', '🇿'
        ]


    def generate_schedule(self, args: list, amount: int = 1, offset: int = 0,
            include: list = None, days: list = "en", date: dt = dt.today()) -> (list, list):
        """
        Generate the schedule text with <args> as lines
        Return the message list as well as the reactions to add
        """
        # By default, include all slots in all days
        if include is None: include = [True for i in range(len(args)*(amount))]
        # Turn language code into list of days if needed
        if isinstance(days, str): days = self._SCHEDULE_DAYS[days]
        # Get the current weekday and offset it
        weekday = (date.weekday() + offset) % 7 ; emojis = []
        
        # Maximum lenght of the line headers
        max_arg_len = max([len(a) for a in args])
        # Initialize the lines with headers (with first as blank)
        # Note the 0-width character at [["<HERE> `" to avoid discord collapsing the start
        lines = [["​ `" + " " * (max_arg_len-1)]] + \
            [["`" + args[i].ljust(max_arg_len) + "`"]
            for i in range(len(args))]
        
        for i in range(amount):
            # Add the day column header to the first line
            lines[0] += [" " + days[(i+weekday) % 7][:2]]
            for j in range(len(args)):
                # If the slot is True in <include>, add the corresponding emoji
                if include[i * len(args) + j]: 
                    letter = string.ascii_lowercase[len(emojis)] # a, b, c, ...
                    lines[j+1] += [f" :regional_indicator_{letter}:"]
                    emojis += [self._SCHEDULE_EMOJIS[len(emojis)]]
                # Otherwise, an empty slot is a black square
                else: lines[j+1] += [f" :black_large_square:"]
        
        lines[0][-1] += "`" # Close the first line header
        return lines, emojis


    @CMDS.command(name = "schedule", aliases = ["sked", "sched", "skedule"])
    async def schedule(self, ctx: CTX, *args: str) -> None:
        """
        Create a schedule query to check when people are available.
        As arguments, write the lines you wish to provide (ex: Morning Afternoon Evening),
        a positive integer x for the amount of days to provide (default 99),
        and a positive interger +x for the offset of the first day (default is +0 today).
        If the first argument is a language code, this sets the language for the message
        (currently supported: 'en', 'fr', 'es', 'de', 'it').
        If the first or second argument is '!', directly send the schedule without needing to customize it.
        Remember that discord does not allow for more than 20 emojis per message
        React with ✅ to finalize the schedule.
        """
        # If the first argument is a language code
        if args and args[0].lower() in self._SCHEDULE_DAYS.keys():
            # Set the days and remove the argument
            days = self._SCHEDULE_DAYS[args[0].lower()]
            args = args[1:]
        # Otherwise, default to english
        else: days = self._SCHEDULE_DAYS["en"]
        if args and args[0] == "!":
            args = args[1:] ; direct = True
        else: direct = False

        # Ensure there is at least one argument, and remove backticks if any
        if not args: return await self.Reactech.reactech_user(ctx,
            "⁉️", "Insufficient number of arguments (minimum 1 excluding starting parameters).")
        args = [a.replace("`", "") for a in args]

        i = 0 ; amount = 99 ; offset = 0
        while i < len(args):
            # If argument corresponds to amount or offset,
            # set it and remove the argument
            if args[i].isdigit():
                amount = int(args[i])
                args = args[:i] + args[i+1:]
            elif args[i].startswith("+") and args[i][1:].isdigit():
                offset = int(args[i][1:])
                args = args[:i] + args[i+1:]
            else: i += 1

        if amount == 0: return await self.Reactech.reactech_user(ctx,
            "❌", "Could not display empty schedule.")
        # If too many slots would be displayed, reduce it so that there are at most 19 slots
        # (We need at least one free space for the checkmark)
        max_reacts = 19 if not direct else 20
        if len(args)*(amount) > max_reacts: amount = (max_reacts//len(args))
        if amount <= 0: return await self.Reactech.reactech_user(ctx,
            "❌", "Could not display schedule: too many lines")

        date = dt.today() ; ctx_message = ctx.message # Save date and message for later
        
        if not direct: # If we need to ask the user which slots to keep
            await self.Reactech.reactech_user(ctx, "ℹ️",
                "Schedule is being built", self._SCHEDULE_WAIT_TIMEOUT)

            # Generate the schedule for the first time (all slots included)
            lines, emojis = self.generate_schedule(args, amount, offset, days = days, date = date)
            text = "\n".join(["".join(i) for i in lines]) # Join the lines into a single text
            embed = DSC.Embed(description = text, color = 0x3b88c3) # Create the embed
            ask_message = await ctx.author.send(embed = embed) # Send the message to the user (in DM)
            gather(*[ask_message.add_reaction(e) for e in emojis + ["✅"]]) # Add the reactions

            def check(reaction: DSC.Reaction, user: DSC.User) -> bool: # Check function
                return (reaction.message == ask_message # Same message
                    and reaction.emoji == "✅") # Checkmark emoji
            
            try: await self.bot.wait_for("reaction_add", # Wait for the checkmark reaction
                timeout = self._SCHEDULE_WAIT_TIMEOUT, check = check)
            except TimeoutError: # On timeout, delete the ask_message, the context reaction,
                # If we cannot delete or remove reaction, ignore the error as it is not critical
                try: await ask_message.delete()
                except Exception: pass
                try: await ctx_message.remove_reaction("ℹ️", self.bot.user)
                except Exception: pass
                # Warn the user of the timout (relative to channel if relevant)
                mention = "" if ctx.guild is None else f" ({ctx.channel.mention})"
                return await self.Reactech.reactech_user(ctx, "⚠️",
                    f"Schedule command timed out{mention}")
            except CancelledError: return
            
            # On checkmark reaction, fetch the message again to get up-to-date reactions
            try: message = await ctx.author.dm_channel.fetch_message(ask_message.id)
            except Exception: return await self.Reactech.reactech_user(ctx,
                "❓", "Could not fetch the schedule message.")
            # Determine which slots to keep based on reactions with at least 2 counts (bot and user)
            reactions_to_keep = [r.count >= 2 for r in message.reactions if r.emoji in self._SCHEDULE_EMOJIS]

            # Delete the ask_message, the context reaction, non-critical errors ignored
            try: await message.delete()
            except Exception: pass
            try: await ctx_message.remove_reaction("ℹ️", self.bot.user)
            except Exception: pass

            if any(reactions_to_keep): # If at least one slot was selected
                while not any(reactions_to_keep[:len(args)]):
                    # Remove excess from the start (+offset, -amount)
                    reactions_to_keep = reactions_to_keep[len(args):]
                    offset += 1 ; amount -= 1
                while not any(reactions_to_keep[-len(args):]):
                    # Remove excess from the end (-amount)
                    reactions_to_keep = reactions_to_keep[:-len(args)]
                    amount -= 1
            # If no slot was selected, include all slots
            else: reactions_to_keep = None
        else: reactions_to_keep = None

        # Generate the final schedule with the selected slots only
        lines, emojis = self.generate_schedule(args, amount, offset, reactions_to_keep, days, date)
        # Add the date range at the top of the message
        start = date + td(days = offset) ; end = start + td(days = amount-1)
        lines.insert(0, f"<t:{int(start.timestamp())}:d> → <t:{int(end.timestamp())}:d>")
        text = "\n".join(["".join(i) for i in lines]) # Join the lines into a single text
        embed = DSC.Embed(description = text, color = 0x3b88c3) # Create the embed
        end_message = await ctx.reply(embed = embed) # Send the message as a reply
        gather(*[end_message.add_reaction(e) for e in emojis]) # Add the reactions



##################################################
# COG
##################################################



class Temp(CMDS.Cog):
    """Temporary cog to hold commands and cogs that have yet to be reworked."""
    def __init__(self, bot: Bot):
        self.bot = bot
        self.Reactech = Reactech(bot)


    @CMDS.command(name = "test")
    @CMDS.is_owner()
    async def test(self, ctx: CTX) -> None:
        pass



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
