"""
Dice and rolling logic, used in conjuction along with logic.py
Specifically targeted towards Evaluation.py
"""



##################################################
# IMPORTS
##################################################



from discord.ext.commands.context import Context as CTX

from random import choices, randint
from Modules.logic import is_num, _REPLACE, replace_simple
from Modules.logic import _AFTER_STR, resolve, noresolve_stack
from Modules.logic import analyse, check_for_func
from Modules.basic import isiterable, surround



##################################################
# GLOBALS
##################################################
    


# Acceptable args on _d<here>_
_DICE_ARGS = set("@!^vl#xpn~-")
# Acceptable args on _d_<here>
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
    # x, r and rr need only to be evaluated once in their str form
    x = resolve(x, *s) or set()
    r = resolve(r, *s) or set()
    rr = resolve(rr, *s) or set()

    rolled = None ; mx = None
    while rolled is None or rolled in rr:
        result = resolve(expr, *s)
        # Most dice function return (result, max)
        if isinstance(result, tuple):
            rolled, mx = int(result[0]), result[1]
        else: rolled = int(result[0])
        # 'reroll-once' must be an iterable
        if r and isiterable(r) and rolled in r:
            # Once exhausted, do not apply on recursion
            return anyroll(s, expr, x, None, rr)

    # If exploding is true and rolled max
    # Or exploding is a list and rolled among it
    if x and ((isinstance(x, bool) and mx and rolled == mx)
            or (isiterable(x) and rolled in x)):
        rolled += anyroll(s, expr, x, r, rr)
    return rolled


def roll(s: tuple, x: str) -> (int, int):
    """Roll an x sided dice."""
    sides = int(resolve(x, *s)) ; m = 1
    if sides == 0: return 0, None # d0 = [0]
    # randint() only accepts positive numbers, so we use m as negative multiplier
    (sides, m) = (sides, 1) if sides > 0 else (-sides, -1)
    # Note that in case of negative sides, redurned max is the lowest
    if sides == 1: return randint(0, 1) * m, sides # d1 = [0;1] | d-1 = [-1;0]
    return randint(1, sides) * m, sides # dX = [1;X] | d-X = [-X;-1]


def penetrating(s: tuple, x: str, p: str = None, first: bool = True) -> (int,int):
    """Roll x, reroll lower x if result is max."""
    # Like anyroll(), only calculated once
    sides = int(resolve(x, *s))
    p = resolve(p, *s)
    if sides not in DICE_LIST: raise ValueError(
        "Penetrating dice must have sides in " +
        f"[{', '.join(DICE_LIST)}]")
    
    # Roll the actual dice
    rolled, mx = roll(s, sides)
    # If p is not instantiated, use the max of the dice
    if not isiterable(p): p = {mx}
    index = DICE_LIST.index(sides)
    if rolled in p and index != 0: # Penetrating : lower face on reroll 
        rolled += penetrating(s, DICE_LIST[index - 1], p, False)[0]
    return rolled, sum(DICE_LIST[:index+1]) \
        if first else rolled, None # ^ Compute max here as well


