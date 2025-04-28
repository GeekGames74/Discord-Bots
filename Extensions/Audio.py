"""
Main handler for voice channel and audio interaction.
"""



##################################################
# IMPORTS
##################################################



import discord as DSC
from discord.ext import commands as CMDS
from discord.ext.commands.bot import Bot
from discord.ext.commands.context import Context as CTX

import subprocess
from os import listdir, replace
from os.path import getmtime, isfile
from asyncio import gather, sleep

from Modules.reactech import Reactech
from Modules.discord_utils import DscConverter
from Modules.data import data_JSON, checkfile, write_JSON
from Modules.basic import mixmatch, plural, correspond, path_from_root


async def setup(bot: Bot):
    await bot.add_cog(Voice(bot))
    await bot.add_cog(Sounds(bot))


##################################################
# VOICE
##################################################



MAX_VOLUME = 200


def get_audio(bot: Bot = None, ctx: CTX = None, key: str = None, default = None) -> any:
    try: data = data_JSON("Data/audio.json")
    except FileNotFoundError: data = {}
    if bot is None and not ctx: return data
    elif isinstance(bot, dict): data = bot
    else: data = data.get(str(bot.user.id), {})
    if ctx is None: return data
    elif isinstance(ctx, dict): data = ctx
    else: data = data.get(str(ctx.guild.id), {})
    if key is None: return data
    return data.get(key, default)


def set_audio(data: dict = None, bot: Bot = None, ctx: CTX = None, key: str= None, value: any = None) -> dict:
    if not data: data = get_audio()
    if bot:
        if str(bot.user.id) not in data:
            data[str(bot.user.id)] = {}
        if ctx:
            if str(ctx.guild.id) not in data[str(bot.user.id)]:
                data[str(bot.user.id)][str(ctx.guild.id)] = {}
            if key:
                data[str(bot.user.id)][str(ctx.guild.id)][key] = value
    write_JSON("Data/audio.json", data)
    return data


