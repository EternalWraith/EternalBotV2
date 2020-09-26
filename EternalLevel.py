import discord
import os
import EternalChecks
import io
import requests
import math

from discord.ext import commands

from PIL import Image, ImageDraw, ImageFilter, ImageFont
from datetime import datetime, timedelta
from random import randint

DATABASE_URL = os.environ['DATABASE_URL']


def round_square(pil_img, blur_radius, offset=0):
    offset = blur_radius * 2 + offset
    mask = Image.new("L", pil_img.size, 0)
    draw = ImageDraw.Draw(mask)
    shape = (offset,
             offset,
             pil_img.size[0] - offset,
             pil_img.size[1] - offset)
    draw.ellipse(shape, fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(blur_radius))

    result = pil_img.copy()
    result.putalpha(mask)

    return result


def hexcol(rgb):
    return '#%02x%02x%02x' % (rgb[0], rgb[1], rgb[2])


def star(x, y, r=16):
    g = []
    ri = r*0.38
    for n in range(0, 5):
        px = x-(r*math.cos(math.radians(90+n*72)))
        py = y-(r*math.sin(math.radians(90+n*72)))
        zx = x-(ri*math.cos(math.radians(126+n*72)))
        zy = y-(ri*math.sin(math.radians(126+n*72)))
        g.append((px, py))
        g.append((zx, zy))
    return g


