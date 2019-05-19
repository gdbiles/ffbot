# Module for interacting with Yahoo Fantasy Sports API
#
# May build out functionality for dealing with authorizing
# app on Yahoo dev, as this process was not straightforward.
#
# Before using this module, user must have
#  1. Created app with Yahoo Dev
#  2. Registered app with properties defined in README
#  3. Filled out auth.json

import json
import logging
import os
import oauthlib
import requests_oauthlib
import webbrowser

from oauthlib.common import urldecode


logger = logging.getLogger(__name__)
AUTHFILE = os.path.abspath(os.path.join(os.path.realpath(__file__), '..', '..', 'auth.json'))


def load_auth(t=None):
    with open(AUTHFILE, 'r') as f:
        auth = json.load(f)
    if not t:
        return auth
    return auth[t]


# ------------------------------------------------- #
#                     API Classes                   #
# ------------------------------------------------- #

class YahooAPIBase(requests_oauthlib.OAuth2Session):
    """
    Root API object
    This will allow us to interact with Yahoo's OAuth2-enabled web API
    and seamlessly update tokens via requests_oauth2lib.
    """
    token_url = 'https://api.login.yahoo.com/oauth2/get_token'
    base_url = 'https://fantasysports.yahooapis.com/v2/'

    def __init__(self):
        # Load auth config into class
        self.logger = logger
        self.auth_cfg = load_auth(t='yahoo')

        assert self.auth_cfg['client_id']
        assert self.auth_cfg['client_secret']

        # Try to pick up token data from auth
        refresh_token = self.auth_cfg.get('token', {}).get('refresh_token', None)

        # Define base class requirements
        auth = (self.auth_cfg['client_id'], self.auth_cfg['client_secret'])
        refresh_kwargs = {
            'client_id': self.auth_cfg['client_id'],
            'redirect_uri': 'oob',
        }

        super(YahooAPIBase, self).__init__(
            client_id=self.auth_cfg['client_id'],
            auto_refresh_url=self.token_url,
            redirect_uri='oob',
            auto_refresh_kwargs=refresh_kwargs,
        )

        # Try to refresh token using whatever we have in auth.json
        # This should imitate a "persistent" token to user (i.e. user
        # does not have to re-authorize token for same environment)
        if refresh_token:
            self.refresh_token(self.token_url, refresh_token=refresh_token, auth=auth)

        # Try to pick up token from auth file
        if not self.token:
            try:
                self.fetch_token(YahooAPIBase.token_url,
                                 code=self.auth_cfg['code'],
                                 auth=auth
                                 )
                self.__save_token()
            except Exception as e:
                if not (isinstance(e, oauthlib.oauth2.InvalidGrantError)
                        or 'INVALID_AUTHORIZATION_CODE' in str(e)):
                    raise
                print(e)
                self.generate_new_auth_code()
                self.__init__()

    def __save_token(self):
        """
        Save token state locally so on env reload, we don't have to manually
        reauthorize

        :return:
        """
        auth = load_auth()
        with open(AUTHFILE, 'w') as f:
            auth['yahoo']['token'] = dict(self.token)
            json.dump(auth, f, indent=4, separators=(',', ': '))
        self.logger.info('New token updated in auth')

    def generate_new_auth_code(self):
        """Generate new auth token via code entry

        :return:
        """
        self.logger.info('Auth code has expired... generating link to renew')
        url = 'https://api.login.yahoo.com/oauth2/request_auth?' \
              'client_id=%s&redirect_uri=oob&response_type=code' % self.auth_cfg['client_id']
        self.logger.info(url)
        webbrowser.open(url)
        code = input('Enter the code generated by popup: ')
        self.logger.info('Writing new code to auth.json')
        auth = load_auth()
        with open(AUTHFILE, 'w') as f:
            auth['yahoo']['code'] = code
            json.dump(auth, f, indent=4, separators=(',', ': '))
        self.__save_token()
        self.logger.info('Authfile updated. Renewing %s' % __class__.__name__)

    def refresh_token(self, token_url, refresh_token=None, body="", auth=None,
                      timeout=None, headers=None, verify=True, proxies=None, **kwargs):
        """Fetch a new access token using a refresh token.
        :param token_url: The token endpoint, must be HTTPS.
        :param refresh_token: The refresh_token to use.
        :param body: Optional application/x-www-form-urlencoded body to add the
                     include in the token request. Prefer kwargs over body.
        :param auth: An auth tuple or method as accepted by `requests`.
        :param timeout: Timeout of the request in seconds.
        :param headers: A dict of headers to be used by `requests`.
        :param verify: Verify SSL certificate.
        :param proxies: The `proxies` argument will be passed to `requests`.
        :param kwargs: Extra parameters to include in the token request.
        :return: A token dict
        """
        if not token_url:
            raise ValueError("No token endpoint set for auto_refresh.")

        if not oauthlib.oauth2.is_secure_transport(token_url):
            raise InsecureTransportError()

        refresh_token = refresh_token or self.token.get("refresh_token")

        self.logger.debug(
            "Adding auto refresh key word arguments %s.", self.auto_refresh_kwargs
        )
        kwargs.update(self.auto_refresh_kwargs)
        body = self._client.prepare_refresh_body(
            body=body, refresh_token=refresh_token, scope=self.scope, **kwargs
        )
        self.logger.debug("Prepared refresh token request body %s", body)

        if headers is None:
            headers = {
                "Accept": "application/json",
                "Content-Type": ("application/x-www-form-urlencoded;charset=UTF-8"),
            }

        r = self.post(token_url, data=dict(urldecode(body)), auth=auth, timeout=timeout,
                      headers=headers, verify=verify, withhold_token=True, proxies=proxies)
        self.logger.debug("Request to refresh token completed with status %s.", r.status_code)
        self.logger.debug("Response headers were %s and content %s.", r.headers, r.text)
        self.logger.debug(
            "Invoking %d token response hooks.",
            len(self.compliance_hook["refresh_token_response"]),
        )
        for hook in self.compliance_hook["refresh_token_response"]:
            log.debug("Invoking hook %s.", hook)
            r = hook(r)

        self.token = self._client.parse_request_body_response(r.text, scope=self.scope)
        if not "refresh_token" in self.token:
            self.logger.debug("No new refresh token given. Re-using old.")
            self.token["refresh_token"] = refresh_token

        # Save token state
        self.__save_token()
        return self.token


class YahooAPIClient(YahooAPIBase):

    def __init__(self, base_url='https://fantasysports.yahooapis.com/fantasy/v2/'):
        assert base_url.endswith('/')
        assert base_url.startswith('https')
        self.base_url = base_url
        super(YahooAPIClient, self).__init__()

    def send_get(self, uri):
        url = self.base_url + uri
        return self.__send_request(url, method='GET')

    def send_post(self, uri, data={}):
        url = self.base_url + uri
        return self.__send_request(url, data=data, method='POST')

    def __send_request(self, url, data=None, method=''):
        # current Yahoo app is auth'd for readonly, though we may
        # want to support POST going forward
        if method == 'GET':
            try:
                r = self.request(url=url, method=method)
                if not r.ok:
                    r.raise_for_status()
                return r
            except Exception as e:
                # TODO: catch specific exceptions and retry pending error type
                self.logger.exception('Encountered %s on %s %s' % (e, url, method))
        if method == 'POST':
            raise NotImplementedError('POST is not supported!')
