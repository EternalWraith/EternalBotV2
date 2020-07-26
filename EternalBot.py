import discord
import os
import psycopg2

from discord.ext import commands
from datetime import datetime

DATABASE_URL = os.environ['DATABASE_URL']


async def get_prefix(bot, message):
    if not message.guild:
        return commands.when_mentioned_or("e2-")(bot, message)
    else:
        if message.guild.id not in bot.Configs:
            await bot.AddConfig(message.guild.id)

        prefix = bot.Configs[message.guild.id]["Prefix"]
        return commands.when_mentioned_or(prefix)(bot, message)


class EternalBot(commands.Bot):

    def __init__(self, command_prefix, description):
        super(__class__, self).__init__(command_prefix=command_prefix,
                                        description=description)

        self.Conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        self.Cursor = self.Conn.cursor()

    async def Setup(self):
        # Configs: stores server configs
        await self.GrabConfigs()
        # Tickets: stores open mod tickets
        await self.GrabTickets()
        # Lobbies: stores open VC lobbies
        await self.GrabLobbies()
        # Levels: stores server level info
        await self.GrabLevels()

    async def GrabConfigs(self):
        self.Configs = {}
        self.Cursor.execute("SELECT * FROM Config")
        results = self.Cursor.fetchall()
        for config in results:
            guildId = int(config[1])
            self.Configs[guildId] = {
                # "ID": int(config[0]),
                "Server": self.get_guild(guildId),
                "Audit": None if not config[2] else
                bot.get_channel(int(config[2])),
                "Prefix": config[3],
                "Lobbies": {},
                "Inbox": None if not config[5] else
                bot.get_channel(int(config[5])),
                "Tickets": int(config[6]),
                "Whitelist": [],
                "Lang": "English"
            }

            for lobby in config[4]:
                lobbyId = int(lobby[0])
                channelId = int(lobby[1])
                self.Configs[guildId]["Lobbies"][lobbyId] = {
                    "Category": bot.get_channel(lobbyId),
                    "Channel": bot.get_channel(channelId),
                    "Limit": int(lobby[2])
                }

            for role in config[7]:
                self.Configs[guildId]["Whitelist"].append(
                    self.Configs[guildId]["Server"].get_role(int(role))
                )

    async def AddConfig(self, guildId):
        self.Configs[guildId] = {
            # "ID": null,
            "Server": self.get_guild(guildId),
            "Audit": None,
            "Prefix": "e2-",
            "Lobbies": {},
            "Inbox": None,
            "Tickets": 0,
            "Whitelist": []
        }

    async def AddLobbyCategory(self, guildId, categoryId, channelId, limit):
        self.Configs[guildId]["Lobbies"][categoryId] = {
            "Category": bot.get_channel(categoryId),
            "Channel": bot.get_channel(channelId),
            "Limit": limit
        }

    async def GrabTickets(self):
        self.Tickets = {}
        self.Cursor.execute("SELECT * FROM Tickets")
        results = self.Cursor.fetchall()
        for ticket in results:
            guildId = int(ticket[1])
            ownerId = int(ticket[2])
            channelId = int(ticket[3])
            channel = bot.get_channel(channelId)

            if not ticket[4]:
                ending = None
            else:
                ending = await channel.fetch_message(int(ticket[4]))

            self.Tickets[channelId] = {
                # "ID": int(ticket[0]),
                "Server": bot.get_guild(guildId),
                "Channel": channel,
                "Owner": bot.get_user(ownerId),
                "Ending": ending
            }

    async def AddTicket(self, guildId, channelId, ownerId):
        self.Tickets[channelId] = {
            # "ID": int(ticket[0]),
            "Server": bot.get_guild(guildId),
            "Channel": bot.get_channel(channelId),
            "Owner": bot.get_user(ownerId),
            "Ending": None
        }
        self.Configs[guildId]["Tickets"] += 1

    async def GrabLobbies(self):
        self.Lobbies = {}
        self.Cursor.execute("SELECT * FROM Lobbies")
        results = self.Cursor.fetchall()
        for lobby in results:
            guildId = int(lobby[1])
            channelId = int(lobby[2])
            ownerId = int(lobby[3])

            self.Lobbies[ownerId] = {
                # "ID": int(lobby[0]),
                "Server": bot.get_guild(guildId),
                "Channel": bot.get_channel(channelId),
                "Owner": bot.get_user(ownerId)
            }

    async def AddLobby(self, guildId, channelId, ownerId):
        self.Lobbies[ownerId] = {
            # "ID": int(ticket[0]),
            "Server": bot.get_guild(guildId),
            "Channel": bot.get_channel(channelId),
            "Owner": bot.get_user(ownerId)
        }

    async def GrabLevels(self):
        self.Levels = {}
        self.Cursor.execute("SELECT * FROM Levels")
        results = self.Cursor.fetchall()
        for server in results:
            guildId = int(server[1])
            self.Levels[guildId] = {
                # "ID": int(server[0]),
                "Server": bot.get_guild(guildId),
                "Enabled": server[2],
                "Levels": {},
                "Prestiges": [],
                "LevelCap": {
                    "Normal": int(server[4][0]),
                    "Master": int(server[4][1])
                },
                "Gain": {
                    "Min": int(server[6][0]),
                    "Max": int(server[6][1]),
                    "Voice": int(server[6][2])
                }
            }

            if (self.Levels[guildId]["Enabled"]):
                for member in server[3]:
                    user = bot.get_user(int(member[0]))
                    if (user):
                        self.Levels[guildId]["Levels"][user.id] = {
                            "User": user,
                            "Prestige": int(member[1]),
                            "Level": int(member[2]),
                            "XP": int(member[3])
                        }
                for member in server[7]:
                    timeformat = "%Y-%m-%d %H:%M:%S.%f"
                    user = bot.get_user(int(member[0]))
                    if (user):
                        self.Levels[guildId]["Levels"][user.id].update({
                            "Cooldown": datetime.strptime(
                                member[1],
                                timeformat
                            ),
                            "Stay": datetime.strptime(
                                member[2],
                                timeformat
                            )
                        })
                for prestige in server[5]:
                    guild = self.Levels[guildId]["Server"]
                    role = guild.get_role(int(prestige))
                    self.Levels[guildId]["Prestiges"].append(role)

    async def AddPrestige(self, guild, role):
        self.Levels[guild.id]["Prestiges"].append(role)

    async def AddLevel(self, guild, user):
        self.Levels[guild.id]["Levels"][user.id] = {
            "User": user,
            "Prestige": 0,
            "Level": 0,
            "XP": 0,
            "Cooldown": datetime.now(),
            "Stay": datetime.now()
        }

    async def CompileLobbyCategories(self, guildId):
        output = []
        for lobby in self.Configs[guildId]["Lobbies"]:
            input = self.Configs[guildId]["Lobbies"][lobby]
            output.append([
                input["Category"].id,
                input["Channel"].id,
                input["Limit"]
            ])
        return output

    async def CompileRoleWhitelist(self, guildId):
        output = []
        for role in self.Configs[guildId]["Whitelist"]:
            output.append(role.id)
        return output

    async def CompileUserLevels(self, guildId):
        output = []
        for user in self.Levels[guildId]["Levels"]:
            input = self.Levels[guildId]["Levels"][user]
            output.append([
                input["User"].id,
                input["Prestige"],
                input["Level"],
                input["XP"]
            ])
        return output

    async def CompilePrestigeRoles(self, guildId):
        output = []
        for role in self.Levels[guildId]["Prestiges"]:
            output.append(role.id)
        return output

    async def CompileUserCooldowns(self, guildId):
        output = []
        for user in self.Levels[guildId]["Levels"]:
            input = self.Levels[guildId]["Levels"][user]
            output.append([
                str(input["User"].id),
                str(input["Cooldown"]),
                str(input["Stay"])
            ])
        return output

    async def close(self):
        await super().close()

        print("Saving Config")
        self.Cursor.execute("DELETE FROM Config")
        for c in self.Configs:
            config = self.Configs[c]
            if not (config["Audit"]):
                audit = None
            else:
                audit = config["Audit"].id
            if not (config["Inbox"]):
                inbox = None
            else:
                inbox = config["Inbox"].id
            code = """
INSERT INTO Config (ServerID,
                    AuditID,
                    Prefix,
                    Lobbies,
                    TicketID,
                    "Tickets",
                    WhiteList)
VALUES (%s, %s, %s, %s, %s, %s, %s)"""
            values = (
                config["Server"].id,
                audit,
                config["Prefix"],
                await self.CompileLobbyCategories(c),
                inbox,
                config["Tickets"],
                await self.CompileRoleWhitelist(c)
            )
            self.Cursor.execute(code, values)
        self.Conn.commit()

        print("Saving Levels")
        self.Cursor.execute("DELETE FROM Levels")
        for c in self.Levels:
            level = self.Levels[c]
            code = """
INSERT INTO Levels (ServerID,
                    Enabled,
                    Users,
                    LevelCap,
                    Prestiges,
                    XPGain,
                    Cooldowns)
VALUES (%s, %s, %s, %s, %s, %s, %s)"""
            values = (
                level["Server"].id,
                level["Enabled"],
                await self.CompileUserLevels(c),
                [
                    level["LevelCap"]["Normal"],
                    level["LevelCap"]["Master"]
                ],
                await self.CompilePrestigeRoles(c),
                [
                    level["Gain"]["Min"],
                    level["Gain"]["Max"],
                    level["Gain"]["Voice"]
                ],
                await self.CompileUserCooldowns(c)
            )
            self.Cursor.execute(code, values)
        self.Conn.commit()

        print("Saving Tickets")
        self.Cursor.execute("DELETE FROM Tickets")
        for c in self.Tickets:
            ticket = self.Tickets[c]
            if not ticket["Ending"]:
                ending = None
            else:
                ending = ticket["Ending"].id
            code = """
INSERT INTO Tickets (ServerID,
                    OwnerID,
                    ChannelID,
                    EndingID)
VALUES (%s, %s, %s, %s)"""
            values = (
                ticket["Server"].id,
                ticket["Owner"].id,
                ticket["Channel"].id,
                ending
            )
            self.Cursor.execute(code, values)
        self.Conn.commit()

        print("Saving Lobbies")
        self.Cursor.execute("DELETE FROM Lobbies")
        for c in self.Lobbies:
            lobby = self.Lobbies[c]
            code = """
INSERT INTO Tickets (ServerID,
                    VCID,
                    OwnerID)
VALUES (%s, %s, %s)"""
            values = (
                lobby["Server"].id,
                lobby["Channel"].id,
                lobby["Owner"].id
            )
            self.Cursor.execute(code, values)
        self.Conn.commit()

        print("Done saving. Closing.")


bot = EternalBot(command_prefix=get_prefix, description="EternalBot v2")
bot.load_extension("EternalLobby")
bot.load_extension("EternalTicket")
bot.load_extension("EternalModerate")
bot.load_extension("EternalLevel")

bot.load_extension("EternalDefcon")


@bot.event
async def on_ready():
    await bot.Setup()
    print("We logged in as {0.user}".format(bot))

    game = discord.Game(name="Nibbling on Cookies",
                        type=1,
                        url="http://twitch.tv/TheRealWraithGG")

    print(bot.Configs)
    print(bot.Lobbies)
    print(bot.Tickets)
    print(bot.Levels)
    await bot.change_presence(activity=game)


@bot.event
async def on_message(message):
    if message.author == bot.user:
        # stop bot from responding to itself
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
    await ctx.channel.send("Here you go friend! One invite just for you!\n%s"
                           % (discord.utils.oauth_url(app_info.id, perms)))


bot.run(os.environ["BOT_TOKEN"])
