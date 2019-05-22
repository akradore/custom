import json
import requests
import logging

from .. import constants

_logger = logging.getLogger(__name__)


class Auth:
    def __init__(self):
        pass


class Sign(Auth):
    def __init__(self, app_id, app_secret):
        self.app_id = app_id
        self.app_secret = app_secret

    def get_app_id(self):
        return self.app_id

    def get_app_secret(self):
        return self.app_secret


class Token(Auth):
    def __init__(self, app_id, app_secret, kdt_id):
        self.app_id = app_id
        self.app_secret = app_secret
        self.authority_id = kdt_id

    @classmethod
    def DEFAULT_SETUP_TOKEN(cls):
        return cls(
            constants.YOUZAN_CLIENT_ID,
            constants.YOUZAN_CLIENT_SECRET,
            constants.YOUZAN_AUTHORITY_ID
        )

    def get_token(self):

        params = {
            "grant_id": self.authority_id,
            "client_secret": self.app_secret,
            "authorize_type": "silent",
            "client_id": self.app_id
        }

        r = self.send_request(constants.YOUZAN_AUTHORIZE_URL, 'POST', params, [])
        response = r.json()

        _logger.debug('Youzan AccessToken Response: %s' % response)

        if not (response['code'] == 200 and response['success']):
            raise ValueError('Youzan AccessToken Error: %s' % response['message'])

        # default expired in 8 days
        return response['data']['access_token']

    def send_request(self, url, method, param_map, files):
        headers_map = {
            'User-Agent': 'X-YZ-Client 3.0.0 - Python',
            'Content-Type': 'application/json;charset=UTF-8'
        }

        req_data = json.dumps(param_map)
        if method.upper() == 'GET':
            return requests.get(url=url, params=req_data, headers=headers_map)

        elif method.upper() == 'POST':
            return requests.post(url=url, data=req_data, files=files, headers=headers_map)
