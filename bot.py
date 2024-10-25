"""
Create and manage bot instances, with different behavior depending on OS:
Windows: runs a single bot in the current console (will prompt if none provided)
Linux: execute one or more bot instances in screen sessions (will prompt if none provided)
example usage: python3 bot.py <bot_name>
"""



##################################################
# IMPORTS
##################################################



from discord.ext.commands.bot import Bot
from discord import Intents, Activity

from platform import system as pltf_sys
from os import listdir, path
from sys import argv
from subprocess import run, PIPE
from asyncio import get_event_loop, gather
from asyncio import run as asyncrun
from pkg_resources import require, VersionConflict, DistributionNotFound
from datetime import datetime

from Modules.data import data_JSON, data_TXT
from Modules.basic import makeiterable, correspond, least_one



##################################################
# BOTBUILDER
##################################################



async def build_bot(path: str) -> Bot:
    """
    Create the bot instance with the given source file.
    Location is given relative to ./Resources/Configs/. directory.
    """
    if not path.endswith(".json"): path += ".json"
    data = data_JSON("./Resources/Configs/" + path)
    base_intent = getattr(Intents(), data["base_intent"])
    intents = toggle_intents(base_intent(), data["target_intents"])
    bot = Bot(data["prefix"], case_insensitive = True,
               strip_after_prefix = True, activity = Activity(),
               intents = intents) # Default activity and status are set in @on_ready()
    for ext in data["base_extensions"]: # No extension is loaded by default
        name = "Extensions." + ext.removesuffix(".py").capitalize()
        await bot.load_extension(name) # load is asynchronous
    location = "/Secret/" + data["token_location"]
    TOKEN = data_TXT(location, "token")["token"]
    await bot.start(TOKEN, reconnect = True)
    return bot



def toggle_intents(obj: Intents, intents: list) -> Intents:
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
            for f in listdir("./Resources/Configs/")
            if f.endswith(".json")} ; to_launch = set()
    if not names: # Ask for names
        print("Available config files:\n" + " ".join(all_files))
        names = input("Enter bot names to launch (one line):\n").lower().split(" ")
    names = [n.removesuffix(".json") for n in names if n]
    for n in names:
        corr = correspond(n, all_files)
        if corr: # Match found
            to_launch.add(corr)
        else: raise FileNotFoundError(f"Did not find file corresponding with '{n}'")
    return {i for i in to_launch}



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

        name = "DiscordBot;" + n + datetime.today().strftime(";%d/%m/%Y;%H:%M:%S")
        screen = f"screen -dmS '{name}' bash -c"
        source = f"source {venv_path}/bin/activate"
        pip = "pip install -r requirements.txt"
        python = "python3 bot.py " + n + " --no-screen"
        cmd =  f"{screen} '{source} && {pip} && {python}'"

        print(f"Starting '{n}' in screen '{name}'")
        run(cmd, shell=True)



def get_active_bots():
    """
    Get all screen sessions starting with DiscordBot
    Kill those that are not running python
    Retreive the bot name among the remaining
    """
    result = run(['screen', '-list'], stdout=PIPE, text=True)
    sessions = result.stdout.splitlines()
    sessions = [line.strip() for line in sessions if '\t' in line]
    
    active_bots = set()
    for session in sessions:
        # 00000.DiscordBot;name;dd/mm/yyyy;hh:mm:ss'
        parts = session.split('.')
        if len(parts) <= 1 or not parts[1].startswith("DiscordBot;"): continue
        
        session_id, session_info = parts[0], parts[1]
        bot_name = session_info.split(';')[1]
        if is_active(session_id):
            active_bots.add(bot_name)
        else: kill_screen(session_id, bot_name)

    return active_bots



def is_active(session_id: str) -> bool:
    """
    Check if the screen session is running 'python3 bot.py'.
    """
    result = run(['ps', '-p', session_id, '-o', 'cmd='], stdout=PIPE, text=True)
    process_cmd = result.stdout.strip()
    return 'python3 bot.py' in process_cmd



def kill_screen(session_id: str, name: str = None):
    """Terminates a screen session by its session ID."""
    run(['screen', '-S', session_id, '-X', 'quit'], check=True)
    txt = f" (which used to run '{name}')" if name else ""
    print(f"Killed screen session {session_id}{txt}.")



##################################################
# MAIN
##################################################



def main(to_launch: set) -> None:
    if not to_launch:
        raise TypeError("No configs given to resolve and launch")
    async def asyncmain(schedule) -> None:
        await gather(*schedule)
    schedule = [build_bot(f) for f in to_launch]
    asyncrun(asyncmain(schedule))
    


if __name__ == "__main__":
    myargs = [a.lower() for a in argv[1:]]
    if least_one(["--help", "--h"], myargs): bothelp()
    noscreen = "--no-screen" in myargs
    trueargs = [i for i in myargs if not i.startswith("-")]
    to_launch = names_to_files(*trueargs)

    if pltf_sys() == "Windows":
        require(data_TXT("./requirements.txt"))
        main(to_launch)
    elif pltf_sys() == "Linux":
        try: require(data_TXT("./requirements.txt"))
        except (VersionConflict, DistributionNotFound) as e:
            if not noscreen: start_screen("./venv", to_launch)
            else: raise e
        else: main(to_launch)
    else: raise NotImplementedError("Can only run in windows and linux")
