import os
import EternalChecks
import EternalTables

from discord.ext import commands

DATABASE_URL = os.environ['DATABASE_URL']


class Defcon(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        EternalTables.SetupConfigTable(self.bot.Cursor, self.bot.Conn)
        EternalTables.SetupLobbyTable(self.bot.Cursor, self.bot.Conn)
        EternalTables.SetupTicketTable(self.bot.Cursor, self.bot.Conn)
        EternalTables.SetupLevelTable(self.bot.Cursor, self.bot.Conn)

        print("Defcon Cog booted successfully")

    @commands.command(name="resetconfigtable", hidden=True)
    @commands.check_any(EternalChecks.has_killswitch())
    async def resetconfigtable(self, ctx):
        self.bot.Configs = {}
        await ctx.channel.send("Reset the Config table for you, Mr Wraith!",
                               delete_after=5)
        await ctx.message.delete()

    @commands.command(name="resetleveltable", hidden=True)
    @commands.check_any(EternalChecks.has_killswitch())
    async def resetleveltable(self, ctx):
        self.bot.Levels = {}
        await ctx.channel.send("Reset the Level table for you, Mr Wraith!",
                               delete_after=5)
        await ctx.message.delete()

    @commands.command(name="resetlobbytable", hidden=True)
    @commands.check_any(EternalChecks.has_killswitch())
    async def resetlobbytable(self, ctx):
        self.bot.Lobbies = {}
        await ctx.channel.send("Reset the Lobby table for you, Mr Wraith!",
                               delete_after=5)
        await ctx.message.delete()

    @commands.command(name="resettickettable", hidden=True)
    @commands.check_any(EternalChecks.has_killswitch())
    async def resettickettable(self, ctx):
        self.bot.Tickets = {}
        await ctx.channel.send("Reset the Ticket table for you, Mr Wraith!",
                               delete_after=5)
        await ctx.message.delete()

    @commands.command(name="execute", hidden=True)
    @commands.check_any(EternalChecks.has_killswitch())
    async def execute(self, ctx, command: str):
        await ctx.channel.send("Executing '%s'" % (command),
                               delete_after=5)
        self.bot.Cursor.execute(command)
        self.bot.Conn.commit()
        await ctx.channel.send("Executed", delete_after=5)
        await ctx.message.delete()

    @resettickettable.error
    @resetlobbytable.error
    @resetconfigtable.error
    @resetleveltable.error
    async def table_error(self, ctx, error):
        if isinstance(error, commands.CheckFailure):
            await ctx.channel.send("Only Wraith can use this command."
                                   " Sorry pal.")


def setup(bot):
    bot.add_cog(Defcon(bot))
