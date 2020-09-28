import discord
import os
import EternalChecks

from discord.ext import commands

DATABASE_URL = os.environ['DATABASE_URL']


class Moderate(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("Moderate Cog booted successfully")

    @commands.command(name="erase", aliases=["purge", "prune"])
    @commands.check_any(EternalChecks.is_whitelisted())
    async def erase(self, ctx, *, amount: int = None):
        if not amount:
            await ctx.channel.send(
                "Yo, %s, you gotta specify an amount of messages to erase Bud"
                % (ctx.message.author.mention)
            )
        else:
            def is_call(m):
                return m.id != ctx.message.id
            await ctx.channel.purge(limit=amount+1, check=is_call)
            await ctx.channel.send("All cleaned up!",
                                   delete_after=10)
            await ctx.message.delete()

    @erase.error
    async def erase_error(self, ctx, error):
        if isinstance(error, commands.CheckFailure):
            await ctx.message.delete()
            await ctx.send(
                "You do not have the required permissions for this command",
                delete_after=10
            )

    @commands.command(name="whitelist")
    @commands.check_any(EternalChecks.is_topdog())
    async def whitelist(self, ctx, *, role: discord.Role):
        if (role in self.bot.Configs["Whitelist"]):
            self.bot.Configs["Whitelist"].remove(role)
            await ctx.channel.send(
                "Removed %s from the whitelist,"
                " now they have less power than me without cookies"
                % (role.mention))
        else:
            self.bot.Configs["Whitelist"].append(role)
            await ctx.channel.send(
                "Whitelisted %s for you,"
                " so now they can use the STRONG commands"
                % (role.mention))

    @commands.command(name="prefix")
    @commands.check_any(EternalChecks.is_whitelisted())
    async def prefix(self, ctx, *, symbol: str = None):
        if not ctx.message.guild:
            await ctx.channel.send(
                "This command can only be used in a server by an admin."
                " Sorry pal.")
            return

        if not symbol:
            await ctx.channel.send("My command prefix for your server is '%s'"
                                   % (self.bot.Configs["Prefix"]))
        else:
            self.bot.Configs["Prefix"] = symbol
            await ctx.channel.send(
                "My command prefix for your server is now set to '%s'!"
                % (symbol))


def setup(bot):
    bot.add_cog(Moderate(bot))
