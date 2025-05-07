"""
Dice and rolling logic, used in conjuction along with logic.py
Specifically targeted towards Evaluation.py
"""



##################################################
# IMPORTS
##################################################



from discord.ext.commands.context import Context as CTX

from random import choices, randint
from Modules.logic import is_num
from Modules.logic import _AFTER_STR, resolve
from Modules.logic import _REPLACE, replace_simple
from Modules.logic import analyse, check_for_func
from Modules.basic import isiterable, surround



##################################################
# GLOBALS
##################################################
    


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
DICE_LIST = [4, 6, 8, 10, 12, 20, 100]


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
    p = resolve(p, *s)
    if not isiterable(p): p = {sides}
    if sides not in DICE_LIST: raise ValueError(
        "Penetrating dice must have sides in " +
        f"[{', '.join(DICE_LIST)}]")
    rolled = roll(s, sides)[0]
    index = DICE_LIST.index(sides)
    if rolled in p and index != 0:
        rolled += penetrating(s, DICE_LIST[index - 1], p, False)[0]
    return rolled, sum(DICE_LIST[:index+1]) \
        if first else rolled, None


def nuclear(s: tuple, x: str, n: str = None, first: bool = True) -> (int,int):
    """Roll x, reroll higher x if result is max."""
    sides = int(resolve(x, *s))
    n = resolve(n, *s)
    if not isiterable(n): n = {sides}
    if sides not in DICE_LIST: raise ValueError(
        "Nuclear dice must have sides in " +
        f"[{', '.join([str(i) for i in DICE_LIST])}]")
    rolled = roll(s, sides)[0]
    index = DICE_LIST.index(sides)
    if rolled in n and index != len(DICE_LIST)-1:
        rolled += nuclear(s, DICE_LIST[index + 1], n, False)[0]
    return rolled, sum(DICE_LIST[index:]) \
        if first else rolled, None


SOURCE = {
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
    774649444842209300, # Ghost
})

def allow_scuff(ctx: CTX) -> bool:
    """Check if user is allowed to SCUFF™."""
    if ctx.author.id in _ALLOW: return True
    return ctx.guild is not None and \
        ctx.guild.get_member(_JESUS)


_SCUFF = {1: 24, 2: 81, 3: 21, 4: 12, 5: 27,
          6: 24, 7: 2, 8: 40, 9: 29, 10: 18,
          11: 10, 12: 41, 13: 17, 14: 6, 15: 28,
          16: 16, 17: 22, 18: 18, 19: 101, 20: 34}

def scuff(s: tuple) -> (int, int):
    """Return a d20 output using the SCUFF™ dice"""
    return choices(list(_SCUFF.keys()),
        weights=list(_SCUFF.values()), k=1)[0], 20



##################################################
# DICE
##################################################



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



##################################################
# FUNCTIONS
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
        if dice.sides is None and \
            not dice.advantage and \
            not dice.disadvantage:
                return False
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