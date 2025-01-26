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

from random import choices, randint
from asyncio import wait_for, to_thread, TimeoutError

from Modules.reactech import Reactech
from Modules.logic import main as main_math
from Modules.logic import get_args, is_num
from Modules.logic import _AFTER_STR, resolve
from Modules.logic import _REPLACE, replace_simple, ensure_parenthesis
from Modules.logic import analyse, check_for_func
from Modules.basic import isiterable, mixmatch, plural


async def setup(bot: Bot):
    await bot.add_cog(Math(bot))
    await bot.add_cog(Roll(bot))



##################################################
# GLOBALS
##################################################
    


_ARG_TIMEOUT = 3

_DICE_ARGS = set("@!^vl#xpn~")
_DICE_ADDONS = [
    ["kh", "^"],
    ["kl", "v"],
    ["rr", "reroll"],
    ["r"],
    ["p", "pn", "pnt", "pen", "penet", "penetrate"],
    ["x", "ex", "exp"],
    ["n", "nuke", "nuclear"]
]
_DICE_LIST = [4, 6, 8, 10, 12, 20, 100]


def anyroll(s: tuple, expr: str, x: str = None,
            r: str = None, rr: str = None) -> int:
    """Roll expr, explode x, reroll y once, reroll all z."""
    x = resolve(x, *s) or set()
    r = resolve(r, *s) or set()
    rr = resolve(rr, *s) or set()
    rolled = None ; mx = None
    while rolled is None or rolled in rr:
        result = resolve(expr, *s)
        if isinstance(result, tuple):
            rolled, mx = int(result[0]), result[1]
        else: rolled = int(result[0])
        if r and isiterable(r) and rolled in r:
            return anyroll(s, expr, x, None, rr)
    if x and ((isinstance(x, bool) and mx and rolled == mx)
            or (isiterable(x) and rolled in x)):
        rolled += anyroll(s, expr, x, r, rr)
    return rolled


def roll(s: tuple, x: str) -> (int, int):
    """Roll an x sided dice."""
    sides = int(resolve(x, *s)) ; m = 1
    if sides == 0: return 0, None
    (sides, m) = (sides, 1) if sides > 0 else (-sides, -1)
    if sides == 1: return randint(0, 1) * m, sides
    return randint(1, sides) * m, sides


def penetrating(s: tuple, x: str, p: str = None, first: bool = True) -> (int,int):
    """Roll x, reroll lower x if result is max."""
    sides = int(resolve(x, *s))
    if isinstance(p, str): p = resolve(p, *s)
    if isinstance(p, bool): p = {sides}
    if sides not in _DICE_LIST: raise ValueError(
        "Penetrating dice must have sides in " +
        f"[{', '.join(_DICE_LIST)}]")
    rolled = roll(s, sides)[0]
    index = _DICE_LIST.index(sides)
    if rolled in p and index != 0:
        rolled += penetrating(s, _DICE_LIST[index - 1], p, False)[0]
    return rolled, sum(_DICE_LIST[:index+1]) \
        if first else rolled, None


def nuclear(s: tuple, x: str, n: str = None, first: bool = True) -> (int,int):
    """Roll x, reroll higher x if result is max."""
    sides = int(resolve(x, *s))
    if isinstance(n, str): n = resolve(n, *s)
    if isinstance(n, bool): n = {sides}
    if sides not in _DICE_LIST: raise ValueError(
        "Nuclear dice must have sides in " +
        f"[{', '.join([str(i) for i in _DICE_LIST])}]")
    rolled = roll(s, sides)[0]
    index = _DICE_LIST.index(sides)
    if rolled in n and index != len(_DICE_LIST)-1:
        rolled += penetrating(s, _DICE_LIST[index + 1], n, False)[0]
    return rolled, sum(_DICE_LIST[index:]) \
        if first else rolled, None


_SOURCE = {
    "anyroll": anyroll,
    "roll": roll,
    "penetrating": penetrating,
    "nuclear": nuclear
}


