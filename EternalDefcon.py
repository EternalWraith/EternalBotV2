import discord, psycopg2, os, asyncio, EternalChecks, EternalTables

from discord.ext import commands

DATABASE_URL = os.environ['DATABASE_URL']


class Defcon(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        EternalTables.SetupConfigTable()
        EternalTables.SetupLobbyTable()
        EternalTables.SetupTicketTable()
        EternalTables.SetupLevelTable()
        
        print ("Defcon Cog booted successfully")

    @commands.command(name="dropoldtables", hidden=True)
    @commands.check_any(EternalChecks.has_killswitch())
    async def dropoldtables(self, ctx):
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        cursor = conn.cursor()
        cursor.execute("""DROP TABLE ModConfig;
DROP TABLE TicketConfig;
DROP TABLE LobbyConfig;
DROP TABLE ServerConfig;""")
        conn.commit()
        cursor.close()
        conn.close()

        
    @commands.command(name="resetconfigtable", hidden=True)
    @commands.check_any(EternalChecks.has_killswitch())
    async def resetconfigtable(self, ctx):
        EternalTables.SetupConfigTable(True)
        await ctx.channel.send("Reset the Config table for you, Mr Wraith!")
        servers = self.bot.guilds

        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        cursor = conn.cursor()
        
        for server in servers:
            print("Adding in server {0}".format(server))
            code = """INSERT INTO Config (ServerID, AuditID, Prefix, Lobbies, TicketID, "Tickets", WhiteList)
VALUES (%s,%s, %s, %s, %s, %s, %s)"""
            values = (server.id, None, "e2-", [], None, 0, [])
            cursor.execute(code, values)
            conn.commit()

    @commands.command(name="resetleveltable", hidden=True)
    @commands.check_any(EternalChecks.has_killswitch())
    async def resetleveltable(self, ctx):
        EternalTables.SetupLevelTable(True)
        await ctx.channel.send("Reset the Level table for you, Mr Wraith!")
        servers = self.bot.guilds

        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        cursor = conn.cursor()
        
        for server in servers:
            print("Adding in server {0}".format(server))
            code = """INSERT INTO Levels (ServerID, Enabled, Users, LevelCap, Prestiges, XPGain, Cooldowns)
VALUES (%s, %s, %s, %s, %s, %s, %s)"""
            values = (server.id, False, [], [55,1000], [], [5,50,15], [])
            cursor.execute(code, values)
            conn.commit()

    @commands.command(name="resetlobbytable", hidden=True)
    @commands.check_any(EternalChecks.has_killswitch())
    async def resetlobbytable(self, ctx):
        EternalTables.SetupLobbyTable(True)
        await ctx.channel.send("Reset the Lobby table for you, Mr Wraith!")

    @commands.command(name="resettickettable", hidden=True)
    @commands.check_any(EternalChecks.has_killswitch())
    async def resettickettable(self, ctx):
        EternalTables.SetupTicketTable(True)
        await ctx.channel.send("Reset the Ticket table for you, Mr Wraith!")

    @commands.command(name="testinterpret", hidden=True)
    @commands.check_any(EternalChecks.has_killswitch())
    async def testinterpret(self, ctx):
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Config WHERE ServerID='{0}'".format(ctx.guild.id))
        try:
            it = cursor.fetchall()
            print(EternalTables.InterpretData(self.bot, it[0]))
        except:
            print("Failure")

    @resettickettable.error
    @resetlobbytable.error
    @resetconfigtable.error
    @resetleveltable.error
    async def table_error(self, ctx, error):
        if isinstance(error, commands.CheckFailure):
            await ctx.channel.send("Only Wraith can use this command. Sorry pal.")



def setup(bot):
    bot.add_cog(Defcon(bot))