class Voice(CMDS.Cog):
    """Voice interaction."""
    def __init__(self, bot: Bot):
        self.bot = bot
        self.Reactech = Reactech(bot)
        self.DscConverter = DscConverter(bot)
    

    async def cog_unload(self):
        await self.bot.remove_cog("Sounds")


    @CMDS.command(name = "join", aliases = mixmatch(["join", "connect", ""],
            ["", "vc", "voice", "vchannel", "voicechannel"], remove="join"))
    async def join(self, ctx: CTX, channel: str = None, component: bool = False) -> bool:
        """Join the voice channel you are currently in (or the one specified)."""
        if ctx.guild is None:
            await self.Reactech.reactech_user(ctx,
                "🚫", "Command only works in servers.")
            return False
        
        if channel is None:
            if ctx.author.voice is None:
                await self.Reactech.reactech_user(ctx,
                    "⁉️", "No channel specified to join.")
                return False
            channel = ctx.author.voice.channel
        
        else: # resolve given channel
            try: channel = self.DscConverter.convertobj(channel, "voice", ctx)
            except TypeError: channel = None
            if channel is None:
                await self.Reactech.reactech_user(ctx, "❓",
                    "Could not find specified channel.")
                return False
            if not isinstance(channel, DSC.VoiceChannel):
                await self.Reactech.reactech_user(ctx, "🚫",
                    "The channel provided is not a voice channel.")
                return False

        if ctx.voice_client is not None:
            if ctx.voice_client.is_connected():
                if not component: await self.Reactech.reactech_channel(ctx,
                    "ℹ️", "Bot is already in a voice channel on this server.")
                return True
        
        try:
            await channel.connect()
            if component: return True
            await self.Reactech.reactech_valid(ctx,
                f"Joined voice channel {channel.mention}.")
        except DSC.Forbidden:
            await self.Reactech.reactech_user(ctx, "‼️",
                "Bot does not have the permission to join.")
        else: return True
        return False


    @CMDS.command(name = "leave", aliases = mixmatch(["quit", "leave", "disconnect", "dc"],
            ["", "vc", "voice", "vchannel", "voicechannel"], remove="leave"))
    async def leave(self, ctx: CTX) -> None:
        """Leave the voice channel the bot is in."""
        if ctx.guild is None:
            return await self.Reactech.reactech_user(ctx, "🚫",
                "Command only works in servers.")
        
        vc = ctx.voice_client
        if vc is None or not vc.is_connected():
            return await self.Reactech.reactech_channel(ctx, "ℹ️",
                "Bot is not connected to a voice channel.")
        
        channel = vc.channel
        await vc.disconnect()
        await self.Reactech.reactech_valid(ctx,
            f"Left voice channel {channel.mention}.")
    

    @CMDS.command(name = "volume", aliases = mixmatch(["volume", "vol"],
            ["", "vc", "voice", "vchannel", "voicechannel"], remove="volume"))
    async def volume(self, ctx: CTX, txt: str = None) -> None:
        """Count all voice channels the bot is currently connected to."""
        if ctx.guild is None:
            return await self.Reactech.reactech_user(ctx, "🚫",
                "Command only works in servers.")
        
        volume = get_audio(self.bot, ctx, "volume", 100)
        if txt is None:
            return await ctx.send("Volume is currently at " + str(volume) + "%")
        
        relative = None
        txt = txt.removeprefix("=")
        if txt.startswith("+"): relative = 1
        elif txt.startswith("-"): relative = -1
        if relative is not None:
            if len(txt) == 1:
                await self.Reactech.reactech_user(ctx, "⁉️",
                    "Volume was not correctly formatted.")
            txt = txt[1:]
        if not txt or not txt.isdigit():
            return await self.Reactech.reactech_user(ctx, "⁉️",
                "Volume was not correctly formatted.")
        nb = int(txt) ; msg = ""

        if relative is None: volume = nb
        else: volume = volume + nb*relative
        if volume < 0:
            msg = " (minimum volume)"
            volume = 0
        elif volume > MAX_VOLUME:
            msg = " (maximum volume)"
            volume = MAX_VOLUME
        
        set_audio(None, self.bot, ctx, "volume", volume)
        if ctx.voice_client:
            vc = ctx.voice_client
            if vc and vc.is_connected() and vc.source:
                vc.source.volume = volume/100
        msg = f"Volume set to {volume}%{msg}."
        await self.Reactech.reactech_valid(ctx, msg)


    @CMDS.command(name = "voicechannels", aliases = mixmatch(["list", ""],
            ["vcs", "vchannels", "voicechannels"], remove="voicechannels")
            + mixmatch("list", ["vc", "voice", "vchannel", "voicechannel"]))
    @CMDS.is_owner()
    async def voicechannels(self, ctx: CTX, cmd: str = None) -> None:
        """Count all voice channels the bot is currently connected to."""
        vcs = self.bot.voice_clients; gatherer = []
        
        if cmd is None or cmd.lower() in ["l", "ls", "list", "c", "count"]:
            msg = ""
            if len(vcs) == 0:
                return await ctx.send("The bot is not connected to any voice channels.")
            playing = [vc for vc in vcs if vc.is_playing()]
            msg += f"The bot is connected to `{len(vcs)}` voice channel{plural(len(vcs))}."
            if playing: msg += f"\n`{len(vcs)}` of those {plural(vcs, _1='is', _p='are')} actively playing."
            if cmd is not None and cmd.lower() in ["l", "ls", "list"]:
                for vc in vcs:
                    playmsg = "🔊" if vc.is_playing() else "🔇"
                    if ctx.guild and ctx.guild == vc.guild:
                        msg += f"\n- {vc.channel.mention} in '{vc.guild.name}' " + playmsg
                    elif not ctx.guild and vc.guild.get_member(ctx.author.id):
                        msg += f"\n- '#{vc.channel.name}' in '{vc.guild.name}' " + playmsg
                    else:
                        msg += f"\n- #{vc.channel.id} in {vc.guild.id} " + playmsg
            return await ctx.send(msg)

        CMD_MUTE = ["m", "mute", "p", "pause"]
        CMD_STOP = ["s", "stop", "end"]
        CMD_QUIT = ["q", "quit", "dc", "disconnect", "leave"]
        if cmd.lower() in CMD_MUTE + CMD_STOP + CMD_QUIT:
            success = 0; errors = {}
            for vc in vcs:
                try:
                    if cmd.lower() in CMD_MUTE:
                        vc.pause()
                        txt = "Paused"
                    elif cmd.lower() in CMD_STOP:
                        vc.stop()
                        txt = "Stopped"
                    elif cmd.lower() in CMD_QUIT:
                        await vc.disconnect()
                        txt = "Disconnected"
                    success += 1
                except Exception as e:
                    errors[vc] = e
            gatherer.append(self.Reactech.reactech_valid(
                ctx, f"{txt} `{success}` voiceclient{plural(success)}."))
            
            if len(errors) > 0:
                msg = f"Raised `{len(errors)}` error{plural(len(errors))}."
                for vc,e in errors.items():
                    msg += f"\n- #{vc.channel.id}: `{e.__class__.__name__}`: {e}"
                gatherer.append(self.Reactech.reactech_user(ctx, "❌", msg))
            
            await gather(*gatherer)
            return
        
        await self.Reactech.reactech_user(ctx, "⁉️",
                f"Invalid or unknown command argument `{cmd}`.")