##################################################
# SCUFF
##################################################



_JESUS = 536998412223250462

_ALLOW = {_JESUS}.union({
    427031555383492609, # Geek
    #774649444842209300, # Ghost
})

def allow_scuff(ctx: CTX) -> bool:
    """Check if user is allowed to SCUFF™."""
    if ctx.author.id in _ALLOW: return True
    if ctx.guild is not None and \
        ctx.guild.get_member(_JESUS):
        return True
    return False


_SCUFF = {1: 24, 2: 81, 3: 21, 4: 12, 5: 27,
          6: 24, 7: 2, 8: 40, 9: 29, 10: 18,
          11: 10, 12: 41, 13: 17, 14: 6, 15: 28,
          16: 16, 17: 22, 18: 18, 19: 101, 20: 34}

def scuff(s: tuple) -> (int, int):
    """Return a d20 output using the SCUFF™ dice"""
    return choices(list(_SCUFF.keys()),
        weights=list(_SCUFF.values()), k=1)[0], 20



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
    results = [] ; comms = [] ; stack = [] ; errors = []
    for arg in args:
        expr, comm = get_comm(arg)
        if not expr: continue
        comms.append(comm)
        try: result, had_dice = await wait_for(to_thread(solver,
                expr, stack, dice, is_scuff, noresolve), _ARG_TIMEOUT)
        except TimeoutError as e:
            results.append("TimeoutError")
            errors.append("'TimeoutError': Evaluation has timed out. " +
                f"(maximum runtime is set to {_ARG_TIMEOUT} second{plural(_ARG_TIMEOUT)})")
        except Exception as e:
            results.append(e.__class__.__name__)
            errors.append(f"'{e.__class__.__name__}': {e}")
        else: results.append(result)
    try: had_dice
    except NameError: had_dice = False
    return results, comms, stack, errors, had_dice


def solver(expr: str, stack: list, dice: bool = False,
        is_scuff: bool = False, noresolve: bool = False):
    source = _SOURCE.copy() if dice else {}
    if dice and is_scuff: source["scuff"] = scuff
    if dice: expr, had_dice = translate_dice(expr, is_scuff)
    result = main_math(expr, stack, source, noresolve)[0]
    return result, had_dice


def ensure_size(result: any, size: int = 100) -> str:
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
    if not results: # No expression
        if not auto: await self.Reactech.reactech_user(ctx, "⚠️",
            "No expression to evaluate (was it commented out?)")
        return
    # Auto filter 
    if auto and errors or txt.removeprefix("+") \
        .startswith(str(results[0])): return
    # Send the output lines and prepare the error log
    lines = format_lines(results, comms, stack)
    emoji = "🎲" if had_dice else "🧮"
    if not auto: await ctx.message.reply("\n".join(lines), mention_author=False)
    else: await self.Reactech.reactech_channel(ctx, emoji, "\n".join(lines))
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
        

    @CMDS.Cog.listener()
    async def on_message(self, msg: DSC.message.Message) -> None:
        if msg.content.startswith(self.bot.command_prefix): return # If it's not a bot command
        if msg.author.bot: return # And not sent by a bot
        if msg.mentions or msg.role_mentions: return # No mentions
        if len(msg.content) > 50: return # Don't treat big messages
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



##################################################
# DICE ANALYSIS
##################################################



def translate_dice(arg: str, scuff: bool = False) -> (str,bool):
    """Translate dice-rolling input into a mathematical expression"""
    if isiterable(arg): return [translate_dice(i) for i in arg]
    arg = replace_simple(arg, _REPLACE)
    has_dice = False ; i = 0
    while i < len(arg):
        dice = analyse_dice(arg, i, scuff)
        if dice:
            arg = dice.replace(arg)
            i = 0 ; has_dice = True
        i += 1
    return arg, has_dice


