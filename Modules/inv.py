"""
Inventory management helper functions, global constants, and logging logic.
"""



##################################################
# IMPORTS
##################################################



import discord as DSC
from discord.ext.commands.context import Context as CTX

from Extensions.Common import get_prefix
from Modules.reactech import Reactech



##################################################
# GLOBALS
##################################################



WORDS = { # Common word aliases for command parsing
    "inv": ["inventory", "inv", "item", "items"],
    "all": ["everyone", "all", "*"],
    "conf": ["manage", "setup", "init", "setting", "settings", "config", "configure", "conf"],
    "help": ["help", "-h", "--help", "?"],
}
INV_ACTIONS = { # Supported inventory actions and their aliases
    "view":    ["view", "check", "v"],
    "show":    ["show", "display"],
    "change":  ["change", "update", "set", "modify", "="],
    "info":    ["info", "information", "i"],
    "clear":   ["clear", "empty", "reset"],
    "give":    ["give", "add", "grant", "g", "a", "+"],
    "remove":  ["remove", "delete", "take", "withdraw", "del", "r", "-"],
}
_ITEM_ACTIONS = { # Supported item management actions and their aliases
    "create":  ["create", "new", "add", "c", "+"],
    "edit":    ["edit", "update", "change", "modify", "e"],
    "delete":  ["delete", "remove", "del", "d", "-"],
}
SERVER_DEFAULTS = { # Default inventory structure for a server
    "items": {}, # "item_id": {item_data}
    "users": {}, # "user_id": {"item_id": quantity}
    "settings": {
        "slots": None, "capacity": None, "volume": None,
        "strict": True, "secret": True, "default_item": None
    },
    "item_default": {
        "color": "ffffff", "size": 0, "fractions": 1,
        "min": 0, "base": 0, "max": "+∞",
    },
    # Permissions for actions: "action": [["can_self"], ["can_others"]]
    "permissions":
        {"view": ([], []), "show": ([], []), "change": ([], []), "info": []}
        | {act: [] for act in _ITEM_ACTIONS},
    # Logging configuration: "action": (channel_id, log_self)
    "logs":
        {"view": (None, True), "show": (None, True), "change": (None, True)}
        | {act: None for act in list(_ITEM_ACTIONS.keys())}
        | {"error": None, "deny": (None, True)},
}
_ITEM_DEFAULTS = { # Default item structure
    "name": None, "plural": None, "aliases": [], "emoji": None,
    "id": None, "description": None, "image": None
}



##################################################
# LOGGING
##################################################



async def log_get_channel(ctx: CTX, logs: dict, action: str, self: bool = False) -> DSC.TextChannel|None:
    """Get the log channel for a given action, or None if not set."""
    if action not in logs:
        raise ValueError(f"Invalid action to log: '{action}'.")
    log = logs.get(action, (None, False))
    # Ensure log is a tuple (channel_id, log_self)
    if not isinstance(log, (list, tuple)):
        log = (log, True)
    # If no channel or not logging for this case, return None
    if not log[0] or (self and not log[1]):
        return None

    channel = ctx.guild.get_channel(int(log[0]))
    if not channel:
        # If not found and not error, log the error
        if action != "error":
            await log_error(ctx, logs,
                f"Log channel `<#{log[0]}>` for action `{action}` not found.")
            return None
        channel = ctx.channel # For error, fallback to current channel
    return channel


def log_create_embed(ctx: CTX, action: str, title: str, description: str, user: DSC.User) -> DSC.Embed:
    """Create a basic embed for logging an action, with color and author info."""
    color = {
        "view": 0x00ffff, "show": 0x00ffff, "change": 0x00ff00,
        "create": 0xffff00, "edit": 0xffff00, "delete": 0xffff00,
        "list": 0x0000ff, "info": 0x0000ff,
        "error": 0xff0000, "deny": 0xff00ff
    }.get(action, 0xffffff)
    embed = DSC.Embed(
        title=title,
        color=color,
        description=description,
        timestamp=ctx.message.created_at,
        url=ctx.message.jump_url
    )
    if user:
        author_icon = user.avatar.url if user.avatar else None
        embed.set_author(name=user.display_name, icon_url=author_icon)
    return embed


async def log_error(ctx: CTX, logs: dict, msg: str) -> None:
    """Log an error message in the inventory log channel, or notify if not set."""
    channel = await log_get_channel(ctx, logs, "error")
    if not channel:
        # If no error log channel, notify in current channel
        return await Reactech(ctx.bot).reactech_channel(
            ctx, "⚠️", "An error occurred, but no error log channel is set.\n" +
            f"Use `{get_prefix(ctx)[0]}manage_inventory log error <channel>` to set one up." # TODO:
        )
    embed = log_create_embed(ctx, "error", "Inventory: System Error", msg, ctx.bot.user)
    embed.set_footer(text=f"Created by command '{ctx.command.name}' in #{ctx.channel.name}")
    return await channel.send(embed=embed)