##################################################
# Sounds
##################################################



AUDIO_EXTS = ["mp3", "m4a", "wav", "ogg", "flac", "opus", "webm", "aac"]
RELATIVE_PATH = "Resources/Assets/Sounds/"
TARGET_VOLUME = -40 # LUFS


def format_filename(input: str) -> (str, str):
    """Format the filename for soundboard use."""
    splitted = input.split(".")
    ext = splitted[1] if len(splitted) > 1 else None
    name = "".join(c for c in splitted[0] if c.isalnum())
    return name.lower(), ext


def normalize_sounds() -> None:
    """Normalize the audio files to a target volume."""
    try: checkfile(RELATIVE_PATH + "info.json")
    except FileNotFoundError:
        write_JSON(RELATIVE_PATH + "info.json", {})
    info = data_JSON(RELATIVE_PATH + "info.json")
    for file in listdir(RELATIVE_PATH):
        filename, ext = format_filename(file)
        if ext in AUDIO_EXTS:
            path = path_from_root(RELATIVE_PATH + file)
            if filename not in info:
                info[filename] = {}
            if "mod_time" not in info[filename] or \
                    info[filename]["mod_time"] < getmtime(path):
                temp_path = path_from_root(RELATIVE_PATH + filename + "._temp_." + ext)
                if isfile(temp_path): continue
                command = [
                    "ffmpeg", "-i", path, "-filter:a",
                    f"loudnorm=I={TARGET_VOLUME}:TP=-1.5:LRA=11",
                    "-ar", "48000", "-y", temp_path
                ]
                subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                replace(temp_path, path)
                info[filename]["mod_time"] = getmtime(path) + 1
                print(f"Sound: normalized '{file}'")
    write_JSON(RELATIVE_PATH + "info.json", info)


