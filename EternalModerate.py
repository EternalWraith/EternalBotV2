import discord, os, psycopg2, EternalChecks

from discord.ext import commands
from EternalTables import GetData, CompileWhitelist

DATABASE_URL = os.environ['DATABASE_URL']


class Moderate(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print ("Moderate Cog booted successfully")
    
    @commands.command(name="erase", aliases=["purge","prune"])
    @commands.check_any(EternalChecks.is_whitelisted())
    async def erase(self, ctx, *, amount: int=None):
        if not amount:
            await ctx.channel.send("Yo, {0}, you gotta specify an amount of messages to erase Bud".format(ctx.message.author.mention))
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
            await ctx.send("You do not have the required permissions for this command",
                           delete_after=10)

    @commands.command(name="whitelist")
    @commands.check_any(EternalChecks.is_topdog())
    async def whitelist(self, ctx, *, role: discord.Role):
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        cursor = conn.cursor()

        data = GetData(self.bot, ctx.guild)

        if (role in data["WhiteList"]):
            data["WhiteList"].remove(role)
            await ctx.channel.send("Removed {0} from the whitelist, now they have less power than me without cookies".format(role.mention))
        else:
            data["WhiteList"].append(role)
            await ctx.channel.send("Whitelisted {0} for you, so now they can use the STRONG commands".format(role.mention))

        code = """UPDATE Config SET WhiteList=%s WHERE ServerID='%s'"""
        values = (CompileWhitelist(data["WhiteList"]), ctx.guild.id)
        cursor.execute(code, values)
        conn.commit()

    
        

def setup(bot):
    bot.add_cog(Moderate(bot))
