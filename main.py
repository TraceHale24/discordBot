from collections import namedtuple
from datetime import datetime, timedelta
import discord
from dotenv import load_dotenv
import requests
import os
import sqlite3
import random
import schedule
import time
import threading

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
print(TOKEN)
OPTIONS = [('🟥', '\U0001F7E5'), ('🟦', '\U0001F7E6'), ('🟨', '\U0001F7E8'),
           ('🟩', '\U0001F7E9'), ('🟧', '\U0001F7E7'), ('🟪', '\U0001F7EA')]

intents = discord.Intents.all()
client = discord.Client(intents=intents)

# Read in users
with open("data.txt", "r") as f:
    cols = f.readline().split()
    User = namedtuple('User', cols)
    users = [User(*row.split()) for row in f.readlines()]
users.sort()

def create_reminder(content):
    reminder_content = content.split(" ")
    if len(reminder_content) < 3:
        return "Structure is /reminder 2024-11-3T17:30 Message Goes Here"

    reminder_date_time = reminder_content[1].split("T")
    reminder_message = " ".join(reminder_content[2:])

    reminder_date = reminder_date_time[0].split("-")
    reminder_time = reminder_date_time[1].split(":")

    time_to_send = datetime(int(reminder_date[0]), int(reminder_date[1]), int(reminder_date[2]), int(reminder_time[0]), int(reminder_time[1]))
    sent = False
    tag_everyone = True

    # Insert the data into the events table
    conn = sqlite3.connect("DiscordBot.db")
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO events (timeToSend, sent, message, tagEveryone)
        VALUES (?, ?, ?, ?)
    ''', (time_to_send, sent, reminder_message, tag_everyone))

    # Commit the changes and close the connection
    conn.commit()
    conn.close()

    return "Reminder Created"

def create_scoreboard(content):
    COLUMNS = ['kd', 'winRate', 'minutesPlayed']
    TIME_WINDOW = 'lifetime' if 'lifetime' in content else 'season'
    for m in ['solo', 'duo', 'squad']:
        if m in content:
            MODE = m
            break
    else:
        MODE = 'overall'

    # generate scoreboard message
    res = ['```',
           '{} scoreboard ({})'.format(MODE, TIME_WINDOW),
           '{:<7}{:>7}{:>9}{:>10}'.format('name', *COLUMNS[:-1], 'playTime')
           ]
    for user in users:
        headers = {'Authorization': os.getenv('API_KEY')}
        params = {'name': user.user,
                  'accountType': user.accountType,
                  'timeWindow': TIME_WINDOW,
                  'image': 'none'
                  }

        r = requests.get('https://fortnite-api.com/v2/stats/br/v2',
                         params=params,
                         headers=headers).json()

        print(r)
        if r['status'] != 200:
            continue

        stats = r['data']['stats']['all'][MODE]

        if stats:
            res.append('{:<7}{:>7.3f}{:>9.3f}{:>10}'.format(
                user.name, *[stats[col] for col in COLUMNS]))
        else:
            res.append('{:<7}{:>7}{:>9}{:>10}'.format(
                user.name, *['NONE']*3))

    res.append('```')
    return '\n'.join(res)

def check_events():
    """Check for events whose timeToSend has passed and process them."""
    now = datetime.now()
    conn = sqlite3.connect("mydatabase.db")
    cursor = conn.cursor()
    cursor.execute('''
        SELECT message FROM events WHERE timeToSend <= ? AND sent = 0
    ''', (now,))
    
    events_to_send = cursor.fetchall()
    
    for event in events_to_send:
        message = event[0]
        # Here you would add your logic to send the message (e.g., to a Discord channel)
        print(f"Sending message: {message}")
        
        # Update the event to mark it as sent
        cursor.execute('''
            UPDATE events SET sent = 1 WHERE message = ?
        ''', (message,))
    
    conn.commit()
    conn.close()

def run_scheduler():
    """Runs the scheduler to check events every 30 minutes."""
    schedule.every(30).minutes.do(check_events)
    
    while True:
        schedule.run_pending()
        time.sleep(1)

@client.event
async def on_ready():
    print(f'{client.user.name} has connected to Discord!')

# Start the scheduler in a separate thread
threading.Thread(target=run_scheduler, daemon=True).start()

@client.event
async def on_member_join(member):
    await member.create_dm()
    await member.dm_channel.send(
        f'Hi {member.name}, welcome to my Discord Server!')

@client.event
async def on_member_update(before, after):
    if after.activity and (before.activity != after.activity):
        if "fortnite" in after.activity.name.lower():
            channel = client.get_channel(945836161451061258)
            await channel.send(fortnite_blast(after.nick))
        elif "pycharm" in after.activity.name.lower():
            channel = client.get_channel(956305809736888421)
            await channel.send(f"{after.display_name} is working on my body ;)")

        else:
            channel = client.get_channel(945782914019377154)
            await channel.send(f"{after.display_name} has started doing {after.activity.name}")

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith("/scoreboard"):
        m = await message.channel.send("Generating scoreboard...")
        res = create_scoreboard(message.content)
        await m.edit(content=res)

    if message.content.startswith("/reminder"):
        result = create_reminder(message.content)
        await message.reply(result)

    ur_mom = random.randint(0, 100)
    if ur_mom == 69 or ("who" in message.content and not random.randint(0, 4)):
        await message.reply("ur mom lol")

    if "faith" in message.content.lower():
        await message.reply("Faith is Trace's Hottie")

client.run(TOKEN)
