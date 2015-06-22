from collections import namedtuple
import json
import sys

import validictory

from gmusicapi.exceptions import ValidationException
from gmusicapi.protocol.shared import Call, authtypes
from gmusicapi.utils import utils

log = utils.DynamicClientLogger(__name__)

OAuthInfo = namedtuple('OAuthInfo', 'client_id client_secret scope redirect')
oauth = OAuthInfo(
    '228293309116.apps.googleusercontent.com',
    'GL1YV0XMp0RlL7ylCV3ilFz-',
    'https://www.googleapis.com/auth/skyjam',
    'urn:ietf:wg:oauth:2.0:oob'
)


class IOSCall(Call):
    """Abstract base for iOS calls."""

    static_method = 'POST'
    static_url = 'https://www.googleapis.com/rpc'
    static_params = {'prettyPrint': False}

    api_version = 'v1.2'
    required_auth = authtypes(oauth=True)

    # validictory schema for the response
    _res_schema = utils.NotImplementedField

    @classmethod
    def validate(cls, response, msg):
        """Use validictory and a static schema (stored in cls._res_schema)."""
        try:
            return validictory.validate(msg, cls._res_schema)
        except ValueError as e:
            trace = sys.exc_info()[2]
            raise ValidationException(str(e)), None, trace

    @classmethod
    def parse_response(cls, response):
        return cls._parse_json(response.text)

    @classmethod
    def jsonrpc(cls, request_num, **kwargs):
        base = {
            "id": "gtl_%s" % request_num,
            "jsonrpc": "2.0",
            "params": {"hl": "en_US", "refresh": "0", "tier": "aa"},
            "apiVersion": cls.api_version,
        }
        base.update(kwargs)
        return base


class ConfigList(IOSCall):
    """
    {"method":"sj.config.list","id":"gtl_1","jsonrpc":"2.0","params":{"hl":"en_US","refresh":"0","tier":"aa"},"apiVersion":"v1.2"}
    """
    @classmethod
    def dynamic_data(cls, num):
        return json.dumps(cls.jsonrpc(
            num,
            method='sj.config.list',
        ))
