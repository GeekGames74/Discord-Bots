"""
Logic module for calculation, randomness, and boolean operations.
"""



##################################################
# IMPORTS
##################################################



from asyncio import TimeoutError
from time import time
from Modules.data import data
from Modules.basic import isiterable, flatten
import math ; import random



##################################################
# GLOBALS
##################################################



_ARG_TIMEOUT = 5


# numbers (as str) 0-9 (because '²'.isdigit() return True)
def nums() -> str: return "".join([str(n) for n in range(10)])
# is numerical or part of decimal point
def is_num(txt: str): return all([c in nums() or c == "." for c in txt])

def symb_comma() -> set: return set(_SYMBOLS.keys()).union({","})


_LOGIC_FUNC = {} ; _SYMBOLS = {} ; _NAMES = {}
_MID = [{} for i in "x"*6]
_AFTER = {} ; _NO_RESOLVE = set()

_CONSTANTS = {
    "pihold()": ["pi", "π"],
    "tauhold()": ["tau", "τ"],
    "ehold()": ["e"],
    "random()": ["?"],
    "truehold()": ["true"],
    "falsehold()": ["false"],
    "nonehold()": ["none", "null", "void"]
}

_REPLACE = {
    "(": ["[", "{"],
    ")": ["]", "}"],
    "+": ["++", "--"]
}

_ALLOW = set("abcdefghijklmnopqrstuvwxyzπτ()[]{},.?")
_ALLOW = _ALLOW.union(nums())


def set_globals() -> None:
    """Set global variables for the module"""
    global _SYMBOLS ; global _NAMES ; global _LOGIC_FUNC
    # Get the function data from the json file (raise error if doesn't exist)
    _LOGIC_FUNC = data("Resources/Files/logic.json", filenotfound = False)

    for key, value in _LOGIC_FUNC.items():
        _NAMES[key] = value["aliases"]
        # Functions for which args should not be resolved outside
        if not value.get("resolve", True):
            _NO_RESOLVE.add(key)
        if "symbols" in value:
            # Set the dict key to the 'top-level' symbol
            _SYMBOLS[value["symbols"][0]] = []
            for s in value["symbols"]: _ALLOW.add(s)

            if value["placement"] == "mid": # if symbol goes between args
                _MID[value["priority"]-1][value["symbols"][0]] = key
            elif value["placement"] == "after": # if symbol goes after arg
                _AFTER[value["symbols"][0]] = key
            
            if len(value["symbols"]) > 1: # 'low-level' symbols as dict values
                _SYMBOLS[value["symbols"][0]] = value["symbols"][1:]

set_globals()

_AFTER_STR = "".join(_AFTER.keys())
_TYPES = {"comma", "other", "symbol", "num", "alpha", "par", "func"} # Analysis types



##################################################
# ANALYSIS
##################################################


class Analysis:
    """Analysis class for the module"""
    def __init__(self, start: int, end: int, content: str, type: str) -> None:
        """Initialise the Analysis class"""
        if start > end: raise ValueError("Start index must be less than end index")
        if type.lower() not in _TYPES:
            raise ValueError(f"Invalid type : '{type.lower()}'")
        self.start = start ; self.end = end
        self.content = content
        self.type = type.lower()


def analyse(txt: str, i: int) -> Analysis:
    """
    Return several informations about a string section:
    start, end, literal string, type
    """
    if i < 0 or i >= len(txt): raise IndexError("Index out of range")
    # Regular characters, no analysis needed
    if txt[i] == ",": return Analysis(i, i, txt[i], "comma")
    if txt[i] in "πτ?": return Analysis(i, i, txt[i], "other")
    # Among the list of symbols (only top-level symbols)
    if txt[i] in _SYMBOLS: return Analysis(i, i, txt[i], "symbol")
    # Number or function name (or constant name)
    if is_num(txt[i]): return analyse_num(txt, i)
    if txt[i].isalpha(): return analyse_alpha(txt, i)
    # Part of a parenthesis/bracket pair
    if txt[i] == "(": return analyse_left_par(txt, i)
    if txt[i] == ")": return analyse_right_par(txt, i)
    # Unknown character (filtered before, so newly introduced)
    raise ValueError(f"What is '{txt[i]}' at index {i} ?")


