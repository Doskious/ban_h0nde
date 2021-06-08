#!/usr/bin/python
"""
# WARNING!
# DO not use this script for malicious purposes!
# Author: daegontaven - taven#0001
# License: Public Domain
# README
# I have resigned from using discord indefinitely to pursue schoolwork.
# As such I will not be maintaining this script anymore.
# How to  Install
1 - Download Python 3.7 or 3.6   : https://www.python.org/downloads/
2 - Run this command  : python3 -m pip install discord.py
3 - Run this command  : python3  discord-ban-bot.py
4 - Invite bot to the servers you want to ban members from.
5 - Wait until banning is done. Don't close the terminal. This may take a while.
"""


import discord

TOKEN = ""      # Put your Bot token here
SKIP_BOTS = False


client = discord.Client()

@client.event
async def on_ready():
    print('Logged in!')
    for member in client.get_all_members():
        if member.bot and SKIP_BOTS:
            continue
        await member.ban(reason="Banned by BanBot", delete_message_days=7)
        print(f"Banned {member.display_name}!")
    print("Banning is complete!")

client.run(TOKEN)