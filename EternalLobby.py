import discord, psycopg2, os, asyncio, EternalChecks

from discord.ext import commands
from EternalTables import GetData, CompileLobbies, InterpretVC

DATABASE_URL = os.environ['DATABASE_URL']


class Lobby(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print ("Lobby Cog booted successfully")

    @commands.Cog.listener()
    async def on_voice_state_update(ctx, member, before, after):
        if (before.channel is not None and after.channel is None) or (before.channel is not None and after.channel != before.channel):

            conn = psycopg2.connect(DATABASE_URL, sslmode='require')
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM LobbyList WHERE ServerID='{0}' AND OwnerID='{1}' AND VCID='{2}'".format(before.channel.guild.id, member.id, before.channel.id))

            records = cursor.fetchall()
            if (len(records) > 0):
                if len(before.channel.members) == 0:
                    await before.channel.delete()
                    cursor.execute("DELETE FROM LobbyList WHERE ServerID='{0}' AND OwnerID='{1}'".format(before.channel.guild.id, member.id))
                    conn.commit()
                else:
                    tran = False
                    for i in range(0, len(before.channel.members)):
                        new = before.channel.members[i]

                        print("Transferring channel from {0} to {1}".format(member, new))

                        cursor.execute("SELECT * FROM LobbyList WHERE ServerID='{0}' AND OwnerID='{1}'".format(before.channel.guild.id, new.id))
                        results = cursor.fetchall()
                        if (len(results) > 0):
                            print("{0} already has a lobby. Skipping".format(new.name))
                            if (len(before.channel.members) == 1):
                                channel = discord.utils.find(lambda m: m.id == int(results[0][2]), before.channel.guild.voice_channels)
                                new.move_to(channel)
                                break
                        else:
                            print("Success transferring channel")
                            code = "UPDATE LobbyList SET OwnerID='%s' WHERE ServerID='%s' AND VCID='%s'"
                            values = (before.channel.members[0].id, before.channel.guild.id, before.channel.id)
                            await before.channel.edit(name="{0}#{1}".format(new.name,before.channel.members[0].discriminator))
                            cursor.execute(code, values)
                            conn.commit()
                            tran = True
                            break
                    if (tran == False):
                        await before.channel.delete()
                        cursor.execute("DELETE FROM LobbyList WHERE ServerID='{0}' AND OwnerID='{1}'".format(before.channel.guild.id, member.id))
                        conn.commit()
            cursor.close()
            conn.close()
            

    @commands.command(name="setlobby")
    @commands.check_any(EternalChecks.is_whitelisted())
    @commands.guild_only()
    async def setlobby(self, ctx, *, limit: int=0):
        lobby = ctx.channel.category
        
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        cursor = conn.cursor()
        
        data = GetData(self.bot, ctx.guild)
        
        print("Set lobby config for {0} in {1} to {2} with limit {3}".format(lobby, ctx.guild, ctx.channel, limit))

        data["Lobbies"][lobby] = {}
        data["Lobbies"][lobby]["Channel"] = ctx.channel
        data["Lobbies"][lobby]["UserLimit"] = limit
        
        code = """UPDATE Config SET Lobbies=%s WHERE ServerID='%s'"""
        values = (CompileLobbies(data["Lobbies"]), ctx.guild.id)
        cursor.execute(code, values)
        conn.commit()

        cursor.close()
        conn.close()
        
        await ctx.channel.send("Set the lobby channel for category '{0}' to '{1}'. Get gaming!".format(lobby, ctx.channel.name),
                               delete_after=10)
        await ctx.message.delete()

    @commands.command(name="stoplobby")
    @commands.check_any(EternalChecks.is_whitelisted())
    @commands.guild_only()
    async def stoplobby(self, ctx):
        lobby = ctx.channel.category
        
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        cursor = conn.cursor()
        
        data = GetData(self.bot, ctx.guild)

        print ("Removing lobby")
        data["Lobbies"].pop(lobby)
        code = """UPDATE Config SET Lobbies=%s WHERE ServerID='%s'"""
        values = (CompileLobbies(data["Lobbies"]), ctx.guild.id)
        cursor.execute(code, values)
        conn.commit()

        cursor.close()
        conn.close()
        
        await ctx.channel.send("Stopped the lobby channel for category '{0}'.".format(lobby),
                               delete_after=10)
        await ctx.message.delete()

    @commands.command(name="create")
    @commands.guild_only()
    async def create(self, ctx, *, limit: int=0):
        if (limit == 1 or limit < 0):
            await ctx.channel.send("Sorry {0}. I can't create a lobby for less than 2 people! To create a non-user limited lobby, simply don't put a number in the command.".format(ctx.message.author.mention))
            await ctx.message.delete()
            return
        elif (limit > 99):
            await ctx.channel.send("Sorry {0}. I can't create a lobby for more than 99 people! To create a non-user limited lobby, simply don't put a number in the command.".format(ctx.message.author.mention))
            await ctx.message.delete()
            return
        
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        cursor = conn.cursor()
        lobby = ctx.channel.category
        
        config = GetData(self.bot, ctx.guild)
    
        if (lobby not in config["Lobbies"]):
            await ctx.channel.send("Sorry, {0}. The server moderators haven't set up lobbies for this category yet. Give them a poke.".format(ctx.message.author.mention),
                                   delete_after=10)
            await ctx.message.delete()
        else:
            specs = config["Lobbies"][lobby]
            if (specs["UserLimit"] != 0 and specs["UserLimit"] != limit):
                await ctx.channel.send("Admins have put a specific user amount on this category. Defaulting to {0}".format(specs["UserLimit"]),
                                       delete_after=2)
                limit = specs["UserLimit"]
            cursor.execute("SELECT * FROM LobbyList WHERE ServerID='{0}' AND OwnerID='{1}'".format(ctx.guild.id, ctx.message.author.id))
            if (len(cursor.fetchall()) > 0):
                await ctx.channel.send("You already have a lobby in this server, silly {0}.".format(ctx.message.author.mention),
                                       delete_after=10)
                await ctx.message.delete()
            else:
                if specs["Channel"] != ctx.channel:
                    await ctx.channel.send("This is not the right channel in this category, {0}.".format(ctx.message.author.mention),
                                           delete_after=10)
                    await ctx.message.delete()
                    cursor.close()
                    conn.close()
                    return
                overwrites = {
                    ctx.guild.default_role: discord.PermissionOverwrite(connect=False),
                    ctx.message.author: discord.PermissionOverwrite(connect=True)
                }
                vc = await ctx.guild.create_voice_channel(name="{0}#{1}".format(ctx.message.author.name,
                                                                                ctx.message.author.discriminator),
                                                                                overwrites=overwrites,
                                                                                category=lobby,
                                                                                user_limit=limit)
                link = await vc.create_invite(max_uses=1,
                                              max_age=10)
                await ctx.channel.send("Channel created {0}. It has the same name as you! **Join it within the next 10 seconds or it will get auto deleted**\n{1}".format(ctx.message.author.mention, link),
                                       delete_after=10)
                
                code = "INSERT INTO LobbyList (ServerID, VCID, OwnerID) VALUES (%s,%s,%s)"
                values = (ctx.guild.id, vc.id, ctx.message.author.id)
                cursor.execute(code,values)
                conn.commit()
                
                await asyncio.sleep(10)
                try:
                    if (discord.utils.find(lambda m: m.id == ctx.message.author.id, vc.members) == None):
                        await vc.delete()
                        cursor.execute("DELETE FROM LobbyList WHERE ServerID='{0}' AND OwnerID='{1}'".format(ctx.guild.id, ctx.message.author.id))
                        conn.commit()
                        await ctx.message.delete()
                    else:
                        overwrites = {
                            ctx.guild.default_role: discord.PermissionOverwrite(connect=True),
                            ctx.message.author: discord.PermissionOverwrite(connect=True)
                        }
                        await vc.edit(overwrites=overwrites)
                        await ctx.message.delete()
                except:
                    cursor.execute("DELETE FROM LobbyList WHERE ServerID='{0}' AND OwnerID='{1}'".format(ctx.guild.id, ctx.message.author.id))
                    conn.commit()
                    await ctx.message.delete()
                cursor.close()
                conn.close()

    @commands.command(name="ban")
    @commands.guild_only()
    async def ban(self, ctx, *, user: discord.Member=None):
        if user is None:
            await ctx.channel.send("Oi, {0}. You've got to give me a user to ban!".format(ctx.message.author.mention),
                                   delete_after=10)
        else:

            author = ctx.message.author
            conn = psycopg2.connect(DATABASE_URL, sslmode='require')
            cursor = conn.cursor()
            lobby = ctx.channel.category

            cursor.execute("SELECT * FROM LobbyList WHERE ServerID='{0}' AND OwnerID='{1}'".format(ctx.guild.id, author.id))
            records = cursor.fetchall()
            if (len(records) == 0):
                await ctx.channel.send("You don't have a lobby to ban anyone from, {0}".format(author.mention),
                                       delete_after=10)
            else:
                VC = InterpretVC(self.bot, records[0])
                channel = VC["VC"]
                if (user in channel.members):
                    if (user.id == author.id) :
                        await ctx.channel.send("Sorry chief... you can't ban yourself. You okay there, {0}?".format(author.mention),
                                       delete_after=10)
                    else:
                        await user.move_to(None)
                overwrites = channel.overwrites
                if (overwrites[user] == discord.PermissionOverwrite(connect=False)):
                    await ctx.channel.send("{0}, that user is already banned.".format(author.mention),
                                       delete_after=10)
                else:
                    overwrites[user] = discord.PermissionOverwrite(connect=False)
                    await channel.edit(overwrites=overwrites)
                    await ctx.channel.send("{0}, that user has been banned.".format(author.mention),
                                           delete_after=10)                
            cursor.close()
            conn.close()
        await ctx.message.delete()

    @commands.command(name="unban")
    @commands.guild_only()
    async def unban(self, ctx, *, user: discord.Member=None):
        if user is None:
            await ctx.channel.send("Oi, {0}. You've got to give me a user to ubban!".format(ctx.message.author.mention),
                                   delete_after=10)
        else:

            author = ctx.message.author
            conn = psycopg2.connect(DATABASE_URL, sslmode='require')
            cursor = conn.cursor()
            lobby = ctx.channel.category

            cursor.execute("SELECT * FROM LobbyList WHERE ServerID='{0}' AND OwnerID='{1}'".format(ctx.guild.id, author.id))
            records = cursor.fetchall()
            if (len(records) == 0):
                await ctx.channel.send("You don't have a lobby to unban anyone from, {0}".format(author.mention),
                                       delete_after=10)
            else:
                VC = InterpretVC(self.bot, records[0])
                channel = VC["VC"]
                if (user.id == author.id) :
                    await ctx.channel.send("Sorry chief... you can't unban yourself. Nice try, {0}".format(author.mention),
                                            delete_after=10)
                else:
                    overwrites = channel.overwrites
                    if (overwrites[user] == discord.PermissionOverwrite(connect=True)):
                        await ctx.channel.send("{0}, that user isn't actually banned.".format(author.mention),
                                       delete_after=10)
                    else:
                        overwrites[user] = discord.PermissionOverwrite(connect=True)
                        await channel.edit(overwrites=overwrites)
                        await ctx.channel.send("{0}, that user has been unbanned.".format(author.mention),
                                               delete_after=10)                
            cursor.close()
            conn.close()
        await ctx.message.delete()

    @commands.command(name="kick")
    @commands.guild_only()
    async def kick(self, ctx, *, user: discord.Member=None):
        if user is None:
            await ctx.channel.send("Oi, {0}. You've got to give me a user to kick!".format(ctx.message.author.mention),
                                   delete_after=10)
        else:

            author = ctx.message.author
            conn = psycopg2.connect(DATABASE_URL, sslmode='require')
            cursor = conn.cursor()
            lobby = ctx.channel.category

            cursor.execute("SELECT * FROM LobbyList WHERE ServerID='{0}' AND OwnerID='{1}'".format(ctx.guild.id, author.id))
            records = cursor.fetchall()
            if (len(records) == 0):
                await ctx.channel.send("You don't have a lobby to kick anyone from, {0}".format(author.mention),
                                       delete_after=10)
            else:
                VC = InterpretVC(self.bot, records[0])
                channel = VC["VC"]
                if (user in channel.members):
                    if (user.id == author.id) :
                        await ctx.channel.send("Sorry chief... you can't kick yourself. You okay there, {0}?".format(author.mention),
                                       delete_after=10)
                    else:
                        await user.move_to(None)
                        await ctx.channel.send("{0}, that user has been kicked.".format(author.mention),
                                       delete_after=10)
                else:
                    await ctx.channel.send("That user isn't even in your channel, {0}!".format(author.mention),
                                       delete_after=10)
            cursor.close()
            conn.close()
        await ctx.message.delete()

def setup(bot):
    bot.add_cog(Lobby(bot))
