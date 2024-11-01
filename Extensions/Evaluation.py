"""
Commands and listeners likely on all bots.
Contains generic setup and managing functions.
"""



##################################################
# IMPORTS
##################################################



import discord as DSC
from discord.ext import commands as CMDS
from discord.ext.commands.bot import Bot
from discord.ext.commands.context import Context as CTX

from Modules.reactech import Reactech
from Modules.logic import main as main_math
from Modules.logic import get_args
from Modules.basic import isiterable


async def setup(bot: Bot):
    await bot.add_cog(Math(bot))



##################################################
# FUNCTIONS
##################################################



def get_comm(txt: str) -> (str, str):
    """
    Strip the expression of its comments.
    Also get the last comment (or '').
    """
    splitted = [i.strip() for i in txt.split("`")]
    expr = [splitted[i] for i in range(len(splitted)) if not i%2]
    txt = "".join([i for i in expr if i]) ; comment = ""
    if not len(splitted)%2: comment = splitted[-1]
    elif not splitted[-1]: comment = splitted[-2]
    if comment: comment = f" `{comment}`"
    return txt, comment


def ensure_size(result: any, size: int = 50) -> str:
    """Format the given argument into a proper output."""
    if isiterable(result) and len(result) == 1:
        return ensure_size(result[0])
    if isiterable(result):
        new_result = f"[{', '.join(map(str, result))}]"
    else: new_result = str(result)
    if len(new_result) > size:
        new_result = f"{new_result[:size-5]}[...]"
        if isiterable(result): new_result += "]"
    return new_result


def format_msg(msg: str) -> list:
    """Format math input to avoid disruption."""
    msg = msg.strip(", ")
    while "``" in msg: msg = msg.replace("``", "")
    while ",," in msg: msg = msg.replace(",,", ",")
    return get_args(msg, "`")


def evaluate_args(args: list) -> tuple:
    """Evaluate the given args using main_math."""
    results = [] ; comms = [] ; stack = [] ; errors = []
    for arg in args:
        expr, comm = get_comm(arg)
        if not expr: continue
        comms.append(comm)
        try: results.append(main_math(expr, stack)[0])
        except Exception as e:
            results.append(e.__class__.__name__)
            errors.append(f"'{e.__class__.__name__}': {e}")
    return results, comms, stack, errors


def format_lines(results: list, comms: list, stack: list) -> list:
    """Format output into disocrd-friendly lines."""
    results = [ensure_size(i) for i in results]
    stack = ensure_size(stack, 150) if stack else ""
    output = [results[i]+comms[i] for i in range(len(results))]
    lines = [output[0]] # Create output lines to send
    for i in output[1:]:
        predicted = len(lines[-1]) + len(i)
        if predicted <= 50: lines[-1] += ", " + i
        else: lines.append(i)
    if stack: # Final one for the stack
        predicted = len(lines[-1]) + len(stack)
        if predicted <= 50: lines[-1] += " \# " + stack
        else: lines.append("\# " + stack)
    return lines



##################################################
# MATH
##################################################



class Math(CMDS.Cog):
    """Mathematical evaluation."""
    def __init__(self, bot: Bot):
        self.bot = bot
        self.Reactech = Reactech(bot)
    

    @CMDS.command(name = "math", aliases = ["maths", "mathematic", "mathematics",
            "calc", "calculate", "calculator", "calculation", "eval", "evaluate"])
    async def math(self, ctx: CTX, *, msg: str) -> None:
        """Evaluate a given mathematical expression"""
        args = format_msg(msg)
        results, comms, stack, errors = evaluate_args(args)
        if not results: # No expression
            await self.Reactech.reactech_user(ctx, "⚠️",
            "No expression to evaluate (was it commented out?)")
            return
        lines = format_lines(results, comms, stack)
        # Send the output lines and prepare the error log
        await ctx.message.reply("\n".join(lines), mention_author=False)
        if not errors: return
        errors = [i.replace("'", "`") for i in errors]
        await self.Reactech.reactech_user(ctx, "⁉️", "\n".join(errors))
    

    @CMDS.Cog.listener()
    async def on_message(self, msg: DSC.message.Message) -> None:
        return # TODO: disabled until DICE is ready
        if msg.content.startswith(self.bot.command_prefix): return # If it's not a bot command
        if msg.author.bot: return # And not sent by a bot
        if self.bot.get_cog("Dice"): return # Priority to dice
        if msg.mentions or msg.role_mentions: return # No mentions
        if len(msg.content) > 50: return # Don't treat big messages
        results, comms, stack, errors = evaluate_args([msg.content.strip(" ,")])
        if not results or errors: return # No expression or error raised
        if msg.content.startswith(str(results[0])): return # Skip if no change
        lines = format_lines(results, comms, stack)
        await self.Reactech.reactech_channel(msg, "🧮", "\n".join(lines))






