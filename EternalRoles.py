import discord
import typing
import os
import EternalChecks

from discord.ext import commands

DATABASE_URL = os.environ['DATABASE_URL']


class Roles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("Roles Cog booted successfully")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        guild = self.bot.get_guild(payload.guild_id)
        channel = self.bot.get_channel(payload.channel_id)
        emoji = payload.emoji
        member = payload.member
        messageid = payload.message_id

        if (member.id == self.bot.user.id):
            return

        if (messageid not in self.bot.Configs[guild.id]["RoleReacts"]):
            return

        if (emoji.is_unicode_emoji()):
            print("String Emoji")
            print(emoji, emoji.name.encode('unicode-escape'))

            if (emoji.name in
               self.bot.Configs[guild.id]["RoleReacts"][messageid]):
                await member.add_roles(
                    (self.bot.Configs[guild.id]["RoleReacts"]
                                     [messageid][emoji.name]["Role"])
                )
                return
        elif (emoji.is_custom_emoji()):
            print("Custom Emoji")

            if (emoji.id in
               self.bot.Configs[guild.id]["RoleReacts"][messageid]):
                await member.add_roles(
                    (self.bot.Configs[guild.id]["RoleReacts"]
                                     [messageid][emoji.id]["Role"])
                )
                return

        message = await channel.fetch_message(messageid)
        await message.remove_reaction(emoji, member)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        guild = self.bot.get_guild(payload.guild_id)
        # channel = self.bot.get_channel(payload.channel_id)
        emoji = payload.emoji
        member = guild.get_member(payload.user_id)
        messageid = payload.message_id

        if (member.id == self.bot.user.id):
            return

        if (messageid not in self.bot.Configs[guild.id]["RoleReacts"]):
            return

        if (emoji.is_unicode_emoji()):
            print("String Emoji")
            print(emoji, emoji.name.encode('unicode-escape'))

            if (emoji.name in
               self.bot.Configs[guild.id]["RoleReacts"][messageid]):
                await member.remove_roles(
                    (self.bot.Configs[guild.id]["RoleReacts"]
                                     [messageid][emoji.name]["Role"])
                )
        elif (emoji.is_custom_emoji()):
            print("Custom Emoji")

            if (emoji.id in
               self.bot.Configs[guild.id]["RoleReacts"][messageid]):
                await member.remove_roles(
                    (self.bot.Configs[guild.id]["RoleReacts"]
                                     [messageid][emoji.id]["Role"])
                )

    @commands.command(name="addreact")
    @commands.check_any(EternalChecks.is_whitelisted())
    async def addreact(self, ctx,
                       emoji: typing.Union[
                        discord.Emoji, discord.PartialEmoji, str],
                       message: discord.Message,
                       role: discord.Role):
        if message.channel.id != ctx.channel.id:
            await ctx.channel.send("This command must be executed in the same"
                                   " channel as the message you're trying"
                                   " to add a react to, %s"
                                   % (ctx.author.mention),
                                   delete_after=10)
            return

        if message.id not in (self.bot.Configs[ctx.guild.id]
                                              ["RoleReacts"]):
            self.bot.Configs[ctx.guild.id]["RoleReacts"][message.id] = {
                "Message": message,
                "Channel": ctx.channel
            }
        if type(emoji) in [discord.Emoji, discord.PartialEmoji]:
            print(emoji.id, emoji.name)
            (self.bot.Configs[ctx.guild.id]["RoleReacts"]
                             [message.id][emoji.id]) = {
                "Type": "emj",
                "Emoji": emoji,
                "Role": role
            }
        elif type(emoji) is str:
            print(emoji, emoji.encode('unicode-escape'))
            emojiid = emoji  # .encode('unicode-escape')
            (self.bot.Configs[ctx.guild.id]["RoleReacts"]
                             [message.id][emojiid]) = {
                "Type": "str",
                "Role": role
            }

        await message.add_reaction(emoji)
        await ctx.message.delete()
        await ctx.channel.send("We added that role to your message, %s"
                               % (ctx.author.mention),
                               delete_after=10)

    @commands.command(name="removereact")
    @commands.check_any(EternalChecks.is_whitelisted())
    async def removereact(self, ctx,
                          emoji: typing.Union[
                           discord.Emoji, discord.PartialEmoji, str],
                          message: discord.Message):
        if message.channel.id != ctx.channel.id:
            await ctx.channel.send("This command must be executed in the same"
                                   " channel as the message you're trying"
                                   " to add a react to, %s"
                                   % (ctx.author.mention),
                                   delete_after=10)
            return

        if message.id not in (self.bot.Configs[ctx.guild.id]
                                              ["RoleReacts"]):
            await ctx.channel.send("This message has no role reactions."
                                   " Mods can add some with `addreact`, "
                                   "%s"
                                   % (ctx.author.mention),
                                   delete_after=10)
            return

        if emoji not in (self.bot.Configs[ctx.guild.id]["RoleReacts"]
                         [message.id]):
            await ctx.channel.send("That emoji is not attached to this"
                                   " message, %s"
                                   % (ctx.author.mention),
                                   delete_after=10)
            return

        (self.bot.Configs[ctx.guild.id]["RoleReacts"]
                         [message.id]).pop(emoji)

        await message.clear_reaction(emoji)
        await ctx.message.delete()
        await ctx.channel.send("We removed that role to your message, %s"
                               % (ctx.author.mention),
                               delete_after=10)


def setup(bot):
    bot.add_cog(Roles(bot))