def nuclear(s: tuple, x: str, n: str = None, first: bool = True) -> (int,int):
    """Roll x, reroll higher x if result is max."""
    # Like anyroll(), only calculated once
    sides = int(resolve(x, *s))
    n = resolve(n, *s)
    if sides not in DICE_LIST: raise ValueError(
        "Nuclear dice must have sides in " +
        f"[{', '.join([str(i) for i in DICE_LIST])}]")
    
    # Roll the actual dice
    rolled, mx = roll(s, sides)
    # If p is not instantiated, use the max of the dice
    if not isiterable(n): n = {mx}
    index = DICE_LIST.index(sides)
    if rolled in n and index != len(DICE_LIST)-1: # Nuclear : higher face on reroll 
        rolled += nuclear(s, DICE_LIST[index + 1], n, False)[0]
    return rolled, sum(DICE_LIST[index:]) \
        if first else rolled, None # ^ Compute max here as well


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
        self.nuclear = False   ; self.negative = False
        self.keep_high = None  ; self.keep_low = None
        self.r = set()         ; self.rr = set()
        self.average_level = 0 # TODO: not implemented
    

    def set_param(self, param):             
        """Set a diceroll parameter among [ @!^vl#xpn~?- ]."""
        # One function call can set multiple params
        if isiterable(param) or \
            (isinstance(param, str) and len(param) > 1):
                for i in param: self.set_param(i)
                return
        match param:
            case "@": self.advantage += 1
            case "!": self.disadvantage += 1
            case "^":
                self.keep_high = self.keep_high or 0
                self.keep_high += 1
            case "v":
                self.keep_low = self.keep_low or 0
                self.keep_low += 1
            case "l": self.list = True
            case "#": self.verbose_level += 1
            case "x": self.exploding = True
            case "p": self.penetrating = True
            case "n": self.nuclear = True
            case "-": self.negative = not self.negative
            case "~": self.average_level += 1
            case "?": self.sides = "?"
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
        if self.adv: # Adv or dAdv solely based on @ and !
            self.sides = self.sides or 20 # Default to 20
            self.amount = self.amount or abs(self.adv)+1 # 1 Adv = 2dX
            if self.adv > 0 and self.keep_high is None:
                self.keep_high = 1 # Only keep one
            elif self.keep_low is None: self.keep_low = 1
        # Without advantage, d20 defaults to 1d20
        elif self.amount is None: self.amount = 1
        # Cannot do anything with dice if there is no side parameter
        if self.sides is None: return False
        return True


    def translate(self) -> str:
        """Translate the parameters into a string."""
        # First function is the actual roll function
        if self.sides == "?": output = "scuff()"
        elif self.penetrating:
            # If p is provided, make it a flattened set
            p = ",None" if isinstance(self.penetrating, bool) \
                else surround(self.penetrating, ",flatten")
            output = surround(self.sides + p, "penetrating")
        elif self.nuclear:
            # If n is provided, make it a flattened set
            n = ",None" if isinstance(self.nuclear, bool) \
                else surround(self.nuclear, ",flatten")
            output = surround(self.sides + n, "nuclear")
        # Normal dice rolling is also allowed
        else: output = surround(self.sides, "roll")

        # x is either None, True, or a set to be flattened
        if not self.exploding: x = ",None"
        elif self.exploding is True: x = ",True"
        elif isinstance(self.exploding, set): 
            x = surround(self.exploding, ",flatten")
        else: raise TypeError(f"Cannot make sense of x '{self.exploding}")
        # r and rr are always Noe or sets, so this will suffice
        r = surround(self.r, ",flatten") if self.r else ",None"
        rr = surround(self.rr, ",flatten") if self.rr else ""
        # ",None" and "" to ensure output + x + r + rr is coherent
        output = surround([output + x + r + rr], "anyroll")

        # Negative sides gives negative results
        if self.negative: output = surround(["0", output], "sub")

        # Output every low-level roll
        if self.verbose_level >= 2 - self.list: output += "#"
        # Iterate with number of sides
        output = surround([output, str(self.amount)], "iter")

        # Advantage and disadvantage part
        keep_args = [] ; keep_str = "keep"
        if self.keep_high:
            keep_args += [str(self.keep_high)]
            keep_str += "high"
        if self.keep_low:
            keep_args += [str(self.keep_low)]
            keep_str += "low"
        # Function keephigh|low works in this very order
        # High to keep, Low to keep, From what to keep
        if keep_args: output = surround(
            keep_args + [output], keep_str)
        # If not asking for a list of results, wrap in summation
        if not self.list: output = surround(output, "sum")
        if self.verbose_level >= 1: output += "#" # Output the final result
        return output.lower() # In lowercase
    

    def replace(self, txt: str) -> str:
        """Replace the dice notation with mathematical expression."""
        return txt[:self.start] + self.translate() + txt[self.end+1:]



##################################################
# FUNCTIONS
##################################################



def translate_dice(arg: str, scuff: bool = False, noresolve: list = None) -> (str,bool):
    """Translate dice-rolling input into a mathematical expression"""
    if isiterable(arg): return [translate_dice(i) for i in arg]
    arg = replace_simple(arg, _REPLACE) # Sanitize string
    has_dice = False ; i = 0
    while i < len(arg):
        # Find if a dice notation is present at this index
        dice = analyse_dice(arg, i, scuff)
        if dice: # If a dice expression is found
            arg = dice.replace(arg) # Replace the dice with its translation
            if noresolve is not None: # Log the change if needed
                noresolve_stack(noresolve, arg, "Dice")
            i = 0 ; has_dice = True # Restart the loop
        i += 1
    return arg, has_dice