def analyse_left_par(txt: str,  i: int) -> Analysis:
    x = 1 ; end_index = i
    while x != 0: # thanks to cleanup(), we know a pair exists
        end_index += 1 # therefore this should always end
        if txt[end_index] == "(": x += 1
        elif txt[end_index] == ")": x -= 1
    return Analysis(i, end_index, txt[i:end_index+1], "par")

def analyse_right_par(txt: str,  i: int) -> Analysis:
    x = -1 ; start_index = i
    while x != 0: # thanks to cleanup(), we know a pair exists
        start_index -= 1 # therefore this should always end
        if txt[start_index] == "(": x += 1
        elif txt[start_index] == ")": x -= 1
    return Analysis(start_index, i, txt[start_index:i+1], "par")

def analyse_alpha(txt: str,  i: int) -> Analysis:
    start = i ; end = i ; mx = len(txt)-1
    # Go backwards in text until no longer alpha
    while start != 0 and txt[start - 1].isalpha(): start -= 1
    # Go forwards in text until no longer alpha
    while end != mx and txt[end + 1].isalpha(): end += 1
    return Analysis(start, end, txt[start:end+1], "alpha")

def analyse_num(txt: str,  i: int) -> Analysis:
    start = i ; end = i ; mx = len(txt)-1
    # Go backwards in text until no longer num
    while start != 0 and is_num(txt[start - 1]): start -= 1
    # Go forwards in text until no longer num
    while end != mx and is_num(txt[end + 1]): end += 1
    return Analysis(start, end, txt[start:end+1], "num")


def check_for_func(txt: str, section: Analysis) -> Analysis:
    """Check if section parenthesis is linked to a function."""
    # If our parenthesis section is preceded by a function name
    if section.type == "par" and section.start != 0 and txt[section.start-1].isalpha():
        new_section = analyse(txt, section.start-1)
        section = Analysis(new_section.start, section.end,
            new_section.content + section.content, 'func')
    # If our function name is folowed by a parenthesis (function)
    elif section.type == "alpha" and section.end != len(txt)-1 and txt[section.end+1] == "(":
        new_section = analyse(txt, section.end+1)
        section = Analysis(section.start, new_section.end,
            section.content + new_section.content, 'func')
    return section


##################################################
# SYNTAX
##################################################



def cleanup(txt: str) -> str:
    """Remove whitespace and fix parentheses."""
    txt = txt.lower() # <-- to be safe, shouldn't be needed
    txt = "".join([i for i in txt if i in _ALLOW])
    txt = replace_simple(txt, _REPLACE)
    txt = ensure_parenthesis(txt)
    return txt


def ensure_parenthesis(txt: str):
    """Fill in parentheses on eiter side to ensure valid entry"""
    current_count = 0 ; leading = 0
    for i in txt:
        # positive for more nesting
        if i == "(": current_count += 1
        # negative when getting out of a pair
        elif i == ")": current_count -= 1
        if current_count == -1:
            leading += 1
            current_count += 1
    txt = "("*leading + txt + ")"*current_count
    return txt


def replace_simple(txt: str, source: dict) -> str:
    """Replace elements of value by key"""
    for key, value in source.items():
        for element in value:
            while element in txt:
                txt = txt.replace(element, key)
    return txt


