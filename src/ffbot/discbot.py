# Interface for Discord

import discord
import json
import os
import utils

from discord.ext import commands


# Define basic bot setup
prefix = '!'
bot = commands.Bot(command_prefix=prefix)

#
# Define events
#


@bot.event
async def on_ready():
    print("Everything's all ready to go~")


@bot.event
async def on_message(message):
    print("The message's content was", message.content)
    await bot.process_commands(message)


@bot.event
async def on_reaction_add(reaction, user):
    pass


@bot.command()
async def ping(ctx):
    '''
    This text will be shown in the help command
    '''

    # Get the latency of the bot
    latency = bot.latency  # Included in the Discord.py library
    # Send it to the user
    await ctx.send(latency)


@bot.command()
async def echo(ctx, *, content: str):
    await ctx.send(content)


#
# Define fantasy related commands
# Majority of command function code is in ffbot/utils.py
# in order to keep this file less cluttered
#


@bot.command()
async def prediction(ctx, *, content: str):
    channel = discord.utils.get(ctx.guild.text_channels, name='predictions')
    await channel.send(ctx.author.mention + ': ' + '`' + content + '`')


@bot.command()
async def mymatchup(ctx, *, content=''):
    '''
    Show stats for your matchup for a given week(s) (defaults to current)
    '''
    # Expect `content` contains either None or a list of ints (weeks)
    for item in utils.mymatchup(ctx, content=content):
        await ctx.send(item)


@bot.command()
async def matchups(ctx, *, content=''):
    '''
    Show all matchups for a given week (defaults to current)
    '''
    pass


@bot.command()
async def config(ctx, member: discord.Member, email: str):
    '''
    Wire up discord user to team mapping
    '''
    if not 'Supreme Leader' in str(ctx.message.author.roles):
        print(ctx.message.author.roles)
        await ctx.send("Hey. Stop that. You can't do that.")
        return
    if not ctx.message.channel.name == 'config':
        await ctx.send("Wrong channel bucko.")
    updated = utils.set_user_team(member.id, email)
    await ctx.send(updated)


@bot.command()
async def standings(ctx, *, content=''):
    '''
    Current league standings (sortkey default is None)
    '''
    table = utils.standings()
    await ctx.send(table)


# Grab token from auth.json
AUTHFILE = os.path.realpath(os.path.join(os.curdir, '..', '..', 'auth.json'))

with open(AUTHFILE, 'r') as f:
    token = json.load(f)['discord']['token']
assert token, 'Discord token not found!'

crons = [item for item in dir(utils) if item.startswith('cron_')]
for cron in crons:
    bot.loop.create_task(getattr(utils, cron)(bot))

bot.run(token)
