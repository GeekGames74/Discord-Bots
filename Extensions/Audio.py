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
from Modules.discord_utils import DscConverter, find_vc
from Modules.data import data, path_from_root
from Modules.basic import mixmatch, plural, correspond, yes_no


async def setup(bot: Bot):
    await bot.add_cog(Voice(bot))
    await bot.add_cog(Sounds(bot))


##################################################
# VOICE
##################################################



MAX_VOLUME = 200


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
    async def join(self, ctx: CTX, target: str = None) -> DSC.VoiceClient:
        """Join the voice channel you are currently in (or the one specified)."""
        if isinstance(target, DSC.VoiceChannel): channel = target
        else:
            channel = find_vc(self.DscConverter, ctx, "connect", target, "move_members")
            if channel and ctx.guild and ctx.guild != channel.guild: channel = None

            if channel is None: return await self.Reactech.reactech_user(
                ctx, "❓", "Could not find a voice channel to connect to.")
            if channel is False: return await self.Reactech.reactech_user(
                ctx, "⛔", "You do not have permission to connect the bot to this channel.")

        vc = channel.guild.voice_client
        if vc and vc.is_connected():
            if vc.channel == channel:
                if not isinstance(target, DSC.VoiceChannel):
                    await self.Reactech.reactech_user(ctx, "ℹ️",
                        "Bot is already connected to this channel.")
                return vc
            
            output = await self.leave(ctx, vc.guild)
            if not output: return vc

        try: await channel.connect()
        except DSC.Forbidden:
            if isinstance(target, DSC.VoiceChannel): return None
            return await self.Reactech.reactech_user(ctx, "‼️",
                "Bot does not have the permission to join.")
        
        if isinstance(target, DSC.VoiceChannel):
            return channel.guild.voice_client
        await self.Reactech.reactech_valid(ctx,
            f"Joined voice channel {channel.mention}.")


    @CMDS.command(name = "leave", aliases = mixmatch(["quit", "leave", "disconnect", "dc"],
            ["", "vc", "voice", "vchannel", "voicechannel"], remove="leave"))
    async def leave(self, ctx: CTX, target: str = None) -> bool:
        """Leave the voice channel the bot is in."""
        if isinstance(target, DSC.Guild): guild = target
        if ctx.guild: guild = ctx.guild
        else:
            channel = find_vc(self.DscConverter, ctx, "view_channel", target, "move_members")
            if channel is None: return await self.Reactech.reactech_user(
                ctx, "❓", "Could not find a voice channel to leave.")
            if channel is False: return await self.Reactech.reactech_user(
                ctx, "⛔", "You do not have permission to move the bot in this server.")
            guild = channel.guild
        
        vc = guild.voice_client
        if vc is not None and vc.is_connected():
            if vc.channel.permissions_for(guild.get_member(ctx.author.id)).view_channel:
                if vc.is_playing(): 
                    if not vc.channel.permissions_for(vc.guild.get_member(ctx.author.id)).move_members:
                        await self.Reactech.reactech_channel(ctx, "⛔",
                            "You do not have permission to move the bot in this server.")
                        return False
                    vc.stop()

                await vc.disconnect(force=True)
                if isinstance(target, DSC.Guild): return True
                return await self.Reactech.reactech_valid(ctx,
                    f"Left voice channel {vc.channel.mention}.")
        
            await self.Reactech.reactech_user(ctx, "❓",
                "Could not find a voice channel to leave.")
            return False
        
        if isinstance(target, DSC.Guild): return True
        await self.Reactech.reactech_user(ctx, "ℹ️",
            "Bot is not connected on this server.")
    

    @CMDS.command(name = "volume", aliases = mixmatch(["volume", "vol"],
            ["", "vc", "voice", "vchannel", "voicechannel"], remove="volume"))
    async def volume(self, ctx: CTX, txt: str = None) -> None:
        """Count all voice channels the bot is currently connected to."""
        if not ctx.guild:
            channel = find_vc(self.DscConverter, ctx)
            if channel is None: return await self.Reactech.reactech_user(
                ctx, "❓", "Could not find a server to apply command to.")
            guild = channel.guild
        else: guild = ctx.guild
        
        volume = data("Data/servers.json", 100, str(guild.id), str(self.bot.user.id), "volume",
            filenotfound = None, keynotfound = None)
        if txt is None: return await ctx.reply(
            "Volume is currently at " + str(volume) + "%",
            mention_author = False)
        
        if not guild.get_member(ctx.author.id).guild_permissions.mute_members:
            return await self.Reactech.reactech_user(ctx, "⛔",
                "You do not have permission to change bot volume in this server.")

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
        
        data("Data/servers.json", volume, str(guild.id), str(self.bot.user.id), "volume", read_only = False)
        if guild.voice_client:
            vc = guild.voice_client
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
                        vc.playing = None
                        txt = "Stopped"
                    elif cmd.lower() in CMD_QUIT:
                        vc.stop()
                        vc.playing = None
                        await vc.disconnect(force=True)
                        txt = "Disconnected"
                    success += 1
                except Exception as e:
                    errors[vc] = e
            if vcs: gatherer.append(self.Reactech.reactech_valid(
                ctx, f"{txt} `{success}` voiceclient{plural(success)}."))
            else: return await ctx.send("The bot is not connected to any voice channels.")

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
    audio = data("Data/audio.json", {}, filenotfound = None)
    for file in listdir(RELATIVE_PATH):
        if "._temp_." in file: continue
        filename, ext = format_filename(file)
        if ext not in AUDIO_EXTS: continue
        path = path_from_root(RELATIVE_PATH + file)
        if filename not in audio:
            audio[filename] = {}
        if "mod_time" not in audio[filename] or \
                audio[filename]["mod_time"] < getmtime(path):
            temp_path = path_from_root(RELATIVE_PATH + filename + "._temp_." + ext)
            if isfile(temp_path): continue
            command = [
                "ffmpeg", "-i", path, "-filter:a",
                f"loudnorm=I={TARGET_VOLUME}:TP=-1.5:LRA=11",
                "-ar", "48000", "-y", temp_path
            ]
            subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            replace(temp_path, path)
            audio[filename]["mod_time"] = getmtime(path) + 1
            print(f"Sound: normalized '{file}'")
    data("Data/audio.json", audio, read_only = False)


