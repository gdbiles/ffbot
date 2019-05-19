# Interface for Yahoo Fantasy

import json
import os
import yclient
import xmltodict


YAPI = yclient.YahooAPIClient()
LEAGUE_JSON_PATH = os.path.realpath(os.path.join(os.path.curdir, 'league.json'))


def xml_to_json(xmltext, api):
    """
    Convert xml retured by YAPI to json

    :param xmltext: xml as string
    :param api: fantasy Yresource api
    :return:
    """
    # need to dump and load in order to access as dict
    api = api.lower()
    convert = json.dumps(xmltodict.parse(xmltext), indent=4, separators=(',', ': '))
    logging.info(convert)
    content = json.loads(convert)['fantasy_content']
    # sometimes info is nested in other content
    # if we want something in a deeper level, provide a map to the resource
    if nest_map:
        for k in nest_map.split(','):
            content = content.get(k, {})
    return content.get(api, {})


def get_yleague_json(path=LEAGUE_JSON_PATH):
    """
    Retrieve yahoo league json file if it exists; create if it
    does not.

    :return:
    """
    with open(path, 'r') as f:
        try:
            yleague = json.load(f)
        except json.JSONDecodeError:
            # If league.json file does not exist or is empty
            return None
    return yleague


def create_yleague_json(league_id, update=False):
    """
    There are certain unchanging characteristics of a given league
    that do not make sense to request on the fly. On first use, this
    module will capture this data and dump into a json file.
    This will greatly speed up requests.

    Likely run this as a daily cron

    :return:
    """
    if get_yleague_json():
        assert update, 'Must be updating league.json to make changes!'
    # First, get season id
    season = get(raw_uri='game/nfl')
    season_id = season['game_id']
    # Get league data for current season
    league_uri = 'league/%s.l.%d' % (season_id, league_id)
    league = get(raw_uri=league_uri)
    # Get data for each team
    league['teams'] = []
    for i in range(1, int(league['num_teams'])+1):
        team_uri = 'team/' + league['league_key'] + '.t.' + str(i)
        league['teams'].append(get(raw_uri=team_uri))
    with open(LEAGUE_JSON_PATH, 'w') as f:
        json.dump(league, f, indent=4, separators=(',', ': '))
    return league


def get(**kwargs):
    """
    Primary entry point for python API client

    :param kwargs: currently supports: <empty>, raw_uri, raw_data
    :return:
    """
    if not kwargs:
        return YResource(json=get_yleague_json(), api='League')
    raw_uri = kwargs.get('raw_uri')
    if raw_uri:
        api = raw_uri.split('/')[0]
        xml = YAPI.send_get(uri=raw_uri)
        json = xml_to_json(xml.text, api)
        if kwargs.get('raw_data'):
            return json
        return YResource(json=json, api=api)


# ------------------------------------------------- #
#                    Named Classes                  #
# ------------------------------------------------- #


class YResource(object):
    """
    YResource base class.

    Queries return XML. This will subclass itself into one of the fantasy league
    component classes, convert XML to json structure, and expose json as class
    attributes.
    """
    def __init__(self, **kwargs):
        self.logger = yclient.logger
        self.json = kwargs.get('json', {})

    def __new__(cls, **kwargs):
        cls = globals().get(kwargs.get('api'), cls)
        return super(YResource, cls).__new__(cls)

    def __getattr__(self, name):
        return self.json.get(name)

    def __hash__(self):
        return hash(str(self))

    def __str__(self):
        return '<%s: %s>' % (self.__class__.__name__, self.id)

    def keys(self):
        return self.json.keys()


class League(YResource):

    @property
    def league_id(self):
        return self.data.get('league_id')

    @property
    def league_key(self):
        return self.data.get('league_key')


class Team(YResource):
    pass


class Transaction(YResource):
    pass
