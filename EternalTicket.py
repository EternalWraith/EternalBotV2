import discord
import os
import EternalChecks
import io
import requests

from discord.ext import commands

DATABASE_URL = os.environ['DATABASE_URL']


class Ticket(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("Ticket Cog booted successfully")

    async def findTicket(self, user):
        for i in self.bot.Tickets:
            if self.bot.Tickets[i]["Owner"].id == user.id:
                if not self.bot.Tickets[i]["Ending"]:
                    return self.bot.Tickets[i]
        return None

    @commands.Cog.listener()
    async def on_message(self, message):
        filetypes = (
            ".jpg",
            ".jpeg",
            ".png",
            ".gif"
        )

        if not (message.guild):
            prefix = "e2-"
        else:
            prefix = self.bot.Configs[message.guild.id]["Prefix"]

        if message.author == self.bot.user:
            # stop bot from responding to itself
            return
        elif (not message.content.startswith(prefix+"close")
              and not message.content.startswith(prefix+"ticket")):
            if not message.guild:
                ticket = await self.findTicket(message.author)
                if (ticket):
                    channel = ticket["Channel"]

                    if message.content != "":
                        emb = discord.Embed(title="Response from User")
                        emb.add_field(name="Message", value=message.content)
                        emb.set_footer(
                            text="%s#%s" % (
                                        message.author.name,
                                        message.author.discriminator
                                    ),
                            icon_url=message.author.avatar_url)
                        await channel.send(embed=emb)

                    if len(message.attachments) > 0:

                        for att in message.attachments:
                            if att.filename.lower().endswith(filetypes):
                                emb = discord.Embed(
                                    title="Attachment from User"
                                )
                                # xfile = await att.to_file()

                                attachment = requests.get(att.url)
                                bytes = io.BytesIO(attachment.content)
                                ext = att.filename.lower().split(".")[-1]
                                file = discord.File(bytes,
                                                    filename="file."+ext
                                                    )

                                emb.set_image(url="attachment://file."+ext)
                                emb.set_footer(
                                    text="%s#%s" % (
                                                message.author.name,
                                                message.author.discriminator
                                            ),
                                    icon_url=message.author.avatar_url)

                                await channel.send(file=file, embed=emb)
            else:
                if (message.channel.id in self.bot.Tickets):
                    ticket = self.bot.Tickets[message.channel.id]
                    if not (ticket["Ending"]):

                        if message.content != "":
                            emb = discord.Embed(title="Response from Mods")
                            emb.add_field(
                                name="Message",
                                value=message.content
                            )
                            emb.set_footer(
                                text="%s#%s" % (
                                            message.author.name,
                                            message.author.discriminator
                                            ),
                                icon_url=message.author.avatar_url
                            )
                            await ticket["Owner"].send(embed=emb)

                        for att in message.attachments:
                            if att.filename.lower().endswith(filetypes):
                                emb = discord.Embed(
                                    title="Attachment from Mods"
                                )
                                # xfile = await att.to_file()

                                attachment = requests.get(att.url)
                                bytes = io.BytesIO(attachment.content)
                                file = discord.File(bytes,
                                                    filename="file."+ext
                                                    )

                                emb.set_image(url="attachment://file."+ext)
                                emb.set_footer(
                                    text="%s#%s" % (
                                                message.author.name,
                                                message.author.discriminator
                                            ),
                                    icon_url=message.author.avatar_url)

                                await ticket["Owner"].send(
                                    file=file,
                                    embed=emb
                                )

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        guild = self.bot.get_guild(payload.guild_id)
        channel = self.bot.get_channel(payload.channel_id)
        emoji = payload.emoji.name
        member = payload.member
        messageid = payload.message_id

        if (member.id == self.bot.user.id):
            return

        if (channel.id in self.bot.Tickets):
            ticket = self.bot.Tickets[channel.id]
            if (ticket["Ending"]):
                print(emoji == "\U0001f512")
                if (emoji == "\U0001f512"):
                    if (messageid == ticket["Ending"].id):
                        print("Deleting")
                        await ticket["Channel"].delete()
                        self.bot.Tickets.pop(channel.id)
                else:
                    await channel.fetch_message(id).remove_reaction(emoji,
                                                                    member)
        elif (channel.id ==
              self.bot.Configs[guild.id]["TicketMessage"]["Channel"].id) and (
              messageid ==
              self.bot.Configs[guild.id]["TicketMessage"]["Message"].id
              ):
            envelope = "\U00002709"
            if (emoji == envelope):
                await self.maketicket(
                    guild,
                    channel,
                    member,
                    self.bot.Configs[guild.id]["TicketMessage"]["Message"],
                    "Created ticket through reaction"
                )
                await (await channel.fetch_message(messageid)).remove_reaction(
                    emoji,
                    member
                )
            else:
                await (await channel.fetch_message(messageid)).remove_reaction(
                    emoji,
                    member
                )

    @commands.command(name="setuptickets")
    @commands.check_any(EternalChecks.is_whitelisted())
    @commands.guild_only()
    async def setuptickets(self, ctx):
        lobby = ctx.channel.category

        # data = GetData(self.bot, ctx.guild)
        self.bot.Configs[ctx.guild.id]["Inbox"] = lobby

        await ctx.channel.send(
            "Set the ticket category for your server to '%s'."
            " You've got mail!" % (lobby),
            delete_after=10
        )
        await ctx.message.delete()

    async def maketicket(self, guild, channel, author, message, string,
                         userMessage=None):
        if userMessage:
            await userMessage.delete()
        if not (string):
            await channel.send(
                "Please provide a message, %s."
                " This helps the moderators to deal with your ticket quicker"
                % (author.mention),
                delete_after=10
            )
            return

        if not (self.bot.Configs[guild.id]["Inbox"]):
            await channel.send(
                "Moderators are not accepting tickets here, %s."
                " They can open an inbox by typing `e2-setuptickets`"
                " in the category they want tickets sent to"
                % (author.mention),
                delete_after=10
            )
        else:
            ticket = await self.findTicket(author)
            if (ticket):
                await channel.send(
                    "You already have a ticket active somewhere."
                    " Please resolve that one first, %s."
                    " (To force close a ticket, type `e2-close`)"
                    % (author.mention),
                    delete_after=10
                )
            else:
                ticket = self.bot.Configs[guild.id]["Tickets"]+1
                category = self.bot.Configs[guild.id]["Inbox"]
                channel = await guild.create_text_channel(
                    name="Ticket #%s" % (str(ticket)),
                    category=category
                )
                await self.bot.AddTicket(
                    guild.id,
                    channel.id,
                    author.id
                )

                await author.send(
                    "Please hold on for a second."
                    " The moderators will look at your ticket soon"
                    " and get back to you. If they don't respond,"
                    " you can close this ticket with `e2-close`")
                await channel.send(
                    "@everyone, %s has created a ticket"
                    % (author.mention))
                emb = discord.Embed(title="New Ticket: #"+str(ticket))
                emb.add_field(name="Message", value=string)
                emb.set_footer(
                    text="%s#%s"
                    % (
                        author.name,
                        author.discriminator
                    ),
                    icon_url=author.avatar_url)
                await channel.send(embed=emb)

    @commands.command(name="ticket")
    @commands.guild_only()
    async def ticket(self, ctx, *, message: str = None):
        await self.maketicket(ctx.guild, ctx.channel, ctx.author,
                              ctx.message, message, ctx.message)

    @commands.command(name="ticketmessage")
    @commands.guild_only()
    async def ticketmessage(self, ctx, *, message: discord.Message):
        print(self.bot.Configs)
        print(self.bot.Configs[ctx.guild.id])
        print(self.bot.Configs[ctx.guild.id]["TicketMessage"])
        self.bot.Configs[ctx.guild.id]["TicketMessage"]["Channel"] =\
            ctx.channel
        self.bot.Configs[ctx.guild.id]["TicketMessage"]["Message"] = message
        await message.add_reaction("\U00002709")
        await ctx.message.delete()

    @commands.command(name="close")
    async def close(self, ctx):
        if not ctx.guild:
            ticket = await self.findTicket(ctx.author)
            if not (ticket):
                await ctx.author.send(
                    "You don't currently have any tickets open."
                    " Open one in a server with `e2-ticket`")
            else:
                channel = ticket["Channel"]
                ending = await channel.send(
                    "This ticket has been closed by the user."
                    " Respond with a :lock: to close the channel")
                await ending.add_reaction("\U0001f512")
                await ctx.author.send(
                    "Your ticket is now closed. "
                    " I hope your issue was resolved!")
                self.bot.Tickets[channel.id]["Ending"] = ending
        else:
            if (ctx.channel.id in self.bot.Tickets):
                ticket = self.bot.Tickets[ctx.channel.id]
                if not (ticket["Ending"]):
                    ending = await ctx.channel.send(
                        "This ticket is now closed."
                        " Respond with a :lock: to close the channel"
                    )
                    await ending.add_reaction("\U0001f512")
                    await ticket["Owner"].send(
                        "The moderators have closed your ticket."
                        " I hope your issue was resolved!"
                    )
                    self.bot.Tickets[ctx.channel.id]["Ending"] = ending
                else:
                    await ctx.channel.send(
                        "This ticket is already closed."
                    )
            else:
                await ctx.channel.send(
                    "You must use this command in either a DM,:"
                    " or as a moderator in a ticket channel, %s"
                    % (ctx.author.mention))


def setup(bot):
    bot.add_cog(Ticket(bot))