class Sounds(CMDS.Cog):
    """Soundboard and preset music."""
    def __init__(self, bot: Bot):
        self.bot = bot
        self.Reactech = Reactech(bot)
        self.DscConverter = DscConverter(bot)
        normalize_sounds()
        if not bot.get_cog("Voice"):
            bot.add_cog(Voice(bot))
    

    @CMDS.command(name = "play", aliases = mixmatch(["p", "play", "start", "resume", ""],
            ["", "sound", "sounds", "audio"], remove="play"))
    async def play(self, ctx: CTX, msg: str = None) -> None:
        """Start or resume a sound from the bot."""
        if msg is None:
            channel = find_vc(self.DscConverter, ctx, "connect")
            if channel and ctx.guild and ctx.guild != channel.guild: channel = None

            if channel is None: return await self.Reactech.reactech_user(
                ctx, "❓", "Could not find a voicechannel to query.")
            if channel is False: return await self.Reactech.reactech_user(
                ctx, "⛔", "You do not have permission to query this voicechannel.")
            
            vc = channel.guild.voice_client
            if not vc or not vc.is_connected() or not (vc.is_playing() or vc.is_paused()):
                return await ctx.reply("Bot is not playing in this server.",
                        mention_author = False)
            if vc.is_playing(): return await ctx.reply(
                f"`{vc.playing}` is playing in {vc.channel.mention}.", mention_author = False)
            
            perm = vc.channel.permissions_for(vc.guild.get_member(ctx.author.id))
            if vc.is_paused() and perm.use_soundboard:
                vc.resume()
                return await self.Reactech.reactech_valid(
                    ctx, f"`{vc.playing}` resumed in {vc.channel.mention}.")
            else: return await ctx.reply(
                f"`{vc.playing}` is paused in {vc.channel.mention}.", mention_author = False)
        
        channel = find_vc(self.DscConverter, ctx, "use_soundboard", None, "use_external_sounds")
        if channel and ctx.guild and ctx.guild != channel.guild: channel = None

        if channel is None: return await self.Reactech.reactech_user(
            ctx, "❓", "Could not find a voicechannel to play sound in.")
        if channel is False: return await self.Reactech.reactech_user(
            ctx, "⛔", "You do not have permission to play sounds in this voicechannel.")
        
        vc = channel.guild.voice_client
        if not vc or not vc.is_connected() or \
            (vc.is_connected() and vc.channel != channel):
                vc = await self.bot.get_cog("Voice").join(ctx, channel)
                if not vc: return

        name = format_filename(msg)[0]
        try:
            audio = data("Data/audio.json", {}, filenotfound = None)
            for key, value in audio.items():
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
        path = path_from_root(RELATIVE_PATH + file)
        volume = data("Data/servers.json", 100, str(channel.guild.id), str(self.bot.user.id),
            "volume", filenotfound = None, keynotfound = None)
        source = DSC.FFmpegPCMAudio(path)
        source = DSC.PCMVolumeTransformer(source, volume/100)
        if vc.is_playing(): vc.stop()
        vc.play(source, after = lambda x: self.tryloop(vc))
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
        channel = find_vc(self.DscConverter, ctx, "connect")
        if ctx.guild and ctx.guild != channel.guild: channel = None

        if channel: vc = channel.guild.voice_client
        if channel is False: return await self.Reactech.reactech_user(
            ctx, "⛔", "You do not have permission to pause the bot.")
        if channel is None or not vc or not vc.is_connected():
            return await self.Reactech.reactech_user(ctx, "❓",
                "Could not find a playing voicechannel to pause.")
        
        if not vc or not vc.is_playing():
            return await self.Reactech.reactech_user(ctx, "ℹ️",
                f"No sound is currently playing in {vc.channel.mention}.")
        
        if time < 0 or time > 60:
            return await self.Reactech.reactech_channel(ctx, "🚫",
                "Fadeout can last between 0 and 60 seconds.")

        volume = data("Data/servers.json", 100, str(channel.guild.id), str(self.bot.user.id),
            "volume", filenotfound = None, keynotfound = None)/100
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
    async def loop(self, ctx: CTX, value: str = None) -> None:
        """Toogle audio looping on current/next source."""
        if not ctx.guild:
            channel = find_vc(self.DscConverter, ctx, "mute_members")

            if channel is None: return await self.Reactech.reactech_user(
                ctx, "❓", "Could not find a server to apply command to.")
            if channel is False: return await self.Reactech.reactech_user(
                ctx, "⛔", "You do not have permission to loop audio in this server.")
            guild = channel.guild
        else: guild = ctx.guild
        
        if not guild.get_member(ctx.author.id).guild_permissions.mute_members:
            return await self.Reactech.reactech_user(ctx, "⛔",
                "You do not have permission to loop audio in this server.")
        
        if value is None: looping = not data("Data/servers.json", False,
            str(guild.id), str(self.bot.user.id), "looping",
            filenotfound = None, keynotfound = None)
        else: looping = yes_no(value)
        if looping is None: return await self.Reactech.reactech_user(ctx,
            "⁉️", f"Value `{value.lower()}` could not resolve to a boolean.")

        data("Data/servers.json", looping, str(guild.id), str(self.bot.user.id), "looping", read_only = False)
        if looping: await self.Reactech.reactech_channel(ctx, "🔁", f"Looping enabled in `{guild}`.")
        else: await self.Reactech.reactech_channel(ctx, "⏯️", f"Looping disabled in `{guild}`.")


    def tryloop(self, vc: DSC.VoiceProtocol, error: Exception = None) -> None:
        try:
            if error: raise error
            if not data("Data/servers.json", False,
                str(vc.guild.id), str(self.bot.user.id), "looping",
                filenotfound = None, keynotfound = None): return
            volume = data("Data/servers.json", 100, str(vc.guild.id), str(self.bot.user.id),
                "volume", filenotfound = None, keynotfound = None)
            path = path_from_root(RELATIVE_PATH + vc.playing)
            source = DSC.PCMVolumeTransformer(DSC.FFmpegPCMAudio(path), volume/100)
            vc.play(source, after = lambda x: self.tryloop(vc))
        except Exception as e:
            if isinstance(e, DSC.ClientException) and vc.source: return
            print(f"Loop error: {e.__class__.__name__}: {e}")