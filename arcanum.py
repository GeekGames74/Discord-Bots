print("Arcanum.py started")

"""
Arcanum Discord Bot
By GeekGames74 (@geek74)

Roleplay bot aimed towards facilitating channel-based
adventures on the Discord chat app and browser.

Hosted on Google Could Compute Engine as a Virtual Machine
Data on Google Cloud SQL (encrypted at rest and in transit)
"""

__author__ = "GeekGames74"
__email__ = "geekgames74.fr@gmail.com"



##########################################################################
# REQUIREMENTS AND IMPORTS
##########################################################################



import os
import sys
import subprocess
import traceback
import json
import time


try:
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "pip", "--upgrade"], shell= True)
except subprocess.CalledProcessError: pass
REQUIRE = ["discord.py", "asyncio", "nest_asyncio", "dice",
           "cloud-sql-python-connector[pymysql]", "sqlalchemy", "pymysql"]
for package in REQUIRE:
    print(f"Checking and installing '{package}'")
    try:
        subprocess.run([sys.executable, "pip", "install", "-q", package], shell= True)
    except subprocess.CalledProcessError: pass
    except FileNotFoundError: pass


import discord as DSC
from discord import *
from discord.ext import commands as CMDS
from discord.ext.commands import Context as CTX

import asyncio
import nest_asyncio

import dice

from google.cloud.sql.connector import Connector as CON
import sqlalchemy as ALC
import pymysql as SQL



##########################################################################
# CREDENTIALS
##########################################################################



def del_env(var) -> None:
    if isinstance(var, str):
        globals()[var] = "HIDDEN"
        exec(f"{var} = 'HIDDEN'")
        exec(f"del {var}")
    elif isinstance(var, list):
        for i in var:
            del_env(i)


def del_i() -> None:
    del_env("In")
    i = 0
    while i < len(globals()):
        if list(globals().keys())[i].startswith("_i"):
            del_env(list(globals().keys())[i])
        else: i += 1


CRED_FILE = f"{os.path.dirname(os.path.realpath(__file__))}\\credentials.txt"
with open(CRED_FILE) as F:
    vars = ["HOST", "USER", "PASSWORD", "DATABASE", "TOKEN"]
    for i in vars:
        exec(f"{i} = {F.readline()}")
del_env("CRED_FILE")



##########################################################################
# BOT SETUP
##########################################################################



# Intents required by the bot. Limit to minimum.
# Ensure both here and dev portal are setup.
intents = DSC.Intents.default()
intents.message_content = True
intents.members = True


PREFIX = "/"
BOT = CMDS.Bot(command_prefix = PREFIX,
               intents = intents,
               case_insensitive = True,
               strip_after_prefix = True,
               activity = DSC.Activity(),
              )



##########################################################################
# SQL SETUP
##########################################################################



connector = CON()
def getconn() -> SQL.connections.Connection:
    conn: SQL.connections.Connection = connector.connect(
        HOST, "pymysql", user = USER, password = PASSWORD, db = DATABASE)
    return conn


DB = ALC.create_engine("mysql+pymysql://", creator = getconn,)
del_env(["HOST", "USER", "PASSWORD", "DATABASE"])


def sql(txt: str) -> any:
    with DB.connect() as db_conn:
        result = db_conn.execute(ALC.text(txt))
        db_conn.commit()
    if result is not None:
        result = result.fetchall()
        return result



##########################################################################
# GLOBALS AND METHODS
##########################################################################



# Blank server entry for replicating and default parameters.
TEMPLATE={'Keys': {}, 'Items': [], 'Players': {}, 'Paths': {},'Params': {'AllowInv': False, 'AllowTpl': False, 'AllowPath': False, 'AllowInit': False, 'RoleMngInv': None, 'RoleMngTpl': None, 'RoleMngPath': None, 'RoleMngInit': None, 'RoleSeeInv': None, 'RoleSeeTpl': None, 'RoleSeePath': None, 'RoleSkipPath': None, 'RoleSelfInit': None, 'RoleSelf+Inv': None, 'RoleCanSelf-Inv': None, 'RoleCanTrade': None, 'RoleCanSelfInfo': None, 'OnlyTpl': False}}

# List of (object,name,get_method)
TYPES = [(CTX, "ctx", None),
         (DSC.Guild, "guild", "get_guild"),
         (DSC.TextChannel, "channel", "get_channel"),
         (DSC.VoiceChannel, "voice", "get_channel"),
         (DSC.Message, "message", "get_partial_message"),
         (DSC.User, "user", "get_user"),
         (DSC.Role, "role", "get_role"),
         (DSC.Member, "member", "get_member"),
         (DSC.CategoryChannel, "category", "get_channel"),
         (DSC.Emoji, "emoji", "get_emoji"),
        ]


