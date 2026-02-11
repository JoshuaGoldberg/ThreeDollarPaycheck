# bot.py
import os
import discord
from discord.ext import tasks
from dotenv import load_dotenv
import spacy
import json
import datetime

from util import *

intents = discord.Intents.all()
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')

client = discord.Client(intents=intents)

banned_set = set(banned_words)
violations = {}
immunities = {}
marked = []

cast_judgement = True

multiplier = 1

nlp = spacy.load('en_core_web_sm')


def save_violations():
    with open("data.txt", "w") as f:
        json.dump({"violations": violations, "immunities": immunities, "marked": marked}, f)


def load_violations():
    global violations
    global immunities
    global marked

    try:
        with open("data.txt", "r") as f:
            data = json.load(f)
            violations = data.get("violations", {})
            violations = {int(k): v for k, v in violations.items()}
            immunities = data.get("immunities", {})
            immunities = {int(k): v for k, v in immunities.items()}
            marked = data.get("marked", [])
    except FileNotFoundError:
        violations = {}
        marked = []


announcement_time = datetime.time(hour=15, minute=0, second=0)


@tasks.loop(time=announcement_time)
async def Announcement():
    guild = client.get_guild(1262846261934035065)

    print("Announcement Sending!")
    channel = client.get_channel(1349929053532061787)
    if channel is None:
        print("Channel not found!")
        return
    await channel.send("Good morning, and welcome to a new day in our wonderful new society.\n"
                       "All current users have gained an immunity token.")
    for member in guild.members:
        update_immunity(member.id, 1)


@client.event
async def on_ready():
    load_violations()
    Announcement.start()
    print(f'{client.user} has connected to Discord!')
    guild = discord.utils.get(client.guilds, name=GUILD)
    print(
        f'{client.user} is connected to the following guild:\n'
        f'{guild.name}(id: {guild.id})'
    )


def is_past_tense(sentence):
    bad = []

    doc = nlp(sentence)

    for token in doc:
        if token.tag_ in ("VBD", "VBN"):
            bad.append(token.text)

    if len(bad) > 0:
        return bad

    return None


def update_violation(userId):
    violation_strength = multiplier
    immune_score = 0

    if immunities.get(userId):
        immune_score = immunities.get(userId)

    immunity_left = 0
    violations_left = 0

    if violation_strength > immune_score:
        violations_left = violation_strength - immune_score
    elif violation_strength <= immune_score:
        immunity_left = immune_score - violation_strength

    immunities.update({userId: immunity_left})

    if userId not in violations:
        violations.update({userId: violations_left})
    else:
        violations.update({userId: violations.get(userId) + violations_left})

    if violations.get(userId) >= 5 and userId not in marked:
        marked.append(userId)


def update_immunity(userId, amount):
    if userId not in immunities:
        immunities.update({userId: amount})
    else:
        immunities.update({userId: immunities.get(userId) + amount})

    save_violations()


def username_to_member(guild: discord.Guild, name: str):
    for member in guild.members:
        if member.name == name:
            return member
    return None