class Dice:
    """Dice analysis to hold information on a roll."""
    def __init__(self, start: int, end: int):
        if start > end: raise ValueError("Start index must be less than end index")
        self.start = start ; self.end = end
        self.init_params()
    

    def init_params(self):
        """Initialise extra parameters for the dice roll."""
        self.amount = None     ; self.sides = None
        self.advantage = 0     ; self.disadvantage = 0
        self.list = False      ; self.verbose_level = 0
        self.exploding = False ; self.penetrating = False
        self.nuclear = False   ; 
        self.keep_high = None  ; self.keep_low = None
        self.r = set()         ; self.rr = set()
        self.average_level = 0 # TODO: not implemented
    

    def set_param(self, param):
        """Set a diceroll parameter among [ @!l#xp^v?~ ]."""
        if isiterable(param) or \
            (isinstance(param, str) and len(param) > 1):
                for i in param: self.set_param(i)
                return
        match param:
            case "@": self.advantage += 1
            case "!": self.disadvantage += 1
            case "l": self.list = True
            case "#": self.verbose_level += 1
            case "x": self.exploding = True
            case "p": self.penetrating = True
            case "n": self.nuclear = True
            case "^":
                self.keep_high = self.keep_high or 0
                self.keep_high += 1
            case "v":
                self.keep_low = self.keep_low or 0
                self.keep_low += 1
            case "?": self.sides = "?"
            case "~": self.average_level += 1
            case _: raise ValueError(f"'{param}' not a dice parameter.")

    def set_addon(self, addon, value: None):
        """Set an addon parameter among _DICE_ADDONS."""
        if addon in _DICE_ADDONS[0]: # kh
            if not value: self.keep_high = 1
            else: self.keep_high = value.content
        if addon in _DICE_ADDONS[1]: # kl
            if not value: self.keep_low = 1
            else: self.keep_low = value.content
        if addon in _DICE_ADDONS[2]: # rr
            if not value: raise SyntaxError(
                f"'{addon}' must include a value")
            self.rr.add(value.content)
        if addon in _DICE_ADDONS[3]: # r
            if not value: raise SyntaxError(
                f"'{addon}' must include a value")
            self.r.add(value.content)
        if addon in _DICE_ADDONS[4]: # p
            if not value: self.penetrating = True
            else:
                if (not isinstance(self.penetrating, set)):
                    self.penetrating = set()
                self.penetrating.add(value.content)
        if addon in _DICE_ADDONS[5]: # x
            if not value: self.exploding = True
            else:
                if (not isinstance(self.exploding, set)):
                    self.exploding = set()
                self.exploding.add(value.content)
        if addon in _DICE_ADDONS[6]: # n
            if not value: self.nuclear = True
            else:
                if (not isinstance(self.nuclear, set)):
                    self.nuclear = set()
                self.nuclear.add(value.content)
        


    def final_param(self) -> bool:
        """Finalise dice when all parameters are set."""
        self.adv = self.advantage - self.disadvantage
        if self.adv:
            self.sides = self.sides or 20
            self.amount = self.amount or abs(self.adv)+1
            if self.adv > 0 and self.keep_high is None:
                self.keep_high = 1
            elif self.keep_low is None: self.keep_low = 1
        elif self.amount is None: self.amount = 1
        if self.sides is None: return False
        return True


    def translate(self) -> str:
        """Translate the parameters into a string."""
        if self.sides == "?": output = "scuff()"
        elif self.penetrating:
            p = surround(self.penetrating, ",flatten") \
                if not isinstance(self.penetrating, bool) else ",None"
            output = surround(self.sides + p, "penetrating")
        elif self.nuclear:
            n = surround(self.nuclear, ",flatten") \
                if not isinstance(self.nuclear, bool) else ",None"
            output = surround(self.sides + n, "nuclear")
        else: output = surround(self.sides, "roll")
        x = surround(self.exploding, ",flatten") if self.exploding else ",None"
        r = surround(self.r, ",flatten") if self.r else ",None"
        rr = surround(self.rr, ",flatten") if self.rr else ""
        output = surround([output + x + r + rr], "anyroll")
        if self.verbose_level >= 2 - self.list: output += "#"
        output = surround([output, str(self.amount)], "iter")
        keep_args = [] ; keep_str = "keep"
        if self.keep_high:
            keep_args += [str(self.keep_high)]
            keep_str += "high"
        if self.keep_low:
            keep_args += [str(self.keep_low)]
            keep_str += "low"
        if keep_args: output = surround(
            keep_args + [output], keep_str)
        if not self.list: output = surround(output, "sum")
        if self.verbose_level >= 1: output += "#"
        return output
    

    def replace(self, txt: str) -> str:
        """Replace the dice notation with mathematical expression."""
        return txt[:self.start] + self.translate() + txt[self.end+1:]