def dsc_toid(input) -> any:
    if isinstance(input, int): return input
    if isinstance(input, str):
        if input.isdigit(): return int(input)
        check = any([input.startswith(i) for i in ["<#", "<&@", "<@"]])
        if check and input.endswith(">"):
            input = [i for i in input if i.isdigit()]
            return int("".join(input))
    return False


def dsc_type(input) -> any:
    for type_, name, call in TYPES:
        if isinstance(input, type_): return name
    if isinstance(input, int) or isinstance(input, str) and input.isdigit():
        return "id"
    else: return None


def dsc_obj(input, obj: str, ctx = None) -> any:
    if dsc_type(input) == obj: return input

    if dsc_toid(input):
        input = dsc_toid(input)

    if ctx is not None:
        if obj == "message": ctx = dsc_obj(ctx, "channel")
        else: ctx = dsc_obj(ctx, "guild")

    if dsc_type(input) == "id":
        if obj == "guild": return BOT.get_guild(int(input))
        method = getattr(ctx, {name: call for (_, name, call) in TYPES}[obj], None)
        return method(int(input))

    elif dsc_type(input) == "ctx":
        if obj in ["user", "member"]: return input.author
        return getattr(input,obj)

    raise TypeError(f"input {input} of type {type(input)} with request '{obj}' in dsc_obj()")


async def reactech(ctx, emoji: str, react: bool = True,
                   recursive: int = -1, timeout: int = 3600, cond: str = "True",
                   method: str = "user.send(args)", *args) -> None:
    msg = dsc_obj(ctx, "message")
    if react: await msg.add_reaction(emoji)

    def check(reaction: DSC.Reaction, user: DSC.User) -> bool:
        return (msg == reaction.message
                and emoji == reaction.emoji and user != BOT.user
                and eval(cond, globals(), locals()|{"ctx": ctx, "emoji": emoji}))
    try:
      reaction, user = await BOT.wait_for("reaction_add",
                                           check = check, timeout = timeout)
    except asyncio.TimeoutError: pass
    except Exception as e: raise e

    else:
        try: await eval(method, globals(), locals())
        except Exception as e: raise e
        else:

            if recursive !=0:
                await reactech(msg, emoji, False, recursive-1,
                               timeout, cond, method, *args)


async def rt_ok(ctx, txt: str) -> None:
    await reactech(ctx, "✅", True, -1, None, "True", "rt_ok_(msg,user,recursive,args)", txt)
async def rt_ok_(msg: DSC.Message, user: DSC.User, recursive: int, txt: str) -> None:
    if recursive == -1:
        await msg.channel.send(*txt)
    else:
        await user.send(*txt)



##########################################################################
# ROLL
##########################################################################



@BOT.command(name = "roll", aliases = ["dice", "calculate", "calc", "c", "d", "r", "eval"])
async def roll(ctx: CTX, *, txt: str):
    allow = "0123456789()+-*/%dtsefxa^hmovl,."
    txt = "".join([i for i in str(txt) if i in allow])
    try: txt = dice.roll(txt)
    except Exception as e:
        await asyncio.gather(reactech(ctx, "⁉️", True, -1, 3600,
                                      "True", "user.send(*args)", e),
                             reactech(ctx, "🆘", True, -1, None, "True",
                                      "user.send('Dice notation: https://pypi.org/project/dice/')"))
    else:
        await ctx.send(txt)
        return txt


async def msg_dice(msg: DSC.message) -> None:
    content = msg.content
    if len(content) > 50: return
    allow = "0123456789()+-*/%dtsefxa^hmovl,."
    txt = "".join([i for i in str(content) if i in allow])
    if len(txt) < 0.5*len(content.replace(" ", "")): return
    try: txt = dice.roll(txt)
    except: pass
    else: await reactech(msg, "🎲", True, 0, 300, "True", f"msg.channel.send('{txt}')")



##########################################################################
# PATH
##########################################################################



def check_path_entry(channel: DSC.channel) -> bool:
    cid, gid = str(channel.id), str(channel.guild.id)
    if cid in SERVERS[gid]["Paths"]:
        rid = SERVERS[gid]["Paths"][cid]
        if dsc_type(rid) == "id":
            role = channel.guild.get_role(int(rid))
            if role is not None and role in channel.overwrites:
                return True
    return False