def replace_targeted(txt: str, source: dict, func: bool) -> str:
    """
    Replace elements of value by key
    Unlike replace_simple, this works by checking along the txt
    and dynamically replacing the whole element using analysis
    """
    index = 0
    while index < len(txt):
        # Here, we analyse the txt to gather info
        section = analyse(txt, index)
        for key, value in source.items():
            if section.content in value: # if analysis substring is an alias
                replace = str(key) # We also need implicit multiplication
                # Otherwise, 2pi --> 23.14159 and not 2*3.14159
                if section.start > 0 and \
                    (is_num(txt[section.start - 1]) or \
                    txt[section.start - 1] == ")" or \
                    txt[section.start - 1] in _AFTER_STR):
                        replace = "*" + replace
                if section.end < len(txt) - 2 and \
                    (is_num(txt[section.end + 1]) or \
                    (txt[section.end + 1] == "(" and func) or \
                    txt[section.end + 1].isalpha()):
                        replace = replace + "*"
                txt = txt[:section.start] + replace + txt[section.end + 1:]
        if section.type == "par": index += 1
        # We can skip the whole section if it doesn't nest
        else: index = section.end + 1
    return txt
        


##################################################
# IMPLICIT OPERATIONS
##################################################



def implicit_multiplication(txt: str) -> str:
    """Place asterixes on implicit multiplication."""
    index = 0
    while index < len(txt):
        section = analyse(txt, index)
        # We check the 'after', then the 'before'
        # So that txt indices don't move too much
        if section.type not in ["symbol", "comma"]:
            # IF it's not at the end AND not before ')'
            # AND not before a top-level symbol or ','
            # AND is not between function name and '('
            if section.end != len(txt)-1 and \
                txt[section.end + 1] != ")" and \
                txt[section.end + 1] not in symb_comma() and \
                (section.type != "alpha" or txt[section.end + 1] != "("):
                    # Insert a '*' after the current section
                    txt = txt[:section.end+1] + "*" + txt[section.end + 1:]
            # IF it's not at the start AND not after '('
            # AND not before a top-level symbol or ','
            # AND is not between function name and '('
            if section.start != 0 and \
                txt[section.start - 1] != "(" and \
                (txt[section.start - 1] not in symb_comma() or \
                 txt[section.start - 1] in _AFTER_STR) and \
                (section.type != "par" or not txt[section.start - 1].isalpha()):
                    # Insert a '*' before the current section
                    txt = txt[:section.start] + "*" + txt[section.start:]
        if section.type == "par": index += 1
        # We can skip the whole section if it doesn't nest
        else: index += section.end - section.start + 1
    return txt


def implicit_zero(txt: str) -> str:
    """Place zero before vacant '-' or '+', or before/after vacant '.'"""
    index = 0
    while True: # Decimal point
        index = txt.find('.', index)
        if index == -1: break
        # Check after then before to avoid moving indices
        if index == len(txt) - 1 or \
            txt[index+1] not in nums() :
                # 123. --> 123.0
                txt = txt[:index] + '.0' + txt[index+1:]
        if index == 0 or \
            txt[index-1] not in nums():
                # .123 --> 0.123
                txt = txt[:index] + '0.' + txt[index+1:]
        index += 1

    for symbol in ['+', '-']:
        index = 0
        while True: # Find standalone '+' and '-'
            index = txt.find(symbol, index)
            if index == -1: break
            # If at the end or followed by '(': Syntax error to avoid loop/range error
            if index == len(txt) - 1 or txt[index+1] == ')':
                raise SyntaxError(f"Symbol '{symbol}' was misplaced")
            # If at the start or not preceded by a valid argument
            if index == 0 or txt[index-1] not in nums() + ')' + _AFTER_STR:
                # Encapsulate the symbol and the 'after' argument
                section = check_for_func(txt, analyse(txt, index + 1))
                # Inside parentheses
                txt = txt[:index] + '(0' + symbol + section.content + ')' + txt[section.end+1:]
            index += 1
    return txt



##################################################
# FUNCTION PLACEMENT
##################################################



def place_functions(txt: str) -> str:
    """Replace symbols by their function."""
    for key, value in _AFTER.items():
            txt = place_after(txt, key, value)
    for priority in range(6): # Order by priority above all
        for key, value in _MID[priority].items():
            txt = place_mid(txt, key, value)
    return txt


