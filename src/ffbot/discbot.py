# Interface for Discord

import croniter
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


@bot.command(hidden=True)
async def ping(ctx):
    '''
    This text will be shown in the help command
    '''

    # Get the latency of the bot
    latency = bot.latency  # Included in the Discord.py library
    # Send it to the user
    await ctx.send(latency)


@bot.command(hidden=True)
async def echo(ctx, *, content: str):
    await ctx.send(content)


#
# Define fantasy related commands
# Majority of command function code is in ffbot/utils.py
# in order to keep this file less cluttered
#


@bot.command()
async def prediction(ctx, *, content: str):
    '''
    Make a prediction
    '''
    channel = discord.utils.get(ctx.guild.text_channels, name='predictions')
    await channel.send(ctx.author.mention + ': ' + '`' + content + '`')


@bot.command()
async def mymatchup(ctx, *, content=''):
    '''
    Show your matchup this week (or provide a week number)
    '''
    # Expect `content` contains either None or a list of ints (weeks)
    for item in utils.mymatchup(ctx, content=content):
        await ctx.send(item)


@bot.command(hidden=True)
@commands.has_role("Admin")
async def config(ctx, member: discord.Member, email: str):
    '''
    Wire up discord user to team mapping
    '''
    updated = await utils.set_user_team(bot, member.id, email)
    await ctx.send(updated)


@bot.command()
async def standings(ctx):
    '''
    Current league standings
    '''
    table = utils.standings()
    await ctx.send(table)


@bot.command(hidden=True)
async def test_cron(ctx, content):
    '''
    Test crons
    '''
    if not 'Supreme Leader' in str(ctx.message.author.roles):
        print(ctx.message.author.roles)
        await ctx.send("Hey. Stop that. You can't do that.")
        return
    await ctx.send(getattr(utils, content.strip('cron_'))())

#
# Define crons
#

# TODO figure out a better way to do this
# 5 min
bot.loop.create_task(utils.cron_waiver_monitor('*/5 * * * *', bot))
bot.loop.create_task(utils.cron_trades_monitor('*/5 * * * *', bot))
# Hourly
bot.loop.create_task(utils.cron_update_league('0 * * * *', bot))
# Some days
bot.loop.create_task(utils.cron_week_in_review('0 15 * * 3', bot))


# Grab token from auth.json
AUTHFILE = os.path.realpath(os.path.join(os.curdir, '..', '..', 'auth.json'))

with open(AUTHFILE, 'r') as f:
    token = json.load(f)['discord']['token']
assert token, 'Discord token not found!'


bot.run(token)