async def log_deny(ctx: CTX, logs: dict, msg: str, user: DSC.User) -> None:
    """Log a denied action in the inventory log channel."""
    channel = await log_get_channel(ctx, logs, "deny", self=ctx.author == user)
    if not channel:
        return
    embed = log_create_embed(ctx, "deny", "Inventory: Action Denied", msg, ctx.author)
    # If the command targeted someone else, add footer
    if ctx.author != user:
        embed.set_footer(
            text=f"Command targeted '{user.display_name}'.",
            icon_url=user.avatar.url if user.avatar else None
        )
    return await channel.send(embed=embed)


async def log_change(ctx: CTX, logs: dict, item: str,
        start: int|float, end: int|float, user: DSC.User) -> None:
    """Log a change message in the inventory log channel."""
    channel = await log_get_channel(ctx, logs, "change", self=ctx.author == user)
    if not channel:
        return
    delta = end - start
    embed = log_create_embed(
        ctx, "change",
        "Inventory: Item Changed",
        f"{item}: {start} ➔ {end} ({'+' if delta >= 0 else ''}{delta})",
        user
    )
    if ctx.author != user:
        embed.set_footer(
            text=f"Executed by '{ctx.author.display_name}'.",
            icon_url=ctx.author.avatar.url if ctx.author.avatar else None
        )
    return await channel.send(embed=embed)


async def log_action(
    ctx: CTX, logs: dict, action: str, item: str|None, user: DSC.User
) -> None:
    """Log a view/show/clear action in the inventory log channel."""
    channel = await log_get_channel(ctx, logs, action, self=ctx.author == user)
    if not channel:
        return
    # Message templates for each action
    txt = {
        "view": (
            "Inventory: Viewed",
            f"Inventory contents checked in private.",
            f"Amount of {item} checked in private."
        ),
        "show": (
            "Inventory: Shown",
            f"Inventory contents shown in {ctx.channel.mention}.",
            f"Amount of {item} shown in {ctx.channel.mention}."
        ),
        "change": (
            "Inventory: Cleared",
            f"Inventory cleared."
        ),
    }[action]
    # Use more specific message if item is specified
    embed = log_create_embed(ctx, action, txt[0], txt[2] if item else txt[1], user)
    if ctx.author != user:
        embed.set_footer(
            text=f"Executed by '{ctx.author.display_name}'.",
            icon_url=ctx.author.avatar.url if ctx.author.avatar else None
        )
    return await channel.send(embed=embed)



##################################################
# HELPER FUNCTIONS
##################################################



def resolve_action(arg: str, actions: dict = INV_ACTIONS) -> str|None:
    """Get the inventory action from the argument string, matching aliases."""
    if not arg: return None
    arg = arg.lower()
    for action, aliases in actions.items():
        if arg in aliases: return action
    return None


async def check_inv_perm(ctx: CTX, action: str, target_self: bool, inventory: dict) -> bool:
    """
    Check if the ctx author has the required permissions to do action on themself/others.
    Returns True if allowed, otherwise False.
    """
    if ctx.author.guild_permissions.administrator:
        return True
    # Map give/remove to change for permission logic
    if action in ["give", "remove"]: action = "change"
    required_perms = inventory["permissions"][action]
    # If permissions are split for self/others, select correct set
    if isinstance(required_perms, (list, tuple)) and len(required_perms) == 2:
        required_perms = required_perms[0 if target_self else 1]
    if not required_perms:
        return False
    for perm in required_perms:
        if perm.startswith("@"):
            if int(perm[1:]) == ctx.author.id:
                return True
        elif perm.startswith("&"):
            role = ctx.guild.get_role(int(perm[1:]))
            if not role:
                await log_error(ctx, inventory["logs"], f"Invalid role `{perm}` in inventory permissions for `{action}`.")
            elif role in ctx.author.roles:
                return True
        elif perm in WORDS["all"]:
            return True
        else: # Discord permission string
            perm_type = perm if hasattr(ctx.author.guild_permissions, perm) else None
            if perm_type is None:
                await log_error(ctx, inventory["logs"], f"Invalid permission `{perm}` in inventory permissions for `{action}`.")
            elif getattr(ctx.author.guild_permissions, perm, None):
                return True
    return False