def place_after(txt: str, symbol: str, func: str) -> str:
    """Replace symbol by its function, affecting the previous term."""
    while symbol in txt:
        # From first to last
        index = txt.find(symbol) ; cursor = index ; content = ""
        while True: # section.start-1 is always out of section.content, so this will end
            if cursor <= 0 or txt[cursor-1] == "(": # even if it ends here
                raise SyntaxError(f"Symbol '{symbol}' was misplaced")
            # Next batch of string to process
            section = check_for_func(txt, analyse(txt, cursor - 1)) # Forced backwards
            content = section.content + content # Concatenate content
            # Only 'par','func' and 'num' can be affected by an 'AFTER' symbol
            if section.type in {"par", "func", "num"}: break
            cursor = section.start # Loop again, find the earliest affected element
        # (10/3)~! --> factorial(round(10/3))
        txt = txt[:section.start] + func + "(" + content + ")" + txt[index+1:]
    return txt


def place_mid(txt: str, symbol: str, func: str) -> str:
    """Replace symbol by its function, affecting the previous and next term."""
    while symbol in txt:
        index = txt.index(symbol)
        # If symbol at start or end
        # OR not preceded by a valid argument
        # OR not followed by a valid argument
        if index == 0 or index >= len(txt) - 1 or \
            txt[index-1] not in nums() + ")" + _AFTER_STR or not \
            (txt[index+1] in nums() + "(+-" or txt[index+1].isalpha()):
                raise SyntaxError(f"Symbol '{symbol}' was misplaced")
        # Need to ensure we get the whole functions if any are
        section1 = check_for_func(txt, analyse(txt, index - 1))
        section2 = check_for_func(txt, analyse(txt, index + 1))
        # func(1+1)^func(2+2) --> pow(func(1+1),func(2+2))
        txt = txt[:section1.start] + func + "(" + section1.content + \
            "," + section2.content + ")" + txt[section2.end + 1:]
    return txt



##################################################
# HOLDER
##################################################



