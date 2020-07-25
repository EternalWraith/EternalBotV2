import discord, psycopg2, os, asyncio, EternalTables, EternalChecks

from discord.ext import commands
from EternalTables import InterpretTicket, GetData

DATABASE_URL = os.environ['DATABASE_URL']



class Ticket(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print ("Ticket Cog booted successfully")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user:
            #stop bot from responding to itself
            return
        elif not message.content.count("-close", 2,8) and not message.content.count("-ticket", 2,9):
            conn = psycopg2.connect(DATABASE_URL, sslmode='require')
            cursor = conn.cursor()
            
            channel = message.channel
            sender = message.author
            cursor.execute("SELECT * FROM TicketList WHERE OwnerID='{0}' AND EndingID IS NULL".format(message.author.id))
            results = cursor.fetchall()
            if not message.guild:
                if (len(results) != 0):
                    ticket = await InterpretTicket(self.bot, results[0])
                    channel = ticket["Channel"]
                    emb = discord.Embed(title="Response from User")
                    emb.add_field(name="Message", value=message.content)
                    emb.set_footer(text="{0}#{1}".format(message.author.name, message.author.discriminator), icon_url=message.author.avatar_url)
                    await channel.send(embed=emb)
            else:
                cursor.execute("SELECT * FROM TicketList WHERE ChannelID='{0}' AND EndingID IS NULL".format(message.channel.id))
                results = cursor.fetchall()
                if (len(results) != 0):
                    ticket = await InterpretTicket(self.bot, results[0])
                    user = ticket["Owner"]
                    DM = await user.create_dm()
                    emb = discord.Embed(title="Response from Mods")
                    emb.add_field(name="Message", value=message.content)
                    emb.set_footer(text="{0}#{1}".format(message.author.name, message.author.discriminator), icon_url=message.author.avatar_url)
                    await DM.send(embed=emb)
            cursor.close()
            conn.close()

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        guild = self.bot.get_guild(payload.guild_id)
        channel = self.bot.get_channel(payload.channel_id)
        emoji = payload.emoji.name
        member = payload.member

        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM TicketList WHERE ChannelID='{0}' AND EndingID IS NOT NULL".format(channel.id))
        results = cursor.fetchall()
        if (len(results) != 0):
            ticket = await InterpretTicket(self.bot, results[0])
            print(emoji == "\U0001f512")
            if (emoji == "\U0001f512"):
                if (payload.message_id == ticket["Ending"].id):
                    print("Deleting")
                    await ticket["Channel"].delete()
                    cursor.execute("DELETE FROM TicketList WHERE ChannelID='{0}' AND EndingID IS NOT NULL".format(channel.id))
                    conn.commit()
        cursor.close()
        conn.close()
                
        

    @commands.command(name="setuptickets")
    @commands.check_any(EternalChecks.is_whitelisted())
    @commands.guild_only()
    async def setuptickets(self, ctx):
        lobby = ctx.channel.category
        
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        cursor = conn.cursor()

        #data = GetData(self.bot, ctx.guild)
        code = """UPDATE Config SET TicketID='%s' WHERE ServerID='%s'"""
        values = (lobby.id, ctx.guild.id)
        cursor.execute(code, values)
        conn.commit()

        cursor.close()
        conn.close()
        
        await ctx.channel.send("Set the ticket category for your server to '{0}'. You've got mail!".format(lobby),
                               delete_after=10)
        await ctx.message.delete()

    @commands.command(name="ticket")
    @commands.guild_only()
    async def ticket(self, ctx, *, message: str=None):
        await ctx.message.delete()
        if (message == None):
            await ctx.channel.send("Please provide a message, {0}. This helps the moderators to deal with your ticket quicker".format(ctx.message.author.mention),
                                   delete_after=10)
            return
        lobby = ctx.channel.category
        
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        cursor = conn.cursor()

        data = GetData(self.bot, ctx.guild)
        if (data["Inbox"] == None):
            await ctx.channel.send("Moderators are not accepting tickets here, {0}. They can open an inbox by typing `e2-setuptickets` in the category they want tickets sent to".format(ctx.message.author.mention),
                                   delete_after=10)
        else:
            cursor.execute("SELECT * FROM TicketList WHERE OwnerID='{0}' AND EndingID IS NULL".format(ctx.message.author.id))
            if (len(cursor.fetchall()) != 0):
                await ctx.channel.send("You already have a ticket active somewhere. Please resolve that one first, {0}. (To force close a ticket, type `e2-close`)".format(ctx.message.author.mention),
                                       delete_after=10)
            else:
                ticket = data["Tickets"]+1
                category = data["Inbox"]
                channel = await ctx.guild.create_text_channel(name="Ticket #{0}".format(str(ticket)), category=category)
                code = """INSERT INTO TicketList (ServerID, OwnerID, ChannelID, EndingID) VALUES (%s,%s,%s, %s)"""
                values = (ctx.guild.id, ctx.message.author.id, channel.id, None)
                cursor.execute(code, values)
                conn.commit()
                code = """UPDATE Config SET "Tickets"='%s' WHERE ServerID='%s'"""
                values = (ticket, ctx.guild.id)
                cursor.execute(code, values)
                conn.commit()
                DM = await ctx.message.author.create_dm()
                await DM.send("Please hold on for a second. The moderators will look at your ticket soon and get back to you. If they don't respond, you can close this ticket with `e2-close`")
                await channel.send("@everyone, {0} has created a ticket".format(ctx.message.author.mention))
                emb = discord.Embed(title="New Ticket: #"+str(ticket))
                emb.add_field(name="Message", value=message)
                emb.set_footer(text="{0}#{1}".format(ctx.message.author.name, ctx.message.author.discriminator), icon_url=ctx.message.author.avatar_url)
                await channel.send(embed=emb)
        cursor.close()
        conn.close()

    @commands.command(name="close")
    async def close(self, ctx):
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM TicketList WHERE OwnerID='{0}'".format(ctx.message.author.id))
        results = cursor.fetchall()
        if not ctx.guild:
            if (len(results) == 0):
                DM = await ctx.message.author.create_dm()
                await DM.send("You don't currently have any tickets open. Open one in a server with `e2-ticket`")
            else:
                ticket = await InterpretTicket(self.bot, results[0])
                channel = ticket["Channel"]
                ending = await channel.send("This ticket has been closed by the user. Respond with a :lock: to close the channel")
                await ending.add_reaction("\U0001f512")
                DM = await ctx.message.author.create_dm()
                await DM.send("Your ticket is now closed. I hope your issue was resolved!")
                cursor.execute("UPDATE TicketList SET EndingID='{0}' WHERE OwnerID = '{1}' AND EndingID IS NULL".format(ending.id, ctx.message.author.id))
                conn.commit()
        else:
            cursor.execute("SELECT * FROM TicketList WHERE ChannelID='{0}'".format(ctx.message.channel.id))
            results = cursor.fetchall()
            if (len(results) != 0):
                ticket = await InterpretTicket(self.bot, results[0])
                user = ticket["Owner"]
                ending = await ctx.channel.send("This ticket is now closed. Respond with a :lock: to close the channel")
                await ending.add_reaction("\U0001f512")
                DM = await user.create_dm()
                await DM.send("The moderators have closed your ticket. I hope your issue was resolved!")
                cursor.execute("UPDATE TicketList SET EndingID='{0}' WHERE OwnerID = '{1}' AND EndingID IS NULL".format(ending.id, user.id))
                conn.commit()
            else:
                await ctx.channel.send("You must use this command in either a DM, or as a moderator in a ticket channel, {0}".format(ctx.message.author.mention))
                
              
        cursor.close()
        conn.close()


def setup(bot):
    bot.add_cog(Ticket(bot))