class Level(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("Level Cog booted successfully")

    async def formula(self, guild, base, level):
        exp = 1.5
        return round(base * (level**exp))+base

    async def calculate_xp(self, guild, user):
        level = self.bot.Levels[guild.id]["Levels"][user.id]["Level"]

        b = (self.bot.Levels[guild.id]["Gain"]["Min"]
             + self.bot.Levels[guild.id]["Gain"]["Max"]
             + self.bot.Levels[guild.id]["Gain"]["Voice"]) / 3
        c = (5+15+50)/3
        d = b/c
        e = round(c*d)

        a = await self.formula(guild, e, level)

        return a

    async def xp_from_level(self, guild, level):
        b = (self.bot.Levels[guild.id]["Gain"]["Min"]
             + self.bot.Levels[guild.id]["Gain"]["Max"]
             + self.bot.Levels[guild.id]["Gain"]["Voice"]) / 3
        c = (5+15+50)/3
        d = b/c
        e = round(c*d)

        a = await self.formula(guild, e, level)

        return a

    async def check_lvlup(self, user, guild, xp):
        next_xp = await self.calculate_xp(guild, user)
        print(xp, next_xp)
        if (xp > next_xp):
            xp -= next_xp

            self.bot.Levels[guild.id]["Levels"][user.id]["Level"] += 1
            pre = self.bot.Levels[guild.id]["Levels"][user.id]["Prestige"]
            level = self.bot.Levels[guild.id]["Levels"][user.id]["Level"]

            if (pre >= len(self.bot.Levels[guild.id]["Prestiges"])):
                cap = self.bot.Levels[guild.id]["LevelCap"]["Master"]
            else:
                cap = self.bot.Levels[guild.id]["LevelCap"]["Normal"]

            if level > cap:
                print("%s has reached the cap"
                      % (user.name))
                self.bot.Levels[guild.id]["Levels"][user.id]["Level"] = cap
                return await self.xp_from_level(guild, cap)

            print("%s has leveled up to Level %s"
                  % (user.name,
                     self.bot.Levels[guild.id]["Levels"][user.id]["Level"]))
            return await self.check_lvlup(user, guild, xp)
        return xp

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):

        leave = (before.channel is not None and after.channel is None)
        move = (before.channel is not None and after.channel != before.channel)
        join = (before.channel is None and after.channel is not None)

        guild = None
        if (join):
            if not await self.check_enabled(after.channel.guild):
                return
            guild = after.channel.guild
        else:
            if not await self.check_enabled(before.channel.guild):
                return
            guild = before.channel.guild

        user = (await self.check_xp(guild, member))["User"]
        now = datetime.now()

        def convert_time(time):
            a = time.days * 24   # days > hours
            b = a * 60   # hours > minutes
            c = time.seconds / 60   # seconds > minutes
            return b + c

        if (join):
            self.bot.Levels[guild.id]["Levels"][user.id]["Stay"] = now
            print("%s user joined %s at %s" % (user, after.channel, str(now)))
        elif (move or leave):
            stay = now - self.bot.Levels[guild.id]["Levels"][user.id]["Stay"]
            print(now,
                  self.bot.Levels[guild.id]["Levels"][user.id]["Stay"],
                  stay.seconds)
            spent = convert_time(stay)
            reward = spent/2

            xp = round(self.bot.Levels[guild.id]["Gain"]["Voice"]*reward)
            print("%s spent %s minutes in the voice chat, they earned %s xp"
                  % (user.name, spent, xp))
            xp += self.bot.Levels[guild.id]["Levels"][user.id]["XP"]
            xp = await self.check_lvlup(user, guild, xp)
            self.bot.Levels[guild.id]["Levels"][user.id]["XP"] = xp

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user or not message.guild:
            # stop bot from responding to itself or DMs
            return

        if not await self.check_enabled(message.guild):
            return

        if (message.content.startswith(
                                self.bot.Configs[message.guild.id]["Prefix"]
                                )):
            return

        guild = message.guild
        user = self.bot.get_user(message.author.id)
        print(guild, user)
        xpd = await self.check_xp(guild, user)
        now = datetime.now()

        if xpd["Cooldown"] <= now:
            tenmin = now + timedelta(minutes=10)
            self.bot.Levels[guild.id]["Levels"][user.id]["Cooldown"] = tenmin

            xp = randint(self.bot.Levels[guild.id]["Gain"]["Min"],
                         self.bot.Levels[guild.id]["Gain"]["Max"])
            print("%s earned %s XP" % (user.name, xp))
            xp += self.bot.Levels[guild.id]["Levels"][user.id]["XP"]
            xp = await self.check_lvlup(user, guild, xp)
            self.bot.Levels[guild.id]["Levels"][user.id]["XP"] = xp
        else:
            print("Could not award XP. On cooldown. %s seconds left"
                  % ((xpd["Cooldown"]-now).seconds))

    async def check_enabled(self, guild):
        if guild.id not in self.bot.Levels:
            print("Adding in server {0}".format(guild))
            self.bot.Levels[guild.id] = {
                "Server": guild,
                "Enabled": False,
                "Levels": {},
                "Prestiges": [],
                "LevelCap": {
                    "Normal": 55,
                    "Master": 1000
                },
                "Gain": {
                    "Min": 5,
                    "Max": 50,
                    "Voice": 15
                }
            }
        return self.bot.Levels[guild.id]["Enabled"]

    async def check_xp(self, guild, user):
        if user.id not in self.bot.Levels[guild.id]["Levels"]:
            print("Adding {0} to server {1}".format(user, guild))
            await self.bot.AddLevel(guild, user)
        return self.bot.Levels[guild.id]["Levels"][user.id]

    @commands.command(name="level")
    async def level(self, ctx, *, user: discord.Member = None):
        if not user:
            user = ctx.author

        guild = ctx.guild

        if await self.check_enabled(guild):
            xpd = await self.check_xp(guild, self.bot.get_user(user.id))

            # Open image and resize it
            bg = Image.open("bg.png").convert("RGBA")
            smallsize = (bg.width, bg.height//2)
            overlay = Image.new("RGBA", smallsize, (255, 255, 255, 0))
            bgrz = bg.resize(smallsize)

            # Add PFP to overlay
            avatar = requests.get(user.avatar_url)
            av_img = Image.open(io.BytesIO(avatar.content))
            av_off = 128
            av_szh = smallsize[1]-av_off
            av_pst = av_img.resize((av_szh, av_szh))
            av_cir = round_square(av_pst, 4)
            overlay.paste(av_cir, (av_off//2, av_off//2))

            # Add XP to overlay
            col = hexcol(user.top_role.colour.to_rgb())

            draw = ImageDraw.Draw(overlay)
            shape = [
                (smallsize[1], smallsize[1]-av_off),
                (smallsize[0]-(av_off//2), smallsize[1]-round(av_off*0.75))
            ]
            draw.rectangle(shape, fill="#666666")   # Grey Bar

            needed = await self.calculate_xp(guild, user)
            percentage = (xpd["XP"]/needed)
            length = smallsize[0] - (av_off//2) - smallsize[1]
            bar = round(length*percentage)
            shape = [
                (smallsize[1], smallsize[1]-av_off),
                (smallsize[1]+bar, smallsize[1]-round(av_off*0.75))
            ]
            draw.rectangle(shape, fill=col)   # XP Bar

            # PFP Border
            shape = [
                ((av_off/2)+2, (av_off/2)+2),
                ((smallsize[1]-(av_off//2))-2, (smallsize[1]-(av_off//2))-2)
            ]
            draw.arc(shape, 0, 360, fill=col, width=6)

            # Place XP and Level text on canvas
            ffnt = open("./helvetica.ttf", "rb")
            bfnt = io.BytesIO(ffnt.read())
            ffnt.close()
            fsize = 80
            fnt = ImageFont.truetype(bfnt, fsize)
            pos = (smallsize[1], (smallsize[1]-av_off)-(fsize))
            draw.text(pos, "Level", fill="#ffffff", font=fnt)

            size = draw.textsize("Level ", font=fnt)[0]
            pos = (smallsize[1]+size, (smallsize[1]-av_off)-(fsize))
            draw.text(pos, str(xpd["Level"]), fill=col, font=fnt)

            pre = xpd["Prestige"]

            if (pre >= len(self.bot.Levels[guild.id]["Prestiges"])):
                cap = self.bot.Levels[guild.id]["LevelCap"]["Master"]
            else:
                cap = self.bot.Levels[guild.id]["LevelCap"]["Normal"]
            capped = xpd["Level"] == cap and \
                xpd["XP"] == await self.xp_from_level(
                        guild,
                        cap
                    )

            if not (capped):
                size = draw.textsize("/%s" % (str(needed)), font=fnt)[0]
                pos = (
                    (smallsize[0]-(av_off//2))-size,
                    (smallsize[1]-av_off)-(fsize)
                )
                draw.text(pos, "/%s" % (str(needed)), fill="#ffffff", font=fnt)

                size = draw.textsize(str(xpd["XP"]), font=fnt)[0]+size
                pos = (
                    (smallsize[0]-(av_off//2))-size,
                    (smallsize[1]-av_off)-(fsize)
                )
                draw.text(pos, str(xpd["XP"]), fill=col, font=fnt)
            else:
                size = draw.textsize("Max", font=fnt)[0]
                pos = (
                    (smallsize[0]-(av_off//2))-size,
                    (smallsize[1]-av_off)-(fsize)
                )
                draw.text(pos, "Max", fill="#ffffff", font=fnt)

            # Place Name text on canvas
            ffnt = open("./helvetica.ttf", "rb")
            bfnt = io.BytesIO(ffnt.read())
            ffnt.close()
            fsize = 120
            xfnt = ImageFont.truetype(bfnt, fsize)
            pos = (smallsize[1], round(av_off*0.75))
            draw.text(pos, user.name, fill="#ffffff", font=xfnt)

            size = draw.textsize(user.name, font=xfnt)[0]
            pos = (smallsize[1]+size, round(av_off*0.75))
            draw.text(pos, "#%s" % (user.discriminator), fill=col, font=xfnt)

            # Draw the prestige stars
            radius = 28
            px = smallsize[1]+(radius*1.25)
            py = smallsize[1]-round(radius*1.7)
            for i in range(1, len(self.bot.Levels[guild.id]["Prestiges"])+1):
                if (xpd["Prestige"] < i):
                    starc = "#666666"
                else:
                    starc = col
                draw.polygon(star(px, py, radius), fill=starc)
                px += round(radius*2.5)

            # Compile the image into IO
            output = Image.alpha_composite(bgrz, overlay)
            arr = io.BytesIO()
            output.save(arr, format="PNG")
            arr.seek(0)
            file = discord.File(arr, filename="image.png")

            # Make the embed and send
            emb = discord.Embed()
            emb.set_image(url="attachment://image.png")
            await ctx.channel.send(file=file, embed=emb)
        else:
            await ctx.channel.send(
                "The admins here haven't set up leveling yet."
                " Maybe they will, maybe they won't",
                delete_after=5
            )

        await ctx.message.delete()

    @commands.command(name="enablelevels", aliases=[
                                                "disablelevels",
                                                "togglelevels"
                                            ])
    @commands.check_any(EternalChecks.is_whitelisted())
    @commands.guild_only()
    async def enablelevels(self, ctx):
        guild = ctx.guild
        enabled = not await self.check_enabled(guild)
        self.bot.Levels[guild.id]["Enabled"] = enabled
        print("Enabled levels" if enabled else "Disabled levels")
        if enabled:
            message = "Enabled levels for this server! Get grinding!"
        else:
            message = ("Disabled levels for this server."
                       " All levels are saved and you can"
                       " enable again at any time.")
        await ctx.channel.send(message,
                               delete_after=10)
        await ctx.message.delete()

    @commands.command(name="addprestige")
    @commands.check_any(EternalChecks.is_whitelisted())
    @commands.guild_only()
    async def addprestige(self, ctx, *, role: discord.Role):
        guild = ctx.guild
        print("Adding %s to prestige for %s" % (role, guild))
        if await self.check_enabled(guild):
            await self.bot.AddPrestige(guild, role)

            prestiges = len(self.bot.Levels[guild.id]["Prestiges"])
            pstr = str(prestiges)
            if (pstr.endswith("1") and not pstr.endswith("11")):
                suf = "st"
            elif (pstr.endswith("2") and not pstr.endswith("12")):
                suf = "nd"
            elif (pstr.endswith("3") and not pstr.endswith("13")):
                suf = "rd"
            else:
                suf = "th"

            await ctx.channel.send(
                "Added a %s%s Prestige for you. Good luck grinding to %s"
                % (pstr, suf, role.mention),
                delete_after=10
            )
        await ctx.message.delete()

    @commands.command(name="givexp")
    @commands.check_any(EternalChecks.is_whitelisted())
    @commands.guild_only()
    async def givexp(self, ctx, *, xp: int, user: discord.Member = None):
        if not user:
            user = ctx.author

        guild = ctx.guild

        print("%s earned %s XP" % (user.name, xp))
        xp += self.bot.Levels[guild.id]["Levels"][user.id]["XP"]
        xp = await self.check_lvlup(user, guild, xp)
        self.bot.Levels[guild.id]["Levels"][user.id]["XP"] = xp

    @commands.command(name="prestige")
    @commands.guild_only()
    async def prestige(self, ctx):
        guild = ctx.guild
        user = ctx.author
        if await self.check_enabled(guild):
            xpd = await self.check_xp(guild, self.bot.get_user(user.id))

            cap = self.bot.Levels[guild.id]["LevelCap"]["Normal"]
            prestiges = len(self.bot.Levels[guild.id]["Prestiges"])
            capped = xpd["Level"] == cap and \
                xpd["XP"] == await self.xp_from_level(
                        guild,
                        cap
                    )

            if (xpd["Prestige"] >= prestiges):
                await ctx.channel.send(
                    "You're already in the final prestige, %s"
                    % (user.mention),
                    delete_after=10)
                await ctx.message.delete()
                return

            if (capped):
                self.bot.Levels[guild.id]["Levels"][user.id]["Prestige"] += 1
                pre = self.bot.Levels[guild.id]["Levels"][user.id]["Prestige"]
                self.bot.Levels[guild.id]["Levels"][user.id]["Level"] = 0
                self.bot.Levels[guild.id]["Levels"][user.id]["XP"] = 0
                print(self.bot.Levels[guild.id]["Prestiges"])
                await user.add_roles(
                    *self.bot.Levels[guild.id]["Prestiges"][0:pre+1]
                )
                await ctx.channel.send(
                    "Congrats, %s!"
                    " You just prestiged up to Prestige %s "
                    % (user.mention, pre),
                    delete_after=10)
            else:
                await ctx.channel.send(
                    "You haven't reached the right level to prestige, %s"
                    % (user.mention),
                    delete_after=10)
        await ctx.message.delete()


def setup(bot):
    bot.add_cog(Level(bot))
