import discord
import os
import asyncio
import EternalChecks

from discord.ext import commands

DATABASE_URL = os.environ['DATABASE_URL']


class Lobby(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("Lobby Cog booted successfully")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        leave = (before.channel is not None and after.channel is None)
        move = (before.channel is not None and after.channel != before.channel)
        if (leave or move):

            if (member.id in self.bot.Lobbies):
                channel = self.bot.Lobbies[member.id]["Channel"]
                count = len(channel.members)
                if count == 0:
                    await channel.delete()
                    self.bot.Lobbies.pop(member.id)
                else:
                    tran = False
                    for new in channel.members:
                        print("Transferring channel from %s to %s"
                              % (member, new))

                        if (new.id in self.bot.Lobbies):
                            print("%s already has a lobby. Skipping"
                                  % (new.name))
                            if (count == 1):
                                channel = self.bot.Lobbies[new.id]["Channel"]
                                self.bot.Lobbies[new.id]["Owner"] = \
                                    self.bot.get_user(new.id)
                                new.move_to(channel)
                                await (channel.delete())
                                self.bot.Lobbies.pop(member.id)
                                break
                        else:
                            self.bot.Lobbies[new.id] = \
                                self.bot.Lobbies[member.id]
                            self.bot.Lobbies.pop(member.id)
                            await before.channel.edit(
                                name="%s#%s"
                                % (new.name, new.discriminator)
                            )

                            tran = True
                            break
                    if not tran:
                        await channel.delete()
                        self.bot.Lobbies.pop(member.id)

    @commands.command(name="setlobby")
    @commands.check_any(EternalChecks.is_whitelisted())
    @commands.guild_only()
    async def setlobby(self, ctx, *, limit: int = 0):
        lobby = ctx.channel.category

        print("Set lobby config for %s in %s to %s with limit %s"
              % (lobby, ctx.guild, ctx.channel, limit))

        await self.bot.AddLobbyCategory(
            ctx.guild.id,
            lobby.id,
            ctx.channel.id,
            limit
        )

        await ctx.channel.send(
            "Set the lobby channel for category '%s' to '%s'. Get gaming!"
            % (lobby, ctx.channel.name),
            delete_after=10
        )
        await ctx.message.delete()

    @commands.command(name="stoplobby")
    @commands.check_any(EternalChecks.is_whitelisted())
    @commands.guild_only()
    async def stoplobby(self, ctx):
        lobby = ctx.channel.category

        print("Removing lobby")
        self.bot.Configs[ctx.guild.id]["Lobbies"].pop(lobby.id)

        await ctx.channel.send(
            "Stopped the lobby channel for category '%s'." % (lobby),
            delete_after=10
        )
        await ctx.message.delete()

    @commands.command(name="create")
    @commands.guild_only()
    async def create(self, ctx, *, limit: int = 0):
        if (limit == 1 or limit < 0):
            await ctx.channel.send(
                "Sorry %s. I can't create a lobby for less than 2 people!"
                " To create a non-user limited lobby,"
                " simply don't put a number in the command."
                % (ctx.author.mention)
            )
            await ctx.message.delete()
            return
        elif (limit > 99):
            await ctx.channel.send(
                "Sorry %s. I can't create a lobby for more than 99 people!"
                " To create a non-user limited lobby,"
                " simply don't put a number in the command."
                % (ctx.author.mention),
                delete_after=10
            )
            await ctx.message.delete()
            return

        lobby = ctx.channel.category

        if (lobby.id not in self.bot.Configs[ctx.guild.id]["Lobbies"]):
            await ctx.channel.send(
                "Sorry, %s. The server moderators haven't"
                " set up lobbies for this category yet. Give them a poke."
                % (ctx.author.mention),
                delete_after=10
                )
            await ctx.message.delete()
        else:
            specs = self.bot.Configs[ctx.guild.id]["Lobbies"][lobby.id]
            if (specs["Limit"] != 0 and specs["Limit"] != limit):
                await ctx.channel.send(
                    "Admins have put a specific user amount on this category."
                    " Defaulting to %s" % (specs["Limit"]),
                    delete_after=2
                )

            if (ctx.author.id in self.bot.Lobbies):
                await ctx.channel.send(
                    "You already have a lobby, silly %s."
                    % (ctx.author.mention),
                    delete_after=10
                )
                await ctx.message.delete()
            else:
                if specs["Channel"] != ctx.channel:
                    await ctx.channel.send(
                        "This is not the right channel in this category, %s."
                        % (ctx.author.mention),
                        delete_after=10
                    )
                    await ctx.message.delete()
                    return

                canjoin = discord.PermissionOverwrite(connect=True)
                cannotjoin = discord.PermissionOverwrite(connect=False)
                overwrites = {
                    ctx.guild.default_role: cannotjoin,
                    ctx.author: canjoin
                }
                vc = await ctx.guild.create_voice_channel(
                    name="{0}#{1}".format(ctx.author.name,
                                          ctx.author.discriminator),
                    overwrites=overwrites,
                    category=lobby,
                    user_limit=specs["Limit"])
                link = await vc.create_invite(max_uses=1,
                                              max_age=10)
                await ctx.channel.send(
                    "Channel created %s. It has the same name as you!"
                    " **Join it within the next 10 seconds or"
                    " it will get auto deleted**\n%s"
                    % (ctx.author.mention, link),
                    delete_after=10
                )

                await self.bot.AddLobby(ctx.guild.id, vc.id, ctx.author.id)

                await asyncio.sleep(10)
                try:
                    if (ctx.author not in vc.members):
                        await vc.delete()
                        self.bot.Lobbies.pop(ctx.author.id)
                        await ctx.message.delete()
                    else:
                        overwrites = {
                            ctx.guild.default_role: canjoin,
                            ctx.message.author: canjoin
                        }
                        await vc.edit(overwrites=overwrites)
                        await ctx.message.delete()
                except Exception as e:
                    print(e)
                    await vc.delete()
                    self.bot.Lobbies.pop(ctx.author.id)
                    await ctx.message.delete()

    @commands.command(name="ban")
    @commands.guild_only()
    async def ban(self, ctx, *, user: discord.Member = None):
        if user is None:
            await ctx.channel.send(
                "Oi, %s. You've got to give me a user to ban!"
                % (ctx.author.mention),
                delete_after=10
            )
        else:
            if not (ctx.author.id in self.bot.Lobbies):
                await ctx.channel.send(
                    "You don't have a lobby to ban anyone from, %s"
                    % (ctx.author.mention),
                    delete_after=10
                )
            else:
                channel = self.bot.Lobbies[ctx.author.id]["Channel"]
                if (user in channel.members):
                    if (user.id == ctx.author.id):
                        await ctx.channel.send(
                            "Sorry chief... you can't ban yourself."
                            " You okay there, %s?"
                            % (ctx.author.mention),
                            delete_after=10
                        )
                    else:
                        await user.move_to(None)

                cannotjoin = discord.PermissionOverwrite(connect=False)
                overwrites = channel.overwrites
                if (user in overwrites):
                    if (overwrites[user] == cannotjoin):
                        await ctx.channel.send(
                            "%s, that user is already banned."
                            % (ctx.author.mention),
                            delete_after=10
                        )
                else:
                    overwrites[user] = cannotjoin
                    await channel.edit(overwrites=overwrites)
                    await ctx.channel.send(
                        "%s, that user has been banned."
                        % (ctx.author.mention),
                        delete_after=10
                    )
        await ctx.message.delete()

    @commands.command(name="unban")
    @commands.guild_only()
    async def unban(self, ctx, *, user: discord.Member = None):
        if user is None:
            await ctx.channel.send(
                "Oi, %s. You've got to give me a user to unban!"
                % (ctx.author.mention),
                delete_after=10
            )
        else:
            if not (ctx.author.id in self.bot.Lobbies):
                await ctx.channel.send(
                    "You don't have a lobby to unban anyone from, %s"
                    % (ctx.author.mention),
                    delete_after=10
                )
            else:
                channel = self.bot.Lobbies[ctx.author.id]["Channel"]
                if (user in channel.members):
                    if (user.id == ctx.author.id):
                        await ctx.channel.send(
                            "You cannot ban yourself, therefore"
                            " you cannot unban yourself, %s?"
                            % (ctx.author.mention),
                            delete_after=10
                        )
                    else:
                        await user.move_to(None)

                canjoin = discord.PermissionOverwrite(connect=True)
                overwrites = channel.overwrites
                if (user in overwrites):
                    if (overwrites[user] == canjoin):
                        await ctx.channel.send(
                            "%s, that user is not currently banned."
                            % (ctx.author.mention),
                            delete_after=10
                        )
                else:
                    overwrites[user] = canjoin
                    await channel.edit(overwrites=overwrites)
                    await ctx.channel.send(
                        "%s, that user has been unbanned."
                        % (ctx.author.mention),
                        delete_after=10
                    )
        await ctx.message.delete()

    @commands.command(name="kick")
    @commands.guild_only()
    async def kick(self, ctx, *, user: discord.Member = None):
        if user is None:
            await ctx.channel.send(
                "Oi, %s. You've got to give me a user to kick!"
                % (ctx.author.mention),
                delete_after=10
            )
        else:
            if not (ctx.author.id in self.bot.Lobbies):
                await ctx.channel.send(
                    "You don't have a lobby to kick anyone from, %s"
                    % (ctx.author.mention),
                    delete_after=10
                )
            else:
                channel = self.bot.Lobbies[ctx.author.id]["Channel"]
                if (user in channel.members):
                    if (user.id == ctx.author.id):
                        await ctx.channel.send(
                            "Sorry chief... you can't kick yourself."
                            " You okay there, %s?"
                            % (ctx.author.mention),
                            delete_after=10
                        )
                    else:
                        await user.move_to(None)

                else:
                    await ctx.channel.send(
                        "This person isn't even in your voice channel"
                        " use `ban` to stop them from joining, okay %s?"
                        % (ctx.author.mention),
                        delete_after=10
                    )

        await ctx.message.delete()


def setup(bot):
    bot.add_cog(Lobby(bot))