def name_to_alias(name: str|None, capitalize: bool = False) -> str|None:
    """Format the item name to a valid alias."""
    if not name: return None
    disallow = "*`\"'_~ "
    for char in disallow:
        name = name.replace(char, "")
    if name.isdigit() or not name:
        return None
    if capitalize:
        name = name.strip().capitalize()
    else:
        name = name.strip().lower()
    return name


def item_display_name(item: str|dict, quantity: int|float = 1) -> str:
    """Get the display name of an item, using plural if abs(quantity) != 1."""
    if isinstance(item, str):
        item = {"name": f"`{item}`", "plural": f"`{item}`", "emoji": ''}
    if abs(quantity) != 1 and item.get("plural"):
        return f"{item.get('emoji') or ''}{item['plural']}"
    return f"{item.get('emoji') or ''}{item['name']}"


def get_item(items: dict, item: str) -> dict:
    """
    Search for an item in the inventory by name, plural, alias, or emoji.
    Returns the item data dict if found, else None.
    """
    if isinstance(item, dict): return item
    item_name = name_to_alias(item)
    if not item_name: return None
    for item_data in items.values():
        if item_name == name_to_alias(item_data["name"]):
            return item_data
        if item_data["plural"] and item_name == name_to_alias(item_data["plural"]):
            return item_data
        if item_name in item_data["aliases"]:
            return item_data
        if item_data['emoji'] and item.lower() == name_to_alias(item_data['emoji']):
            return item_data
    return None


def resolve_value(txt: str) -> (int|float|None, list):
    """
    Extract a numerical value and its type from a string.
    Returns (value, [type flags]), e.g. (5, ["int"]), (0.5, ["float", "percentage"])
    Supports absolute (=), relative (+/-), and percentage (%) notation.
    """
    if not txt: return None, []
    txt = txt.replace(",", ".").strip()
    if any([c for c in txt if not c.isnumeric() and c not in "+-.%="]):
        return None, []
    if txt.startswith("="):
        result, type2 = resolve_value(txt[1:])
        if "relative" in type2: type2.remove("relative")
        return result, type2 + ["absolute"]
    if txt.startswith(("+", "-")):
        result, type2 = resolve_value(txt[1:])
        if not type2 or "relative" in type2: return None, []
        result *= -1 if txt.startswith("-") else 1
        return result, type2 + ["relative"]
    if txt.endswith("%"):
        result, type2 = resolve_value(txt[:-1])
        if not type2 or "percentage" in type2: return None, []
        return result / 100, type2 + ["percentage"]
    if txt.count(".") > 1: return None, []
    if "." in txt:
        try: return float(txt), ["float"]
        except ValueError: return None, []
    try: return int(txt), ["int"]
    except ValueError: return None, []


def check_quantity(inventory: dict, inv: dict, item: str) -> (int|None, bool):
    """
    Get the quantity of an item in the inventory.
    Returns (quantity, present), where present is True if the item is in inventory.
    Returns None if item is not recognized and strict/secret allow the user to know that.
    """
    item_data = get_item(inventory["items"], item)
    if not item_data and inventory["settings"]["strict"] \
        and not inventory["settings"]["secret"]:
        return None, False
    if item_data:
        item = item_data["id"]
    if item in inv:
        return inv[item], True
    return 0, False


def get_user_inv(inventory: dict, user: DSC.User|DSC.Member) -> dict:
    """Get or create the inventory dict for a user."""
    inv = inventory["users"].get(str(user.id), None)
    if inv is None or not isinstance(inv, dict):
        inv = {
            i["id"]: i["base"]
            for i in inventory["items"].values()
            if i.get("base", 0) != 0
        }
    return inv


def get_stats(inventory: dict, inv: dict) -> (int, int|float, int|float):
    """
    Get statistics about the inventory:
    - number of unique items
    - total quantity of all items
    - summed size of all items
    """
    num_items = len(inv)
    total_quantity = sum([abs(q) for q in inv.values()])
    total_size = 0
    for item, quantity in inv.items():
        item_data = get_item(inventory["items"], item)
        size = item_data["size"] if item_data else inventory["item_default"]["size"]
        total_size += abs(quantity) * size
    return num_items, total_quantity, total_size


async def inv_send(ctx: CTX|DSC.TextChannel, msg: str, secret: bool = False) -> None:
    """
    Send a message or embed to the user or channel.
    If secret is True, send as DM to the author.
    """
    message, embed = (None, msg) if isinstance(msg, DSC.Embed) else (msg, None)
    if secret:
        return await ctx.author.send(message, embed=embed)
    if isinstance(ctx, CTX):
        return await ctx.reply(message, embed=embed)
    return await ctx.send(message, embed=embed)



##################################################
# MAIN
##################################################



if __name__ == "__main__":
    pass