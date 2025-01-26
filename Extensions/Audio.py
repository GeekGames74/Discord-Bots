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

from os import listdir
from asyncio import gather

from Modules.reactech import Reactech
from Modules.discord_utils import DscConverter
from Modules.data import data_JSON, checkfile
from Modules.basic import mixmatch, plural, correspond, path_from_root


async def setup(bot: Bot):
    await bot.add_cog(Voice(bot))
    await bot.add_cog(Sounds(bot))



##################################################
# VOICE
##################################################



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

        if ctx.guild.voice_client is not None:
            if ctx.guild.voice_client.is_connected():
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
            await self.Reactech.reactech_user(ctx, "🚫",
                "Command only works in servers.")
            return
        
        vc = ctx.guild.voice_client
        if vc is None or not vc.is_connected():
            await self.Reactech.reactech_channel(ctx, "ℹ️",
                "Bot is not connected to a voice channel.")
            return
        
        channel = vc.channel
        await vc.disconnect()
        await self.Reactech.reactech_valid(ctx,
            f"Left voice channel {channel.mention}.")
    

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
                await ctx.send("The bot is not connected to any voice channels.")
                return
            playing = [vc for vc in vcs if vc.is_playing()]
            msg += f"The bot is connected to `{len(vcs)}` voice channel{plural(len(vcs))}."
            if playing: msg += f"\n`{len(vcs)}` of those {plural(vcs, _1='is', _p='are')} actively playing."
            if cmd is not None and cmd.lower() in ["l", "ls", "list"]:
                for vc in vcs:
                    playmsg = " 🔊" if vc.is_playing() else " 🔇"
                    if ctx.guild and ctx.guild == vc.guild:
                        msg += f"\n- {vc.channel.mention} in '{vc.guild.name}'" + playmsg
                    elif not ctx.guild and vc.guild.get_member(ctx.author.id):
                        msg += f"\n- '#{vc.channel.name}' in '{vc.guild.name}'" + playmsg
                    else:
                        msg += f"\n- #{vc.channel.id} in {vc.guild.id}" + playmsg
            await ctx.send(msg)
            return

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


def format_filename(input: str) -> (str, str):
    """Format the filename for soundboard use."""
    splitted = input.split(".")
    ext = splitted[1] if len(splitted) > 1 else None
    name = "".join(c for c in splitted[0] if c.isalnum())
    return name.lower(), ext


class Sounds(CMDS.Cog):
    """Soundboard and preset music."""
    def __init__(self, bot: Bot):
        self.bot = bot
        self.Reactech = Reactech(bot)
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
            await self.Reactech.reactech_channel(ctx, "ℹ️",
                "Bot is already playing a sound.")
            return
        
        if vc.is_paused() and msg is None:
            vc.resume()
            try: source = f"`{vc.playing}`"
            except AttributeError: source = "audio"
            await self.Reactech.reactech_valid(ctx,
                f"Resumed {source} in {vc.channel.mention}.")
            return
        
        if msg is None:
            await self.Reactech.reactech_user(ctx, "⁉️",
                "No sound filename specified.")
            return
        
        name = format_filename(msg)[0]
        try:
            data = data_JSON(RELATIVE_PATH + "aliases.json")
            for file, aliases in data.items():
                if name == file or name in aliases:
                    name = file
                    break
        except FileNotFoundError:
            pass
        files = [] ; exts = []
        for i in listdir(path_from_root(RELATIVE_PATH)):
            splitted = format_filename(i)
            files.append(splitted[0])
            exts.append(splitted[1])
        final = correspond(name, files)
        if final is None:
            await self.Reactech.reactech_user(ctx,
                "❓", f"Could not find sound file `{msg}`.")
            return
        
        file = final + "." + exts[files.index(final)]
        path = checkfile(RELATIVE_PATH + file)
        source = DSC.FFmpegPCMAudio(path)
        if vc.is_playing(): vc.stop()
        vc.play(source)
        vc.playing = file
        await self.Reactech.reactech_valid(ctx,
            f"Playing `{file}` in {vc.channel.mention}.")
    


    @CMDS.command(name = "pause", aliases = mixmatch(["s", "stop", "pause", "mute"],
            ["", "sound", "sounds", "audio"], remove=["pause", "sounds"]))
    async def pause(self, ctx: CTX) -> None:
        """Stop the sound being played."""
        if ctx.guild is None:
            await self.Reactech.reactech_user(ctx, "🚫",
                "Command only works in servers.")
            return
        
        vc = ctx.guild.voice_client
        if vc is None or not vc.is_connected():
            await self.Reactech.reactech_channel(ctx, "🚫",
                "Bot is not connected to a voice channel.")
            return
        
        if not vc.is_playing():
            await self.Reactech.reactech_user(ctx, "ℹ️",
                f"No sound is currently playing in {vc.channel.mention}.")
            return
        
        vc.pause()
        try: source = f"`{vc.playing}`"
        except AttributeError: source = "audio"
        await self.Reactech.reactech_valid(ctx,
            f"Paused {source} in {vc.channel.mention}.")




        
