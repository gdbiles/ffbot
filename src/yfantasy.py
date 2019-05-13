# Interface for Yahoo Fantasy

import json
import yclient
import xmltodict


YAPI = yclient.YahooAPIClient()


def xml_to_json(xmltext, api):
    convert = json.dumps(xmltodict.parse(xmltext))
    return json.loads(convert)['fantasy_content'][api]


def generate_league_json(league_id, update=False):
    """
    There are certain unchanging characteristics of a given league
    that do not make sense to request on the fly. On first use, this
    module will capture this data and dump into a json file.
    This will greatly speed up requests.

    Likely run this as a daily cron

    :return:
    """
    league = {}
    # First, get season id
    season = get(raw_uri='game/nfl')
    season_id = season['game_id']
    # Get league data for current season
    league_uri = 'league/%s.l.%d' % (season_id, league_id)
    league['data'] = get(raw_uri=league_uri)
    # Get data for each team
    league['teams'] = []
    for i in range(1, int(league['data']['num_teams'])+1):
        team_uri = 'team/' + league['data']['league_key'] + '.t.' + str(i)
        league['teams'].append(get(raw_uri=team_uri))
    with open('ffbot/league.json', 'w') as f:
        json.dump(league, f, indent=4, separators=(',', ': '))
    return league


def get(**kwargs):
    uri = kwargs.get('raw_uri')
    if uri:
        xml = YAPI.send_get(uri=uri)
        return xml_to_json(xml.text, uri.split('/')[0])


# ------------------------------------------------- #
#                    Named Classes                  #
# ------------------------------------------------- #


class Resource(object):
    """
    Resource base class.

    Queries return XML. This will subclass itself into one of the fantasy league
    component classes, convert XML to json structure, and expose json as class
    attributes.
    """
    pass


class League(Resource):

    @property
    def settings(self):
        pass

    @property
    def standings(self):
        pass

    @property
    def scoreboard(self):
        pass


class Teams(Resource):

    @property
    def roster(self):
        pass

    @property
    def matchups(self):
        pass
