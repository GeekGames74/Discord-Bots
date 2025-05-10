"""
Mathematical and logical evaluation for the bot.
Also includes comprehensive dice notation.
"""



##################################################
# IMPORTS
##################################################



import discord as DSC
from discord.ext import commands as CMDS
from discord.ext.commands.bot import Bot
from discord.ext.commands.context import Context as CTX

from asyncio import wait_for, to_thread, TimeoutError
from time import time

from Modules.reactech import Reactech
from Modules.logic import main as main_math
from Modules.logic import get_args, is_num, ensure_parenthesis, _ARG_TIMEOUT
from Modules.basic import isiterable, mixmatch, plural
from Modules.dice import SOURCE, scuff, translate_dice, allow_scuff


async def setup(bot: Bot):
    await bot.add_cog(Math(bot))
    await bot.add_cog(Automath(bot))
    await bot.add_cog(Roll(bot))



##################################################
# FUNCTIONS
##################################################



def ans(msg: DSC.Message, txt: str) -> str:
    """
    Add the numeric part of previous reply
    to the start of current txt.
    """
    if not txt or is_num(txt[0]): return txt
    try: content = msg.reference.resolved.content
    except: return txt
    content = content.split("#")[0].strip(" ")
    if not content: return txt
    return "(" + content + ")" + txt


def format_msg(msg: str) -> list:
    """Format math input to avoid disruption."""
    msg = msg.strip(", ").lower()
    while "``" in msg: msg = msg.replace("``", "")
    while ",," in msg: msg = msg.replace(",,", ",")
    return get_args(msg, "`")


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
    return txt.replace(" ", ""), comment


async def evaluate_args(args: list, dice: bool = False,
        is_scuff: bool = False, noresolve: bool = False) -> tuple:
    """Evaluate the given args using main_math."""
    results = [] ; comms = [] ; stack = [] ; errors = [] ; start = time()
    for arg in args:
        try:
            expr, comm = get_comm(arg)
            if not expr: continue
            comms.append(comm)
            if time() - start > _ARG_TIMEOUT: raise TimeoutError()
            result, had_dice = await wait_for(to_thread(solver,
                    expr, stack, start, dice, is_scuff, noresolve), _ARG_TIMEOUT)
        except TimeoutError as e:
            results.append("TimeoutError")
            errors.append("'TimeoutError': Evaluation has timed out " +
                f"(maximum runtime is set to {_ARG_TIMEOUT} second{plural(_ARG_TIMEOUT)})")
            if noresolve: stack.append(errors[-1])
            break
        except Exception as e:
            results.append(e.__class__.__name__)
            errors.append(f"'{e.__class__.__name__}': {e}")
            if noresolve: stack.append(errors[-1])
        else:
            try: str(result) + str(stack)
            except ValueError:
                results.append("ValueError")
                errors.append("'ValueError': Number is too large to display !")
                if noresolve: stack.append(errors[-1])
            else: results.append(result)
    try: had_dice
    except NameError: had_dice = False
    return results, comms, stack, errors, had_dice


def solver(expr: str, stack: list, start: float, dice: bool = False,
        is_scuff: bool = False, noresolve: bool = False):
    if dice:
        expr, had_dice = translate_dice(expr, is_scuff)
        if had_dice:
            source = SOURCE.copy() if dice else {}
            if is_scuff: source["scuff"] = scuff
        else: source = None
    else:
        had_dice = False ; source = None
    result = main_math(expr, stack, source, start, noresolve)[0]
    return result, had_dice


def ensure_size(result: any, size: int = 256) -> str:
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