def analyse_dice(txt: str, i: int, scuff: bool = False) -> Dice:
    """Analyze a dice roll expression."""
    if txt[i] != "d": return None # Only start from 'd'
    dice = Dice(i, i) # Start the instance
    if not dice_start(dice, txt, i): return None
    if not dice_end(dice, txt, i, scuff): return None
    if not dice.final_param(): return None
    return dice
    

def dice_start(dice: Dice, txt: str, i: int) -> bool:
    if i == 0: return True
    if txt[i-1] in _AFTER_STR:
        if dice.amount is None:
            dice.amount = txt[i-1]
        else: dice.amount = txt[i-1] + dice.amount
        return dice_start(dice, txt, i-1)
    if txt[i-1].isalpha(): return False
    value = dice_value(txt, i-1, ")")
    if value:
        if dice.amount is None:
            dice.amount = value.content
        else: dice.amount = value.content + dice.amount
        dice.start = value.start
    return True


def dice_end(dice: Dice, txt: str, i: int, scuff: bool = False) -> bool:
    if i >= len(txt)-1: return True
    # Test if is a dice arg
    if txt[i+1] in _DICE_ARGS or \
        (scuff and txt[i+1] == "?"):
        if dice.sides is None or dice.sides == "?" :
            dice.set_param(txt[i+1])
            dice.end = i+1
            return dice_end(dice, txt, i+1, scuff)
        if not isaddon(txt, i+1):
            if txt[i+1] in _AFTER_STR:
                dice.end = i+1
                return dice_end(dice, txt, i+1, scuff)
            return False
    # Test if is addon after sides_number
    addon = isaddon(txt, i+1)
    if addon:
        if dice.sides is None: return False
        if i+len(addon) <= len(txt)-2:
            nxt = dice_value(txt, i+len(addon)+1, "(", False)
        else: nxt = None
        dice.set_addon(addon, nxt)
        if nxt: dice.end = nxt.end
        else: dice.end = i+len(addon)
        return dice_end(dice, txt, dice.end, scuff)
    # No function name under any circumstance
    if txt[i+1].isalpha(): return False
    # Value, only first time then exit
    value = dice_value(txt, i+1, "(", False)
    if value:
        if dice.sides is not None: return True
        dice.sides = value.content
        dice.end = value.end
        return dice_end(dice, txt, dice.end, scuff)
    return True


def dice_value(txt, i, parenth: str = None, check_func: bool = True):
    if txt[i] in "πτ" or \
        is_num(txt[i]) or \
        txt[i] == parenth:
            section = analyse(txt, i)
            if check_func: section = check_for_func(txt, section)
            return section
    return None


def isaddon(txt, i):
    for v1 in _DICE_ADDONS:
        for v2 in v1:
            if txt[i:i+len(v2)] == v2:
                return v2
    return None


def surround(txt, prefix) -> str:
    """Return string enclosed by (), optionally with prefix."""
    if isiterable(txt): txt = ','.join(txt)
    return f"{prefix}({txt})" if prefix else f"({txt})"