def analyse_dice(txt: str, i: int, scuff: bool = False) -> Dice:
    """Analyze a dice roll expression."""
    if txt[i] != "d": return None # Only start from 'd'
    dice = Dice(i, i) # Start the instance
    # Here, dice is modified by reference
    if not dice_start(dice, txt, i): return None
    if not dice_end(dice, txt, i, scuff): return None
    if not dice.final_param(): return None
    return dice
    

def dice_start(dice: Dice, txt: str, i: int) -> bool:
    """Analyse the pre-d part of dice."""
    if i == 0: return True # There can be nothing

    # Or an 'after' symbol like ²!~#
    if txt[i-1] in _AFTER_STR:
        # In that case, update dice.amount...
        if dice.amount is None:
            dice.amount = txt[i-1]
        else: dice.amount = txt[i-1] + dice.amount
        # ...and iterate backwards to search further
        return dice_start(dice, txt, i-1)
    
    # If it's alphabetic, cannot happen
    # Constants must be escaped by a ')'
    if txt[i-1].isalpha() and txt[i-1] not in "πτ": return False
    # Acceptable values are either par, func, num or other (consts)
    # But all other Analysis types have already been exhausted
    value = dice_value(txt, i-1, ")")
    if value:
        if dice.amount is None: dice.amount = value.content
        # If dice.amount already contains 'AFTER' symbols
        else: dice.amount = value.content + dice.amount
        dice.start = value.start
    return True


def dice_end(dice: Dice, txt: str, i: int, scuff: bool = False) -> bool:
    """Analyse the post-d part of dice."""
    # Terminate analysis at the end of string
    # If dice.sides is not set and can't be defaulted,
    # it will be caught in final_param()
    if i >= len(txt)-1: return True

    # Test if is a dice arg '@!^vl#xpn~?'
    if txt[i+1] in _DICE_ARGS or \
        (scuff and txt[i+1] == "?"):
        # No more params after dice.sides is set
        if dice.sides is None:
            dice.set_param(txt[i+1])
            dice.end = i+1
            return dice_end(dice, txt, i+1, scuff)
        # If it's neither an addon or an 'AFTER' symbol,
        # then it's a misplaced parameter -> terminate
        if not isaddon(txt, i+1) and \
            not txt[i+1] in _AFTER_STR:
                return False
    
    # Test if it's part of an addon after dice.sides
    addon = isaddon(txt, i+1)
    if addon:
        # Addons only allowed if dice.sides is set,
        # Unless we're taking default @! sides of 20
        if dice.sides is None:
            if dice.advantage - dice.disadvantage != 0:
                dice.sides = 20
            else: return False
        # If addon can have a value argument, look for it
        if i+len(addon) <= len(txt)-2:
            nxt = dice_value(txt, i+len(addon)+1, "(", False)
        else: nxt = None
        # Take it into account and update dice instance
        dice.set_addon(addon, nxt)
        if nxt: dice.end = nxt.end
        else: dice.end = i+len(addon)
        return dice_end(dice, txt, dice.end, scuff)
    
    # Like dice_start, function names need to be escaped by '('
    # For example, d(func()) and not dfunc()
    if txt[i+1].isalpha() and txt[i+1] not in "πτ": return False
    # Value, only first time then exit
    value = dice_value(txt, i+1, "(", False)
    if value:
        # If dice.sides, means we have bad delimitation
        # Since we allow d4(pi) => (d4)*pi,
        # Let's make it so d4π => d4*π
        if dice.sides is not None: return True
        dice.sides = value.content
        dice.end = value.end
        return dice_end(dice, txt, dice.end, scuff)
    return True


def dice_value(txt, i, parenth: str = None, check_func: bool = True):
    """Resolve a value to inject into a dice instance."""
    # Accept either constants, numbers, or parrenth
    if txt[i] in "πτ" or is_num(txt[i]) or txt[i] == parenth:
        section = analyse(txt, i)
        if check_func: section = check_for_func(txt, section)

        if parenth == "(": # If we're going forwards
            i = section.end + 1 # We also check for 'AFTER' symbols
            while i < len(txt) and txt[i] in _AFTER_STR:
                section.end += 1 ; section.content += txt[i] ; i += 1
        # ^ For dice_start, that logic already exists in the function
        return section
    return None


def isaddon(txt, i):
    """Check if txt[i] (and following) is part of a dice addon."""
    for v1 in _DICE_ADDONS: # For every type of addon
        for v2 in v1: # For each of its aliases
            if txt[i:i+len(v2)] == v2:
                return v2
    return None