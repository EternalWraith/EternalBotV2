import discord, os, psycopg2, EternalTables

from discord.ext import commands
from EternalTables import GetData

DATABASE_URL = os.environ['DATABASE_URL']


def get_prefix(bot, message):
    if not message.guild:
        return commands.when_mentioned_or("e2-")(bot, message)
    else:
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Config WHERE ServerID='{0}'".format(message.guild.id))
        configs = cursor.fetchall()
        if (len(configs)==0):
            code = """INSERT INTO Config (ServerID, AuditID, Prefix, Lobbies, TicketID, "Tickets", WhiteList)
VALUES (%s,%s, %s, %s, %s, %s, %s)"""
            values = (message.guild.id, None, "e2-", [], None, 0, [])
            cursor.execute(code, values)
            conn.commit()
            
            cursor.execute("SELECT * FROM Config WHERE ServerID='{0}'".format(message.guild.id))
            configs = cursor.fetchall()
        config = configs[0]
        data = GetData(bot, message.guild)
        cursor.close()
        conn.close()
        return commands.when_mentioned_or(data["Prefix"])(bot, message)


class EternalBot(commands.Bot):

    async def close(self):
        await super().close()
        print("Hello")

bot = commands.Bot(command_prefix=get_prefix, description="EternalBot v2")
bot.load_extension("EternalLobby")
bot.load_extension("EternalTicket")
bot.load_extension("EternalModerate")
bot.load_extension("EternalLevel")

bot.load_extension("EternalDefcon")

@bot.event
async def on_ready():
    print("We logged in as {0.user}".format(bot))
    await bot.change_presence(activity=discord.Game(name="Nibbling on Cookies", type=1, url="http://twitch.tv/TheRealWraithGG"))

@bot.event
async def on_message(message):
    if message.author == bot.user:
        #stop bot from responding to itself
        return

    if message.content.startswith("EternalBot"):
        await message.channel.send("Sah Dude")

    await bot.process_commands(message)

@bot.command(name="invite", aliases=["inv"])
async def invite(ctx):
    perms = discord.Permissions.none()
    perms.read_messages = True
    perms.send_messages = True
    perms.manage_roles = True
    perms.ban_members = False
    perms.kick_members = False
    perms.manage_messages = True
    perms.embed_links = True
    perms.read_message_history = True
    perms.attach_files = True
    app_info = await bot.application_info()
    await ctx.channel.send("Here you go friend! One invite just for you!\n%s" % (discord.utils.oauth_url(app_info.id, perms)))

@bot.command(name="prefix")
@commands.has_permissions(administrator=True)
async def prefix(ctx, *, symbol: str=None):
    if not ctx.message.guild:
        await ctx.channel.send("This command can only be used in a server by an admin. Sorry pal.")
        return
    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    cursor = conn.cursor()

    data = GetData(bot, ctx.guild)
    
    if not symbol:
        await ctx.channel.send("My command prefix for your server is '{0}'".format(data["Prefix"]))
    else:
        code = """UPDATE Config SET Prefix=%s WHERE ServerID='%s'"""
        values = (symbol, ctx.guild.id)
        cursor.execute(code, values)
        conn.commit()
        await ctx.channel.send("My command prefix for your server is now set to '{0}'!".format(symbol))
    cursor.close()
    conn.close()
            
bot.run(os.environ["BOT_TOKEN"])
print("Hello")
