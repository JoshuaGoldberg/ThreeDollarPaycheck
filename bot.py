# bot.py
import os
import discord
from dotenv import load_dotenv
import spacy

from util import *

intents = discord.Intents.all()
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')

client = discord.Client(intents=intents)

banned_set = set(banned_words)
violations = {}
marked = []

cast_judgement = True

multiplier = 1

nlp = spacy.load('en_core_web_sm')


@client.event
async def on_ready():
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
    if userId not in violations:
        violations.update({userId: (1 * multiplier)})
    else:
        violations.update({userId: violations.get(userId) + (1 * multiplier)})

    if violations.get(userId) >= 5 and userId not in marked:
        marked.append(userId)


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
        await message.channel.send("All has been wiped in this land of ash and dust.")
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

                await message.channel.send(
                    f"WARNING! Your message contains the following banned {tense}: **{', '.join(word)}**. Remember that "
                    f"speaking of the past is no longer permissible. A violation has "
                    f"been issued. You now have {violations.get(memberId)} violation(s).")

                if memberId in marked:
                    await message.channel.send("Violations have reached excess too large to ignore. You are marked "
                                               "for obliteration.")
    return


client.run(TOKEN)