async def fix_path_entry(channel: DSC.channel) -> list:
    if check_path_entry(channel): return []
    cid,gid,cnm = str(channel.id), str(channel.guild.id), channel.name
    if (dsc_type(SERVERS[gid]["Paths"].get(cid)) != "id" or
            channel.guild.get_role(int(SERVERS[gid]["Paths"].get(cid))) is None):
        role = [i for i in channel.guild.roles if i.name == cnm]
        if role: role = role[0]
        else:
            role= await channel.guild.create_role(name = cnm,
                                                  reason = f"Path role for channel {cnm}")
        SERVERS[gid]["Paths"][cid] = str(role.id)
    role = channel.guild.get_role(int(SERVERS[gid]["Paths"][cid]))
    if role not in channel.overwrites:
        overwrites = channel.overwrites
        overwrites[role] = DSC.PermissionOverwrite(view_channel=True,
                                                    read_messages=True,
                                                    send_messages=True,
                                                    read_message_history=True)
        await channel.edit(overwrites = overwrites)
    return [channel]


def is_path(fro: DSC.channel, to: DSC.channel) -> bool:
    return fro.guild.get_role(int(SERVERS[str(fro.guild.id)]["Paths"][str(fro.id)])) in to.overwrites


async def create_path(fro: DSC.channel, to: DSC.channel) -> tuple:
    role = fro.guild.get_role(int(SERVERS[str(fro.guild.id)]["Paths"][str(fro.id)]))
    role_see = None #dsc_obj(None, "role")
    role_hear = None #dsc_obj(None, "role")
    role_skip = None #dsc_obj(None, "role")
    can_see_history = True # Decide if can see history of adjacent channels
    overwrites = to.overwrites
    overwrites[to.guild.default_role] = DSC.PermissionOverwrite(view_channel=False)
    overwrites[role] = DSC.PermissionOverwrite(view_channel=True,
                                               read_messages=True,
                                               send_messages=True,
                                               read_message_history=can_see_history)
    if role_see is not None:
        overwrites[role_see] = DSC.PermissionOverwrite(view_channel=True)
    if role_hear is not None:
        overwrites[role_hear] = DSC.PermissionOverwrite(view_channel=True,
                                                        read_messages=True,
                                                        read_message_history=True)
    if role_skip is not None:
        overwrites[role_skip] = DSC.PermissionOverwrite(view_channel=True,
                                                        read_messages=True,
                                                        read_message_history=True,
                                                        send_messages=True)
    await to.edit(overwrites = overwrites)
    return (fro, to)


async def delete_path(fro: DSC.channel, to: DSC.channel) -> tuple:
    role= fro.guild.get_role(int(SERVERS[str(fro.guild.id)]["Paths"][str(fro.id)]))
    await to.set_permissions(role, overwrite = None)
    return (fro, to)


def is_path_void(channel: DSC.channel) -> bool:
    g = channel.guild
    if check_path_entry(channel):
        role = g.get_role(int(SERVERS[str(g.id)]["Paths"][str(channel.id)]))
        for key, value in SERVERS[str(channel.guild.id)]["Paths"].items():
            if check_path_entry(g.get_channel(int(key))) and int(key) != channel.id:
                if (g.get_role(int(value)) in channel.overwrites
                    or role in (g.get_channel(int(key))).overwrites):
                    return False
        return True
    return False



async def destroy_path(channel: DSC.channel) -> list:
    cid, gid = str(channel.id), str(channel.guild.id)
    role_see = None #dsc_obj(None, "role")
    role_hear = None #dsc_obj(None, "role")
    role_skip = None #dsc_obj(None, "role")

    none_ = DSC.PermissionOverwrite()
    overwrites = channel.overwrites
    overwrites[channel.guild.default_role] = none_
    if role_see is not None:
        overwrites[role_see] = none_
    if role_hear is not None:
        overwrites[role_hear] = none_
    if role_skip is not None:
        overwrites[role_skip] = none_

    if cid in SERVERS[gid]["Paths"]:
        if dsc_type(SERVERS[gid]["Paths"].get(cid)) == "id":
            role = (channel.guild.get_role(int(SERVERS[gid]["Paths"][cid])))
            if role is not None:
               await role.delete(reason = f"Destroyed path around {channel.name}: pair ({channel.id}:{role.id})")
        await channel.edit(overwrites = overwrites)
        del SERVERS[gid]["Paths"][cid]
        return [channel]
    return []