class Holder:
    """Holds the static functions for the calculator"""
    @staticmethod
    def abs_(x): return abs(x)
    @staticmethod
    def and_(*x): return all(x)
    @staticmethod
    def avg_(*x): return sum(x)/len(x)
    @staticmethod
    def bool_(x): return bool(x)
    @staticmethod
    def div_(x,y): return x/y
    @staticmethod
    def ehold_(): return math.e
    @staticmethod
    def eq_(x,y): return x == y
    @staticmethod
    def extract_(*x): return x if len(x) > 1 else x[0]
    @staticmethod
    def factorial_(x):
        if x > 1000000: raise OverflowError(
            "factorial() argument should not exceed 1000000")
        return math.factorial(x)
    @staticmethod
    def falsehold_(): return False
    @staticmethod
    def flatten_(*x): return flatten([x])
    @staticmethod
    def grt_(x,y): return x > y
    @staticmethod
    def grteq_(x,y): return x >= y
    @staticmethod
    def ifelse_(x,y,z=None): return y if x else z
    @staticmethod
    def int_(x): return int(x)
    @staticmethod
    def intdiv_(x,y): return x // y
    @staticmethod
    def iter_(s,x,y):
        return [resolve(x, *s) for i in range(resolve(y, *s))]
    @staticmethod
    def iteravg_(s,x,y=1000):
        return Holder.avg_(*[resolve(x, *s) for i in range(resolve(y, *s))])
    @staticmethod
    def itermax_(s,x,y=1000):
        return Holder.max_(*[resolve(x, *s) for i in range(resolve(y, *s))])
    @staticmethod
    def itermin_(s,x,y=1000):
        return Holder.min_(*[resolve(x, *s) for i in range(resolve(y, *s))])
    @staticmethod
    def keephigh_(x,*y): 
        return sorted(flatten(y),reverse=True)[:x]
    @staticmethod
    def keephighlow_(x, y, *z):
        z = flatten(z)
        return sorted(z)[:y] + list(reversed(sorted(z)[y:]))[:x]
    @staticmethod
    def keeplow_(x,*y):
        return sorted(flatten(y))[:x]
    @staticmethod
    def len_(*x): return len(x)
    @staticmethod
    def list_(*x): return x
    @staticmethod
    def logtwo_(x): return math.log2(x)
    @staticmethod
    def logten_(x): return math.log10(x)
    @staticmethod
    def loge_(x): return math.log(x)
    @staticmethod
    def lwr_(x,y): return x < y
    @staticmethod
    def lwreq_(x,y): return x <= y
    @staticmethod
    def max_(*x): return max(x)
    @staticmethod
    def min_(*x): return min(x)
    @staticmethod
    def mod_(x,y): return x % y
    @staticmethod
    def mul_(*x): return math.prod(x)
    @staticmethod
    def nand(*x): return not Holder.and_(*x)
    @staticmethod
    def neq_(x,y): return x != y
    @staticmethod
    def nonehold_(): return None
    @staticmethod
    def nor_(*x): return not Holder.or_(*x)
    @staticmethod
    def not_(x): return not x
    @staticmethod
    def or_(*x): return any(x)
    @staticmethod
    def pihold_(): return math.pi
    @staticmethod
    def pow_(x,y): return x**y
    @staticmethod
    def range_(x, y=None):
        if y is None:
            if x<0: return list(range(x,0))
            else: return list(range(1,x+1))
        else:
            if x>y: x,y = y,x
            return list(range(x,y+1))
    @staticmethod
    def round_(x,y=1): return round(x,y) if y>1 else int(round(x,y))
    @staticmethod
    def root_(x,y=1): return pow(x,1/y)
    @staticmethod
    def sqr_(x): return x**2
    @staticmethod
    def sub_(x,y): return x - y
    @staticmethod
    def sum_(*x): return sum(x)
    @staticmethod
    def tauhold_(): return math.tau
    @staticmethod
    def try_(s,*x):
        for i in x:
            try: return resolve(i, *s)
            except: pass
        return None
    @staticmethod
    def truehold_(): return True
    @staticmethod
    def xnor_(*x): return not Holder.xor_(*x)
    @staticmethod
    def xor_(*x): return any(x) != all(x)



##################################################
# RESOLVE
##################################################



def resolve(txt: str, stack: list = [], source: dict = None, start: float = None) -> any:
    """
    Resolve the nested expression recursively.
    Basically a whole ride to avoid 'eval()'
    """
    if start is None: start = time()
    elif time() - start >= _ARG_TIMEOUT:
        raise TimeoutError("Execution timed out.")
    if not txt: return None
    # Source must be {'name': func}
    if source is None: source = {}
    if not isinstance(txt, str):
        return txt
    # Cull unecessary brackets
    while txt.startswith('('):
        txt = txt[1:-1]
    # If it is a number, just get the value
    if is_num(txt):
        if '.' in txt:
            return float(txt)
        return int(txt)
    
    # If it is a function, get its name
    section = analyse(txt, 0)
    if section.type == "alpha": # And get the actual object from it
        args = get_args(txt[section.end+2 :-1])
        name = section.content
        if name in _LOGIC_FUNC:
            origin = _LOGIC_FUNC[name]["origin"]
            if origin == "math":
                func = getattr(math, name)
            elif origin == "random":
                func = getattr(random, name)
            else: func = getattr(Holder, name + "_")
        elif name in source: func = source[name]
        else: raise NameError(f"Function '{name}' is not recognized.")
    else: # Arguments
        args = get_args(txt)
        return [resolve(arg, stack, source, start) for arg in args]

    # Iteration logic already uses resolve
    if name not in _NO_RESOLVE and name not in source:
        # Resolve arguments
        arguments = [resolve(arg, stack, source, start) for arg in args]
        # Cull None returns
        arguments = [arg for arg in arguments if arg not in [None, ""]]
        # Remove iterables
        if len(arguments) == 1:
            if isiterable(arguments[0]):
                arguments = arguments[0]
    else:
        args = [arg for arg in args if arg not in [None, ""]]
        arguments = [(stack, source, start)] + args

    # Call the function with the arguments
    try: result = func(*arguments)
    except Exception as e:
        name.removesuffix("hold_") ; name.removesuffix("_")
        raise e.__class__(f"An error occured when running '{name}': {e}")
    # To integer if possible, so functions that depend on it work
    if isinstance(result, float) and \
        result.is_integer(): result = int(result)
    # Add it to the call stack (if it's not an iterable)
    if name == "extract":
        if not isiterable(result):
            stack.append(result)
    return result


