import discord, psycopg2, os, asyncio, EternalTables, EternalChecks, io, requests, math

from discord.ext import commands
from EternalTables import InterpretLevels, GetData, CompileUsers, CompilePrestige, CompileCooldowns

from PIL import Image, ImageDraw, ImageFilter, ImageFont
from datetime import datetime, timedelta
from random import randint

DATABASE_URL = os.environ['DATABASE_URL']

def round_square(pil_img, blur_radius, offset=0):
    offset = blur_radius * 2 + offset
    mask = Image.new("L", pil_img.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((offset, offset, pil_img.size[0] - offset, pil_img.size[1] - offset), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(blur_radius))

    result = pil_img.copy()
    result.putalpha(mask)

    return result

def calculate_xp(level, data):
    a = round((4 * (level**3))/5)
    b = (data["Gain"]["Text"]["Min"]+data["Gain"]["Text"]["Max"]+data["Gain"]["Voice"])/3
    c = (5+15+50)/3
    d = b/c
    e = round (c*d)+a
    return e

def hexcol(rgb):
    return '#%02x%02x%02x' % (rgb[0], rgb[1], rgb[2])

def star(x, y, r=16):
    g = []
    ri = r*0.38
    for n in range(0,5):
        px = x-(r*math.cos(math.radians(90+n*72)))
        py = y-(r*math.sin(math.radians(90+n*72)))
        zx = x-(ri*math.cos(math.radians(126+n*72)))
        zy = y-(ri*math.sin(math.radians(126+n*72)))
        g.append((px,py))
        g.append((zx,zy))
    return g

class Level(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print ("Level Cog booted successfully")


    async def check_lvlup(self, user, data, config, xp):
        print(xp, calculate_xp(data["Levels"][user]["Level"], data))
        if (xp > calculate_xp(data["Levels"][user]["Level"], data)):
            xp -= calculate_xp(data["Levels"][user]["Level"], data)
            
            data["Levels"][user]["Level"] += 1
            print("%s has leveled up to Level %s" % (user.name, data["Levels"][user]["Level"]))        
            return await self.check_lvlup(user, data, config, xp)
        return xp

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        
        leave = (before.channel is not None and after.channel is None)
        move = (before.channel is not None and after.channel != before.channel)
        join = (before.channel is None and after.channel is not None)

        guild = None
        if (join):
            if not await self.check_enabled(guild=after.channel.guild):
                return
            guild = after.channel.guild
        else: 
            if not await self.check_enabled(guild=before.channel.guild):
                return
            guild = before.channel.guild

        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        cursor = conn.cursor()
        config = GetData(self.bot, guild)
        cursor.execute("SELECT * FROM Levels WHERE ServerID='{0}'".format(guild.id))
        results = cursor.fetchall()
        data = InterpretLevels(self.bot, results[0])

        user = self.bot.get_user(member.id)
        xpd = await self.check_xp(user, data)
        now = datetime.now()

        def convert_time(time):
            a = time.days * 24 # days > hours
            print("a)",a)
            b = a * 60 # hours > minutes
            print("b)",b)
            b += time.seconds / 60 # seconds > minutes
            print("o)",b)
            return b
        
        if (join):
            data["Levels"][user]["Stay"] = now
            print("%s user joined at %s" % (user.name, str(now)))
            code = """UPDATE Levels SET Cooldowns=%s WHERE ServerID='%s'"""
            values = (CompileCooldowns(data["Levels"]), data["Server"].id)
            cursor.execute(code, values)
            conn.commit()
            cursor.close()
            conn.close()
        elif (move or leave):
            print(now, data["Levels"][user]["Stay"],(now - data["Levels"][user]["Stay"]).seconds)
            stay =  now - data["Levels"][user]["Stay"]
            spent = convert_time(stay)
            reward = spent/2
            
            xp = round(data["Gain"]["Voice"]*reward)
            print("%s spent %s minutes in the voice chat, they earned %s xp" % (user.name, spent, xp))
            xp += data["Levels"][user]["XP"]
            xp = await self.check_lvlup(user, data, config, xp)
            data["Levels"][user]["XP"] = xp
            code = """UPDATE Levels SET Users=%s WHERE ServerID='%s'"""
            values = (CompileUsers(data["Levels"]), data["Server"].id)
            cursor.execute(code, values)
            conn.commit()
            cursor.close()
            conn.close()
            

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user or not message.guild:
            #stop bot from responding to itself
            return

        if not await self.check_enabled(message):
            return
        
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        cursor = conn.cursor()
        config = GetData(self.bot, message.guild)

        if message.content.startswith(config["Prefix"]):
            return

        cursor.execute("SELECT * FROM Levels WHERE ServerID='{0}'".format(message.guild.id))
        results = cursor.fetchall()
        data = InterpretLevels(self.bot, results[0])

        user = self.bot.get_user(message.author.id)
        xpd = await self.check_xp(user, data)
        now = datetime.now()
        
        if xpd["Cooldown"] <= now:
            data["Levels"][user]["Cooldown"] = data["Levels"][user]["Cooldown"] + timedelta(minutes=10)
            
            xp = randint(data["Gain"]["Text"]["Min"],data["Gain"]["Text"]["Max"])
            print("%s earned %s XP" % (user.name, xp))
            xp += data["Levels"][user]["XP"]
            xp = await self.check_lvlup(user, data, config, xp)
            data["Levels"][user]["XP"] = xp
            code = """UPDATE Levels SET Users=%s, Cooldowns=%s WHERE ServerID='%s'"""
            values = (CompileUsers(data["Levels"]), CompileCooldowns(data["Levels"]), data["Server"].id)
            cursor.execute(code, values)
            conn.commit() 
            
        else:
            print("Could not award XP. On cooldown. %s seconds left" % ((xpd["Cooldown"]-now).seconds))
        cursor.close()
        conn.close()

    async def check_enabled(self, ctx=None, guild=None):
        if not guild:
            guild = ctx.guild
        
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Levels WHERE ServerID='{0}'".format(guild.id))
        results = cursor.fetchall()
        if (len(results) == 0):
            print("Adding in server {0}".format(guild))
            code = """INSERT INTO Levels (ServerID, Enabled, Users, LevelCap, Prestiges, XPGain, Cooldowns)
VALUES (%s, %s, %s, %s, %s, %s, %s)"""
            values = (guild.id, False, [], [55,1000], [], [5,50,15], [])
            cursor.execute(code, values)
            conn.commit()

            cursor.execute("SELECT * FROM Levels WHERE ServerID='{0}'".format(guild.id))
            results = cursor.fetchall()
        result = results[0]
        data = InterpretLevels(self.bot, result)
        cursor.close()
        conn.close()
        return data["Enabled"]

    async def check_xp(self, user, data):
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        cursor = conn.cursor()
        if user in data["Levels"]:
            return data["Levels"][user]
        else:
            data["Levels"][user] = {}
            data["Levels"][user]["Prestige"] = 0
            data["Levels"][user]["Level"] = 0
            data["Levels"][user]["XP"] = 0
            data["Levels"][user]["Cooldown"] = datetime.now()
            data["Levels"][user]["Stay"] = datetime.now()
            code = """UPDATE Levels SET Users=%s, Cooldowns=%s WHERE ServerID='%s'"""
            values = (CompileUsers(data["Levels"]), CompileCooldowns(data["Levels"]), data["Server"].id)
            cursor.execute(code, values)
            conn.commit()
            cursor.close()
            conn.close()
            return data["Levels"][user]
            

    @commands.command(name="level")
    async def level(self, ctx, *, user: discord.Member=None):
        if not user:
            user = ctx.author



        if await self.check_enabled(ctx):
            conn = psycopg2.connect(DATABASE_URL, sslmode='require')
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM Levels WHERE ServerID='{0}'".format(ctx.guild.id))
            results = cursor.fetchall()
            data = InterpretLevels(self.bot, results[0])
            xpdata = await self.check_xp(self.bot.get_user(user.id), data) 
            
            bg = Image.open("bg.png").convert("RGBA")
            smallsize = (bg.width, bg.height//2)
            overlay = Image.new("RGBA", smallsize, (255,255,255,0))
            #bg.thumbnail(smallsize, Image.ANTIALIAS)
            bgrz = bg.resize(smallsize)
            #print(bg.size, overlay.size)

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
            shape = [(smallsize[1], smallsize[1]-av_off), (smallsize[0]-(av_off//2), smallsize[1]-round(av_off*0.75))]
            draw.rectangle(shape, fill="#666666") # Grey Bar

            needed = calculate_xp(xpdata["Level"], data)
            percentage = (xpdata["XP"]/needed)
            length = smallsize[0] - (av_off//2) - smallsize[1]
            bar = round(length*percentage)
            shape = [(smallsize[1], smallsize[1]-av_off), (smallsize[1]+bar, smallsize[1]-round(av_off*0.75))]
            draw.rectangle(shape, fill=col) # XP Bar

            # PFP Border
            shape = [((av_off/2)+2,(av_off/2)+2),((smallsize[1]-(av_off//2))-2,(smallsize[1]-(av_off//2))-2)]
            draw.arc(shape, 0, 360, fill=col, width=6) 

            # Place XP and Level text on canvas
            ffnt = open("./helvetica.ttf", "rb")
            bfnt = io.BytesIO(ffnt.read())
            ffnt.close()
            fsize = 80
            fnt = ImageFont.truetype(bfnt , fsize)
            pos = (smallsize[1],(smallsize[1]-av_off)-(fsize))
            draw.text(pos, "Level", fill="#ffffff", font=fnt)

            size = draw.textsize("Level ", font=fnt)[0]
            pos = (smallsize[1]+size,(smallsize[1]-av_off)-(fsize)) 
            draw.text(pos, str(xpdata["Level"]), fill=col, font=fnt)

            size = draw.textsize("/%s" % (str(needed)), font=fnt)[0]
            pos = ((smallsize[0]-(av_off//2))-size,(smallsize[1]-av_off)-(fsize))
            draw.text(pos, "/%s" % (str(needed)), fill="#ffffff", font=fnt)

            size = draw.textsize(str(xpdata["XP"]), font=fnt)[0]+size
            pos = ((smallsize[0]-(av_off//2))-size,(smallsize[1]-av_off)-(fsize))
            draw.text(pos, str(xpdata["XP"]), fill=col, font=fnt)

            # Place Name text on canvas
            ffnt = open("./helvetica.ttf", "rb")
            bfnt = io.BytesIO(ffnt.read())
            ffnt.close()
            fsize = 120
            xfnt = ImageFont.truetype(bfnt , fsize)
            pos = (smallsize[1], round(av_off*0.75))
            draw.text(pos, user.name, fill="#ffffff", font=xfnt)

            size = draw.textsize(user.name, font=xfnt)[0]
            pos = (smallsize[1]+size, round(av_off*0.75))
            draw.text(pos, "#%s" % (user.discriminator), fill=col, font=xfnt)

            # Draw the prestige stars
            radius = 28
            px = smallsize[1]+(radius*1.25)
            py = smallsize[1]-round(radius*1.7)
            for i in range(1,len(data["Prestiges"])+1):
                if (xpdata["Prestige"] < i):
                    starc = "#666666"
                else:
                    starc = col 
                draw.polygon(star(px,py,radius), fill=starc)
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
            await ctx.channel.send("The admins here haven't set up leveling yet. Maybe they will, maybe they won't",
                                   delete_after=5)

        await ctx.message.delete()

    @commands.command(name="enablelevels")
    @commands.check_any(EternalChecks.is_whitelisted())
    @commands.guild_only()
    async def enablelevels(self, ctx):
        enabled = await self.check_enabled(ctx)
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        cursor = conn.cursor()
        code = """UPDATE Levels SET Enabled=%s WHERE ServerID='%s'"""
        values = (not enabled, ctx.guild.id)
        cursor.execute(code, values)
        conn.commit()
        cursor.close()
        conn.close()
        print("Enabled levels" if not enabled else "Discabled levels")
        await ctx.channel.send("Enabled levels for this server! Get grinding!" if not enabled else "Disabled levels for this server. All levels are saved and you can enable again at any time.",
                               delete_after=10)
        await ctx.message.delete()

    @commands.command(name="addprestige")
    @commands.check_any(EternalChecks.is_whitelisted())
    @commands.guild_only()
    async def addprestige(self, ctx, *, role: discord.Role):
        print(role)
        if await self.check_enabled(ctx):
            conn = psycopg2.connect(DATABASE_URL, sslmode='require')
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM Levels WHERE ServerID='{0}'".format(ctx.guild.id))
            results = cursor.fetchall()
            data = InterpretLevels(self.bot, results[0])
            data["Prestiges"].append(role)
            code = """UPDATE Levels SET Prestiges=%s WHERE ServerID='%s'"""
            values = (CompilePrestige(data["Prestiges"]), ctx.guild.id)
            cursor.execute(code, values)
            conn.commit()
            cursor.close()
            conn.close()
            l = len(data["Prestiges"])
            if (str(l).endswith("1")):
                suf = "st"
            elif (str(l).endswith("2")):
                suf = "nd"
            elif (str(l).endswith("3")):
                suf = "rd"
            else:
                suf = "th"
            await ctx.channel.send("Added a %s%s Prestige for you. Good luck grinding to %s" % (l,suf,role.mention),
                               delete_after=10)
        await ctx.message.delete()

def setup(bot):
    bot.add_cog(Level(bot))