@CMDS.has_permissions(manage_channels = True)
@BOT.command(name = "path", aliases = ["pathway", "road", "roadway", "journey", "travel"])
async def path(ctx: CTX, *args: str) -> dict:
    modes={"To": ["to", "towards", "branch", ">", "->"],
           "From": ["fro", "from", "origin", "root", "<", "<-"],
           "Both": ["both", "link", "create", "carve", "pair", "<>", "><"],
           "Delete": ["del", "delete", "undo", "unlink", "collapse", "bar", "remove", "unpair"],
           "Destroy": ["destroy", "unpath", "kill", "x", "void"]}
    mode, check_unpath = None, []
    end = {"Created": [],
           "Deleted": [],
           "Fixed": [],
           "Destroyed": []}
    for arg in args:

        if dsc_toid(arg):
            arg = dsc_toid(arg)
        if dsc_type(arg) == "id":
            channel= dsc_obj(arg, "channel", ctx)
        else:
            channel = None

        if isinstance(arg, str) and any([True if arg.lower() in i else False for i in modes.values()]):
             mode = [i for i, j in modes.items() if arg.lower() in j][0]

        elif channel is not None:
            if mode is None:
                await reactech(ctx, "⁉️", True, -1, 3600, "True",
                               f"user.send('Must select a Mode (direction) before specifying channels.')")
                return
            if len(ctx.guild.roles) > 248:
                await reactech(ctx, "‼️", True, 0, 3600, "True",
                               f"msg.channel.send('Discord does not allow for anymore roles to be created. \
                               \u005cnReduce the number of roles in your server or destroy obsolete path channels to free space. \
                               \u005cnExecution of path command was stopped on argument {channel.mention}.')")
                return

            bits = {"To": "10", "From": "01", "Both": "11", "Delete": "00"}
            if mode in bits and channel != ctx.channel:
                bits = bits[mode]

                end["Fixed"] += await fix_path_entry(ctx.channel)
                end["Fixed"] += await fix_path_entry(channel)

                if bits[0]=="1" and not is_path(ctx.channel, channel):
                    end["Created"].append(await create_path(ctx.channel, channel))
                if bits[0]=="0" and is_path(ctx.channel, channel):
                    end["Deleted"].append(await delete_path(ctx.channel, channel))

                if bits[1]=="1" and not is_path(channel, ctx.channel):
                    end["Created"].append(await create_path(channel, ctx.channel))
                if bits[1]=="0" and is_path(channel, ctx.channel):
                    end["Deleted"].append(await delete_path(channel, ctx.channel))

                if mode == "Delete": check_unpath += [channel]
            elif mode == "Destroy": end["Destroyed"] += await destroy_path(channel)

        else:
            await reactech(ctx, "❓", True, -1, 3600, "True",
                           f"user.send('Argument <{arg}> could not be resolved.')")
            raise ValueError(f"{arg} could not be resolved")

    for i,j in end["Deleted"]:
        if i not in check_unpath:
            check_unpath.append(i)
        if j not in check_unpath:
            check_unpath.append(j)

    for i in check_unpath:
        if is_path_void(i):
            end["Destroyed"] += await destroy_path(i)

    for key, value in end.items():
        for i in range(len(value)):
            if isinstance(value[i],tuple):
                end[key][i] = value[i][0].mention + "  ->  " + value[i][1].mention
            else:
                end[key][i] = value[i].mention
        end[key] = " ,  ".join(end[key])

    if mode is None:
        await reactech(ctx, "⁉️", True, -1, 3600, "True",
                               f"user.send('No mode(s) specified.')")
    elif channel is None:
        await reactech(ctx, "⁉️", True, -1, 3600, "True",
                               f"user.send('No channel(s) specified.')")
    elif any([i for i in end.values()]):
        exit = "\n".join([key + " : " + value for key, value in end.items() if value])
        tasks = [rt_ok(ctx, exit)]
        if len(ctx.guild.roles) > 200:
            tasks += [reactech(ctx, "⚠️", True, 0, 3600, "True",
                               f"msg.channel.send('Warning : maximum role limit nearly reached : {len(ctx.guild.roles)}/250. \
                               \u005cnConsider optimizing number of roles or Path channels.')")]
        await asyncio.gather(*tasks)
    else:
        await rt_ok(ctx, "Nothing changed...")
    return end