def get_args(txt: str, comments: str = None) -> list:
    """Get the arguments of a function call from a string."""
    parenthesis_count = 0 ; in_comment = False
    args = [""] ; arg_num = 0
    # From after the first '(' to before the last ')'
    for index in range(len(txt)):
        if comments and txt[index] in comments:
            in_comment = not in_comment
        # Skip if section is commented out
        if in_comment:
            args[arg_num] += txt[index]
            continue
        if txt[index] == '(': parenthesis_count += 1
        # Make sure to not include ',' in the arguments
        if parenthesis_count != 0 or txt[index] != ',':
            args[arg_num] += txt[index]
        if txt[index] == ')': parenthesis_count -= 1
        # Get to the next substring of arguments
        if parenthesis_count == 0 and txt[index] == ',':
            arg_num += 1
            args.append('')
    return args



##################################################
# MAIN
##################################################



def noresolve_stack(stack: list, expression: str,
        comment: str = "", noresolve: bool = True) -> None:
    """Add an expression to the stack for no-resolve purposes."""
    if not noresolve: return # skip if value is False
    if stack: # Find out if adding this expression is needed
        last_comment, last_expr = stack[-1].split(": ", 1)
        if last_expr == expression: return
    stack.append(comment + ": " + expression) # Add to the stack


def main(txt: str, stack: list = None, source: dict = None,
        start: float = None, noresolve: bool = False) -> any:
    """Resolve and output the given expression"""
    if stack is None: stack = []

    # Sanitize expression and ensure it is properly formatted
    cleanup_ = cleanup(txt)
    noresolve_stack(stack, cleanup_, "Sanatized", noresolve)
    # If there is nothing to evaluate
    if not cleanup_: raise SyntaxError("No valid expression to evaluate")

    # Replace low-level symbols by their primary symbol
    symbols_ = replace_simple(cleanup_, _SYMBOLS)
    noresolve_stack(stack, symbols_, "Symbols", noresolve)

    # Replace low-level func aliases by their primary name
    aliases_ = replace_targeted(symbols_, _NAMES, False)
    noresolve_stack(stack, aliases_, "Aliases", noresolve)

    # Replace constants by their function
    constants_ = replace_targeted(aliases_, _CONSTANTS, True)
    noresolve_stack(stack, constants_, "Constants", noresolve)

    # Implicit 0 in _.123, 123._, _-1 or _+1
    implicit_ = implicit_zero(constants_)
    noresolve_stack(stack, implicit_, "Implicit '0'", noresolve)

    # Place asterixes on implicit multiplication )*(
    # Note that some have already been spotted using replace_targeted()
    multiply_ = implicit_multiplication(implicit_)
    noresolve_stack(stack, multiply_, "Implicit '*'", noresolve)

    # Replace top-level symbols by their function
    # In two parts : 'AFTER' symbols (!²#~ etc), then others by priority
    functions_ = place_functions(multiply_)
    noresolve_stack(stack, functions_, "Functions", noresolve)
    
    # And now, actually resolve the expression recursively
    result = None if noresolve else resolve(functions_, stack, source, start)
    return result, stack



if __name__ == "__main__":
    txt = input()
    result, stack = main(txt)
    print(result)
    print(stack)