@client.event
async def on_message(message):
    global cast_judgement
    global multiplier

    guild = message.guild
    member = guild.get_member(message.author.id)
    memberId = message.author.id
    botId = client.user.id

    if message.author.name == 'crabchip' and message.content == '>blind':
        violations.clear()
        marked.clear()
        immunities.clear()
        save_violations()
        await message.channel.send("All has been wiped in this land of ash and dust.")
        return

    if message.author.name == 'crabchip' and message.content == '>immune_debug':
        update_immunity(memberId, 100)
        await message.channel.send("Done.")
        return

    if message.author.name == 'crabchip' and message.content.startswith('>absolve '):
        targetedMember = message.content[9:]
        user = username_to_member(guild, targetedMember)

        if not user:
            await message.channel.send("who is that bro.")
            return

        if violations.get(user.id):
            if violations.get(user.id) == 0:
                await message.channel.send("You cannot absolve that which has not committed sin.")
                return
            del violations[user.id]

            if user.id in marked:
                marked.remove(user.id)
            save_violations()
            await message.channel.send(f"The sins of {targetedMember} have been absolved. Watch them closely.")
        else:
            await message.channel.send("You cannot absolve that which has not committed sin.")
        return

    if memberId in marked:
        await message.delete()
        return

    if message.content.startswith('>'):
        if message.author == client.user:
            return

        if message.content == '>test':
            if message.author.name == 'crabchip':
                await message.channel.send("Operations Affirmative")
            return

        if message.content.startswith(">decree ") and message.author.name == 'crabchip':
            value = message.content[7:]

            try:
                val_int = int(value)
                multiplier = val_int
                await message.channel.send(
                    f"The eye has accepted the offering, divine ire has been configured to {multiplier}.")
            except ValueError:
                await message.channel.send("Invalid multiplier, woe upon thee.")

        if message.content == ">switch" and message.author.name == 'crabchip':
            cast_judgement = not cast_judgement

            if cast_judgement:
                eye_status = "watching"
            else:
                eye_status = "closed"

            await message.channel.send(f"The eye of judgement has entered configuration: {eye_status}.")
            return

        if message.content == '>info':
            immune_count = 0
            violation_count = 0

            if immunities.get(memberId):
                immune_count = immunities.get(memberId)

            if violations.get(memberId):
                violation_count = violations.get(memberId)

            await message.channel.send(f"**{member.name}'s Information Panel**\n"
                                       f"Immunity tokens: {immune_count}\n"
                                       f"Violations: {violation_count}")

        if message.content == '>rankings':
            paragons = ""
            okay = ""
            bad = ""
            death = ""

            for guildMember in guild.members:
                if guildMember.id != client.user.id:
                    if guildMember.id in violations:
                        score = violations[guildMember.id]
                        if score <= 2:
                            okay += f"{guildMember.name}: {score}\n"
                        elif score < 5:
                            bad += f"{guildMember.name}: {score}\n"
                        else:
                            death += f"{guildMember.name}: {score}\n"
                    else:
                        paragons += f"{guildMember.name}: 0\n"

            await message.channel.send("**Ranking Board**\n\n"
                                       "**Paragons of Virtue**\n"
                                       f"{paragons if paragons != '' else "N/A\n"}"
                                       "\n**Acceptable Standing**\n"
                                       f"{okay if okay != '' else "N/A\n"}"
                                       "\n**Evildoers**\n"
                                       f"{bad if bad != '' else "N/A\n"}"
                                       "\n**Designated for Execution**\n"
                                       f"{death if death != '' else "N/A\n"}")

        if message.content.startswith('>violations') and cast_judgement:
            status = ""
            targetedMemberId = ""
            targetedMember = ""

            if message.content == ">violations":
                targetedMember = message.author.name
                targetedMemberId = message.author.id
            elif message.content.startswith(">violations "):
                targetedMember = message.content[12:]
                user = username_to_member(guild, targetedMember)

                if not user:
                    await message.channel.send("who is that bro.")
                    return

                targetedMemberId = user.id

            if targetedMemberId in violations:

                count = violations.get(targetedMemberId)

                if count == 1:
                    status = "Being kept under watch."
                if count > 1:
                    status = "Preparing to deploy 4 hours tickle torture."
                if count > 4:
                    status = (f"Violations are in egregious excess. {targetedMember} will be prepped for execution "
                              f"shortly.")

                await message.channel.send(f"Violation count for {targetedMember} is: {count}\n"
                                           f"Status: {status}")
            else:
                await message.channel.send(f"User {targetedMember} is violation free. Follow their example.")
        return
    else:
        if botId is not message.author.id and cast_judgement:

            word = is_past_tense(message.content)
            tense = 'word'

            if word:
                update_violation(message.author.id)
                save_violations()

                await message.channel.send(
                    f"WARNING! Your message contains the following banned {tense}: **{', '.join(word)}**. Remember that "
                    f"speaking of the past is no longer permissible. A violation has "
                    f"been issued. You now have {violations.get(memberId)} violation(s).")

                if memberId in marked:
                    await message.channel.send("Violations have reached excess too large to ignore. You are marked "
                                               "for obliteration.")
    return


client.run(TOKEN)
