import os

from discord.ext import commands

DATABASE_URL = os.environ['DATABASE_URL']


def is_whitelisted():
    def predicate(ctx):
        whitelist = ctx.bot.Configs[ctx.guild.id]["Whitelist"]
        return (ctx.guild is not None and
                (ctx.author.id == ctx.guild.owner_id or
                 ctx.author.top_role.permissions.administrator or
                 ctx.author.top_role in whitelist))
    return commands.check(predicate)


def is_topdog():
    def predicate(ctx):
        return (ctx.guild is not None and
                (ctx.author.id == ctx.guild.owner_id or
                 ctx.author.top_role.permissions.administrator))
    return commands.check(predicate)


def has_killswitch():
    def predicate(ctx):
        return (str(ctx.message.author.id) == os.environ["BOT_OWNER"])
    return commands.check(predicate)