class Sounds(CMDS.Cog):
    """Soundboard and preset music."""
    def __init__(self, bot: Bot):
        self.bot = bot
        self.Reactech = Reactech(bot)
        normalize_sounds()
        if not bot.get_cog("Voice"):
            bot.add_cog(Voice(bot))
    

    @CMDS.command(name = "play", aliases = mixmatch(["p", "play", "start", "resume", ""],
            ["", "sound", "sounds", "audio"], remove="play"))
    async def play(self, ctx: CTX, msg: str = None) -> None:
        """Start or resume a sound from the bot."""
        result = await self.bot.get_cog("Voice").join(ctx, None, True)
        if result is False: return
        
        vc = ctx.voice_client
        if vc.is_playing() and msg is None:
            return await self.Reactech.reactech_channel(ctx, "ℹ️",
                "Bot is already playing a sound.")
        
        if vc.is_paused() and msg is None:
            vc.resume()
            try: source = f"`{vc.playing}`"
            except AttributeError: source = "audio"
            return await self.Reactech.reactech_valid(ctx,
                f"Resumed {source} in {vc.channel.mention}.")
        
        if msg is None:
            return await self.Reactech.reactech_user(ctx, "⁉️",
                "No sound filename specified.")
        
        name = format_filename(msg)[0]
        try:
            data = data_JSON(RELATIVE_PATH + "info.json")
            for key, value in data.items():
                if name == key or name in value.get("aliases", []):
                    name = key
                    break
        except FileNotFoundError: pass

        files = [] ; exts = []
        for i in listdir(path_from_root(RELATIVE_PATH)):
            splitted = format_filename(i)
            files.append(splitted[0])
            exts.append(splitted[1])
        final = correspond(name, files)
        if final is None:
            return await self.Reactech.reactech_user(ctx,
                "❓", f"Could not find sound file `{msg}`.")
        
        file = final + "." + exts[files.index(final)]
        path = checkfile(RELATIVE_PATH + file)
        volume = get_audio(self.bot, ctx, "volume", 100)
        source = DSC.FFmpegPCMAudio(path)
        source = DSC.PCMVolumeTransformer(source, volume/100)
        if vc.is_playing(): vc.stop()
        vc.play(source, after = lambda x: self.tryloop(ctx, vc))
        vc.playing = file
        await self.Reactech.reactech_valid(ctx,
            f"Playing `{file}` in {vc.channel.mention}.")


    @CMDS.command(name = "pause", aliases = mixmatch(["s", "stop", "pause", "mute", "fade", "fadeout"],
            ["", "sound", "sounds", "audio"], remove=["pause", "sounds"]))
    async def pause(self, ctx: CTX, time: int = 0) -> None:
        """
        Stop the sound being played.
        Use /pause <time> to create a gradient fadeout that lasts <time> seconds
        """
        if ctx.guild is None:
            return await self.Reactech.reactech_user(ctx, "🚫",
                "Command only works in servers.")
        
        vc = ctx.voice_client
        if vc is None or not vc.is_connected():
            return await self.Reactech.reactech_channel(ctx, "🚫",
                "Bot is not connected to a voice channel.")
        
        if not vc.is_playing():
            return await self.Reactech.reactech_user(ctx, "ℹ️",
                f"No sound is currently playing in {vc.channel.mention}.")
        
        if time < 0 or time > 60:
            return await self.Reactech.reactech_channel(ctx, "🚫",
                "Fadeout can last between 0 and 60 seconds.")

        volume = get_audio(self.bot, ctx, "volume", 100)/100
        if time:
            for i in range(1, 26):
                vc.source.volume = volume - i*volume/25
                await sleep(time/25)

        vc.pause()
        vc.source.volume = volume
        try: source = f"`{vc.playing}`"
        except AttributeError: source = "audio"
        await self.Reactech.reactech_valid(ctx,
            f"Paused {source} in {vc.channel.mention}.")


    @CMDS.command(name = "loop", aliases = mixmatch(["loop", "repeat"],
            ["", "sound", "sounds", "audio"], remove="loop"))
    async def loop(self, ctx: CTX) -> None:
        """Toogle audio looping on current/next source."""
        looping = not get_audio(self.bot, ctx, "looping", False)
        set_audio(None, self.bot, ctx, "looping", looping)
        if looping: await self.Reactech.reactech_channel(ctx, "🔁", "Looping enabled.")
        else: await self.Reactech.reactech_channel(ctx, "⏯️", "Looping disabled.")


    def tryloop(self, ctx: CTX, vc: DSC.VoiceProtocol, error: Exception = None) -> None:
        try:
            if error: raise error
            if not get_audio(self.bot, ctx, "looping", False): return
            volume = get_audio(self.bot, ctx, "volume", 100)
            path = checkfile(RELATIVE_PATH + vc.playing)
            source = DSC.PCMVolumeTransformer(DSC.FFmpegPCMAudio(path), volume/100)
            vc.play(source, after = lambda x: self.tryloop(ctx, vc))
        except Exception as e:
            if isinstance(e, DSC.ClientException) and vc.source: return
            print(f"Loop error: {e.__class__.__name__}: {e}")