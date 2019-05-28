# Utility functions for discord bot
# Likely we do not want to clutter bot module with formatting operations
# Each discord command should call into a function in this module

import json
import os
import prettytable
import sys

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
    with open(MGR_MAP, 'r') as f:
        try:
            mgr_config = json.load(f)
        except json.JSONDecodeError:
            mgr_config = {}
    return mgr_config


def set_user_team(discord_id, manager_email):
    mgr_config = get_mgr_json()
    mgr_config.update({str(discord_id): manager_email})
    with open(MGR_MAP, 'w') as f:
        json.dump(mgr_config, f, indent=4, separators=(',', ': '))
    output = '```\n'
    output += json.dumps(mgr_config, indent=4, separators=(',', ': '))
    output += '```'
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


def matchups(ctx, content=''):
    pass


def standings(sortkey=None):
    league = yfantasy.get()
    table = prettytable.PrettyTable(border=False)
    table.field_names = ['team', 'pts for', 'pts against', 'w', 'l']
    table.add_row(['-'] * len(table.field_names))
    for team in league.standings['standings']['teams']['team']:
        standing = list()
        ts = team['team_standings']
        standing.append(team['name']),
        standing.append(ts['points_for'])
        standing.append(ts['points_against'])
        standing.append(ts['outcome_totals']['wins'])
        standing.append(ts['outcome_totals']['losses'])
        table.add_row(standing)
    table.align = 'l'
    return '```' + str(table) + '```'


# Want crons:
# - weekly awards 6am Tues
# - transaction check at 6am Tues
# - trades check every 30 min