async def msg_path(msg: DSC.message) -> None:
    if msg.guild is None: return
    gid, cid = str(msg.guild.id), str(msg.channel.id)
    if gid not in SERVERS: return
    if cid not in SERVERS[gid]["Paths"]: return
    if not check_path_entry(msg.channel): return
    role = msg.guild.get_role(int(SERVERS[gid]["Paths"][cid]))
    if msg.author.get_role(role.id) is not None: return

    rem_roles, origin = [], "None"
    for key, value in SERVERS[gid]["Paths"].items():
        if check_path_entry(msg.guild.get_channel(int(key))):
            if msg.author.get_role(int(value)) is not None:
                rem_roles.append(msg.guild.get_role(int(value)))
                origin = msg.guild.get_channel(int(key)).mention

    await msg.author.add_roles(role)
    if role in rem_roles:
        rem_roles.remove(role)
    await msg.author.remove_roles(*rem_roles)
    await reactech(msg, "🗺️", True, -1, None, "True",
                               f"user.send('User {msg.author.name} went from {origin} to {msg.channel.mention}')")



##########################################################################
# SYSTEM
##########################################################################



@BOT.command(name = "ping", aliases = ["test", "!", "latency"])
async def ping(ctx: CTX = None) -> int:
    if ctx is not None:
        await ctx.send("pong! " + str(int(BOT.latency*1000)) + "ms")
    return BOT.latency


@BOT.command(name = "echo", aliases = ['console', 'send', 'exec', 'command',' cmd', 'execute'])
@CMDS.is_owner()
async def echo(ctx: CTX, *, txt: str) -> None:
  print(txt)
  # Eval Expression OR run code
  try: await eval(txt)
  except SyntaxError:
    try: exec(txt)
    except Exception as e: raise e
  except Exception as e: print(e)


@BOT.command(name = "activity", aliases = ["status"])
@CMDS.is_owner()
async def activity(ctx: CTX, action: str = 'watch', *, txt: str = str(len(BOT.guilds)+1) + ' servers') -> DSC.Activity:
  if 'https://twitch.tv/' in action: url = action
  else : url = "https://twitch.tv/"
  activity = None
  if any(i in action for i in ['gam', 'play']) : activity = DSC.Game(name = txt)
  if any(i in action for i in ['stream', 'twitch']) : activity = DSC.Streaming(name = txt, url = url)
  if any(i in action for i in ['listen']) : activity = DSC.Activity(type = DSC.ActivityType.listening, name = txt)
  if any(i in action for i in ['watch', 'video']) : activity = DSC.Activity(type = DSC.ActivityType.watching, name = txt)
  await BOT.change_presence(activity = activity)
  if ctx: await rt_ok(ctx, activity)
  return activity


@BOT.command(name = "kill", aliases = ["killtask", "end", "endtask", "destroy", "shutdown"])
@CMDS.is_owner()
async def kill(ctx: CTX = None) -> None:
  """Disconnects the bot"""
  print("\nDisconnecting")
  await BOT.close()



##########################################################################
# EVENTS
##########################################################################



@BOT.event
async def on_message(msg: DSC.message) -> None:
    await BOT.process_commands(msg)
    if msg.content.startswith(PREFIX): return
    if msg.author == BOT.user: return

    await msg_dice(msg)
    await msg_path(msg)



##########################################################################
# ERRORS
##########################################################################



@BOT.event
async def on_command_error(ctx: CTX, error):
    a= ("⛔","This command requires a role or permission you do not posess.\nIf you think this is a mistake, contact server admins.")
    b= ("📛","This command can only be opperated by a bot admin.\nIf you think this is a mistake, contact the developer(s).")
    c= ("🚫","This command cannot be utilized in the current context.\nRefer to the Error name for more precision.")
    d= ("⁉️","This command was wrongfully formatted or does not exist.\nConsult proper usage using the HELP command.")
    e= ("❓","A required Discord Object could not be resolved.\nMake sure your object names or IDs are correct before trying again.")
    f= ("‼️","The bot could not execute this command.\nMake sure to setup the application properly.")
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
            print(type_,i)
            await reactech(ctx, i[0], True, -1, 3600, "True", "user.send(*args)", i[1])
            return
    traceback.print_exception(type(error), error, error.__traceback__)



##########################################################################
# RUN
##########################################################################



@BOT.event
async def on_connect():
  print("\nConnecting\n")
  del_env("TOKEN")
  del_i()


@BOT.event
async def on_ready():
  print("\nConnected\n\n")
  await activity(None)


@BOT.event
async def on_disconnect():
  print("\nDisconnected")


nest_asyncio.apply()
BOT.run(TOKEN, reconnect = True)