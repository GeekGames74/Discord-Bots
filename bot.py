"""
Create and manage bot instances, with different behavior depending on OS:
Windows: runs a single bot in the current console (will prompt if none provided)
Linux: execute one or more bot instances in screen sessions (will prompt if none provided)
example usage: python3 bot.py <bot_name>
"""



##################################################
# IMPORTS
##################################################



from platform import system as pltf_sys
from os import listdir, path
from sys import argv
from subprocess import run, PIPE
from asyncio import gather, Event, create_task
from asyncio import run as asyncrun

from Modules.data import data, path_from_root
from Modules.basic import makeiterable, correspond, least_one



##################################################
# BOTBUILDER
##################################################



async def build_bot(path: str):
    """
    Create the bot instance with the given source file.
    Location is given relative to ./Resources/Configs/. directory.
    """
    from discord.ext.commands.bot import Bot
    from discord import Intents, Activity
    print(f"Starting bot '{path}'")
    
    if not path.endswith(".json"): path += ".json"
    config = data("Resources/Configs/" + path, filenotfound = False)
    base_intent = getattr(Intents(), config["base_intents"])
    intents = toggle_intents(base_intent(), config["target_intents"])
    bot = Bot(config["prefix"], case_insensitive = True,
               strip_after_prefix = True, activity = Activity(),
               intents = intents) # Default activity and status are set in @on_ready()
    
    for ext in config["extensions"]: # No extension is loaded by default
        name = "Extensions." + ext.removesuffix(".py").capitalize()
        await bot.load_extension(name) # load is asynchronous
    for cog in config["unload_cogs"]: # Disable these cogs
        await bot.remove_cog(cog.capitalize())
    
    TOKEN = data("Secret/" + config["token"], filenotfound = False)
    bot.shutdown = Event() # Signal to terminate the bot
    create_task(bot.start(TOKEN, reconnect = True))
    await bot.shutdown.wait() # When the shutdown signal is sent
    await bot.close()
    return bot


def toggle_intents(obj, intents):
    """Toggle the intents in the obj, then return it."""
    intents = makeiterable(intents)
    for name in intents:
        value = getattr(obj, name)
        if isinstance(value, bool):
            value = not value
        else: raise Exception()
        obj.__setattr__(name, value)
    return obj



##################################################
# FUNCTIONS
##################################################



def bothelp(): print("TODO: help")


def names_to_files(*names: str) -> set:
    """
    Get the config files from the given names.
    If no names are given, ask for them.
    """
    all_files = {f.lower().removesuffix(".json")
        for f in listdir(path_from_root("Resources/Configs/"))
        if f.endswith(".json")} ; to_launch = set()
    if not names: # Ask for names
        print("Available config files:\n" + " ".join(all_files))
        names = input("Enter bot names to launch (one line):\n").lower().split(" ")
    names = [n.removesuffix(".json") for n in names if n]
    for n in names:
        corr = correspond(n, all_files)
        if corr: to_launch.add(corr)
        else: raise FileNotFoundError(f"Did not find file corresponding with '{n}'")
    return to_launch



##################################################
# SCREEN
##################################################



def start_screen(venv_path: str, to_launch: set):
    """
    For each bot to launch:
    - start a screen session,
    - activate a venv with dependencies,
    - and launch the bot.py script.
    """
    active_bots = get_active_bots()
    for n in to_launch:
        if n in active_bots:
            print(f"Bot '{n}' is already running.")
            continue

        if not path.exists(venv_path): # Ensure venv is setup
            print(f"Creating virtual environment at {venv_path}...")
            run(f"python3 -m venv {venv_path}", shell=True)

        name = "Discord-Bot:" + n
        screen = f"screen -dmS '{name}' bash -c"
        source = f"source {venv_path}/bin/activate"
        pip = "pip install -r requirements.txt"
        python = "python3 bot.py " + n + " --no-screen"
        cmd =  f"{screen} '{source} && {pip} && {python}'"
        print(f"Starting '{n}' in screen '{name}'")
        result = run(cmd, shell=True, capture_output=True, text=True)
        if result.stderr: print(result.stderr)
        if result.stdout: print(result.stdout)


def get_active_bots():
    """
    Get all screen sessions starting with Discord-Bot:
    Retreive the bot name(s) in a list
    """
    result = run(['screen', '-list'], stdout=PIPE, text=True)
    sessions = result.stdout.splitlines()
    sessions = [line.strip() for line in sessions if '\t' in line]

    active_bots = set()
    for session in sessions:
        # 00000.Discord-Bot:name\t...
        parts = session.split('.')
        if len(parts) <= 1 or not parts[1].startswith("Discord-Bot:"): continue
        session_id, session_info = parts[0], parts[1]
        bot_name = session_info.split(':')[1].split('\t')[0]
        active_bots.add(bot_name)
    return active_bots



##################################################
# MAIN
##################################################



def main(to_launch: set) -> None:
    """Launch all requested bots one after the other using async."""
    if not to_launch: raise TypeError("No configs given to resolve and launch")
    async def asyncmain(schedule) -> None:
        try: await gather(*schedule)
        except Exception as e: print(e)
    schedule = [build_bot(f) for f in to_launch]
    try: asyncrun(asyncmain(schedule))
    except KeyboardInterrupt: print("Aborted script (KeyboardInterrupt)")


if __name__ == "__main__":
    myargs = [a.lower() for a in argv[1:]]
    if least_one(["--help", "-h"], myargs): bothelp()
    noscreen = "--no-screen" in myargs
    trueargs = [i for i in myargs if not i.startswith("-")]
    to_launch = names_to_files(*trueargs)

    if pltf_sys() == "Windows": main(to_launch)
    elif pltf_sys() == "Linux":
        try: main(to_launch)
        except ModuleNotFoundError as e:
            if not noscreen: start_screen("./venv", to_launch)
            else: raise e
        except Exception as e: raise e
    else: raise NotImplementedError("Can only run in windows and linux")

