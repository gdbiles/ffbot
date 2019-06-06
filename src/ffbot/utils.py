# Utility functions for discord bot
# Likely we do not want to clutter bot module with formatting operations
# Each discord command should call into a function in this module

import asyncio
import datetime
import discord
import json
import os
import prettytable
import sys

from croniter import croniter

# Add src/ to syspath
sys.path.append(os.path.realpath(os.path.join(os.curdir, '..')))
try:
    import yfantasy
except ImportError:
    print('Failed to import yfantasy')
    sys.exit(1)

# Point global to manager map
MGR_MAP = 'discmap.json'

#
# Tools to get/set manager config
#


def get_mgr_json():
    mgr_config = {}
    if MGR_MAP in os.listdir('.'):
        with open(MGR_MAP, 'r') as f:
            mgr_config = json.load(f)
    return mgr_config


async def set_user_team(bot, discord_id, manager_email):
    mgr_config = get_mgr_json()
    mgr_config.update({str(discord_id): manager_email})
    with open(MGR_MAP, 'w') as f:
        json.dump(mgr_config, f, indent=4, separators=(',', ': '))
    output = '```\n'
    output += json.dumps(mgr_config, indent=4, separators=(',', ': '))
    output += '```'
    await update_league(bot)
    return output


def get_user_team(discord_id):
    mgr_config = get_mgr_json()
    return mgr_config.get(str(discord_id))

#
# Discord function tools
#


def mymatchup(ctx, content=''):
    # Expect `content` contains either None or a list of ints (weeks)
    league = yfantasy.get()
    weeks = content or league.current_week
    weeks = [int(w) for w in weeks.split()]
    user_email = get_user_team(ctx.message.author.id)
    result = league.teams_by_email(user_email).matchups(weeks=weeks)
    matchups = result['matchups']['matchup']
    if not isinstance(matchups, list):
        matchups = [matchups]
    for m in matchups:
        output = 'Week %s: %s to %s\n\n' % (m['week'], m['week_start'], m['week_end'])
        for team in m['teams']['team']:
            output += '* ' + team['name'] + '\n'
            output += '-' * 25 + '\n'
            output += f"{'points':<15}{team['team_points']['total']:>10}" + '\n'
            output += f"{'projected':<15}{team['team_projected_points']['total']:>10}" + '\n'
            output += f"{'win probability':<15}{str(100.0 * float(team['win_probability'])) + '%':>10}" + '\n'
            output += '\n'
        output = '```' + output + '```'
        yield output


def standings():
    league = yfantasy.get()
    table = prettytable.PrettyTable(border=False)
    table.field_names = ['team', 'record', 'pts for', 'pts against']
    table.add_row(['-'] * len(table.field_names))
    for team in league.standings['standings']['teams']['team']:
        standing = list()
        ts = team['team_standings']
        standing.append(team['name']),
        standing.append(ts['outcome_totals']['wins'] + ' - ' + ts['outcome_totals']['losses'])
        standing.append(ts['points_for'])
        standing.append(ts['points_against'])
        table.add_row(standing)
    table.align = 'l'
    table.sortby = 'record'
    return '```' + str(table) + '```'


def week_in_review():
    league = yfantasy.get()
    scoreboard = league.scoreboard(max([int(league.current_week)-1, 1]))
    tracker = {'stinkers': []}
    for m in scoreboard['scoreboard']['matchups']['matchup']:
        teams = [{'name': t['name'], 'points': t['team_points']['total']} for t in m['teams']['team']]
        teams = sorted(teams, key=lambda i: i['points'])
        winner, loser = teams
        tracker.setdefault('worst week', loser)
        if loser['points'] < tracker['worst week']['points']:
            tracker['worst week'] = loser
        tracker.setdefault('best week', winner)
        if winner['points'] > tracker['best week']['points']:
            tracker['best week'] = winner
        tracker['stinkers'].extend([t for t in teams if float(t['points']) < 60.0])

    sb = scoreboard['scoreboard']['matchups']['matchup'][0]
    output = 'Week in Review: Week %s: %s to %s\n' % (sb['week'], sb['week_start'], sb['week_end'])
    output += '\n'
    output += '\N{CROWN} ' + f"{tracker['best week']['name']:<20}{tracker['best week']['points']:>10}"
    output += ' \N{CROWN}'
    output += '\n\n'
    output += '\N{PILE OF POO} ' + f"{tracker['worst week']['name']:<20}{tracker['worst week']['points']:>10}"
    output += ' \N{PILE OF POO}'
    output += '\n\n'

    stinkers = [t for t in sorted(tracker['stinkers'], key=lambda i: i['points']) if t != tracker['worst week']]
    if stinkers:
        output += 'These teams also deserve shoutouts for indescribably poor showings:\n'
        for team in stinkers:
            output += f"{team['name']:<20}{team['points']:>10}" + '\n'

    return '```' + output + '```'


async def update_league(bot):
    league = yfantasy.get()
    yfantasy.create_yleague_json(int(league.league_id), update=True)
    for disc_id, email in get_mgr_json().items():
        team = league.teams_by_email(email)
        user = discord.utils.get(bot.get_all_members(), id=int(disc_id))
        # Set division role
        division_roles = ['Acorn League East', 'Darby League West']
        role_name = division_roles[int(team.division_id) - 1]
        role = discord.utils.get(user.guild.roles, name=role_name)
        for old_role in user.roles:
            if old_role.name in division_roles:
                await user.remove_roles(old_role)
        await user.add_roles(role)
        # Set team nickname
        await user.edit(nick=team.name)


def waiver_monitor(bot):
    pass


def trades_monitor(bot):
    pass

#
# Crons
#


class CronJob(object):
    def __init__(self, cron):
        self.cron = croniter(cron, self.now)

    @property
    def now(self):
        return datetime.datetime.now()

    @property
    def time_to_next(self):
        diff = self.cron.next(datetime.datetime) - self.now
        return diff.seconds


# Weekly review 6am Weds
async def cron_week_in_review(cron, bot):
    await bot.wait_until_ready()
    league = yfantasy.get()
    channel = discord.utils.get(bot.get_all_channels(), name='general')
    cron_obj = CronJob(cron)
    while not bot.is_closed():
        if league.start_date <= cron_obj.now.strftime('%Y-%m-%d') <= league.end_date:
            await channel.send(week_in_review())
        await asyncio.sleep(cron_obj.time_to_next)


# Grab new waiver claims each morning
async def cron_waiver_monitor(cron, bot):
    pass


# Check for new trades every 15 min
async def cron_trades_monitor(cron, bot):
    pass


# Update league every night at midnight
async def cron_update_league(cron, bot):
    await bot.wait_until_ready()
    cron_obj = CronJob(cron)
    while not bot.is_closed():
        await update_league(bot)
        await asyncio.sleep(cron_obj.time_to_next)