def format_lines(results: list, comms: list, stack: list) -> list:
    """Format output into disocrd-friendly lines."""
    if not (len(results) == 1 and \
        isinstance(results[0], (int, float))):
            results = [ensure_size(i) for i in results]
    else: results = [ensure_size(results[0])]
    stack = ensure_size(stack, 256) if stack else ""
    output = [results[i]+comms[i] for i in range(len(results))]
    lines = [output[0]] # Create output lines to send
    for i in output[1:]:
        predicted = len(lines[-1]) + len(i)
        if predicted <= 100: lines[-1] += ", " + i
        else: lines.append(i)
    if stack: # Final one for the stack
        predicted = len(lines[-1]) + len(stack)
        if predicted <= 100: lines[-1] += " \# " + stack
        else: lines.append("\# " + stack)
    return lines


async def main(self: CMDS.Cog, ctx: CTX, txt: str,
        auto: bool = False, noresolve: bool = False) -> None:
    """Main function to handle math or dice input."""
    msg = ctx if isinstance(ctx, DSC.Message) else ctx.message
    if msg.reference and (not auto or \
            msg.reference.resolved.author.bot):
        txt = ans(msg, txt)
    txt = ensure_parenthesis(txt)
    args = format_msg(txt)
    dice = bool(self.bot.get_cog("Roll"))
    scuff = allow_scuff(ctx)
    results, comms, stack, errors, had_dice = \
        await evaluate_args(args, dice, scuff, noresolve)
    if noresolve:
        end = ["```"]
        while sum([len(s)+2 for s in stack]) > 1985:
            stack = stack[:-1]
            end = ["[...]\n```"]
        stack = ["```"] + stack + end
        return await ctx.message.reply("\n".join(stack), mention_author=False)
    if not results: # No expression
        if not auto: return await self.Reactech.reactech_user(ctx, "⚠️",
            "No expression to evaluate (was it commented out?)")
    # Auto filter
    if auto and (errors or txt.removeprefix("+") \
        .startswith(str(results[0]).lower())): return
    # Avoid ValueErrors because number too long
    for i in range(len(stack)):
        try: str(stack[i])
        except ValueError: stack[i] = "[...]"
    # Send the output lines and prepare the error log
    lines = format_lines(results, comms, stack)
    if not auto: await ctx.message.reply("\n".join(lines), mention_author=False)
    else:
        emoji = "🎲" if had_dice else "🧮"
        await self.Reactech.reactech_channel(ctx, emoji, "\n".join(lines))
    if not errors: return
    errors = [i.replace("'", "`") for i in errors]
    await self.Reactech.reactech_user(ctx, "⁉️", "\n".join(errors))



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
        await main(self, ctx, msg)
    

    @CMDS.command(name = "noresolve", aliases = ["expr", "expression"])
    async def noresolve(self, ctx: CTX, *, msg: str) -> None:
        """Turn the given math notation into a tree of callable elements."""
        await main(self, ctx, msg, False, True)



##################################################
# AUTOMATH
##################################################



class Automath(CMDS.Cog):
    """Automatically resolve and answer math equations without commands."""
    def __init__(self, bot: Bot):
        self.bot = bot
        self.Reactech = Reactech(bot)
    

    @CMDS.Cog.listener()
    async def on_message(self, msg: DSC.message.Message) -> None:
        if msg.content.startswith(self.bot.command_prefix): return # If it's not a bot command
        if msg.author.bot: return # And not sent by a bot
        if msg.mentions or msg.role_mentions: return # No mentions
        if len(msg.content) > 100: return # Don't treat big messages
        if len(msg.content) <= 1: return # Don't treat big messages
        await main(self, msg, msg.content, True)



##################################################
# ROLL
##################################################



class Roll(CMDS.Cog):
    """Random rolls in the classical syntax of RPGs."""
    def __init__(self, bot: Bot):
        self.bot = bot
        self.Reactech = Reactech(bot)


    @CMDS.command(name = "roll", aliases = [i for i in mixmatch(
            ["roll", "r", ""], ["dice", "d", ""], remove = "roll")
            if len(i) > 3] + ["r", "d"])
    async def roll(self, ctx: CTX, *, msg: str) -> None:
        """
        Evaluate a given mathematical expression.
        Accepts dice-rolling input in XdY form (and extended uses).
        """
        await main(self, ctx, msg)