"""Calls made by the web client."""

import json
import sys
from urllib import quote_plus

import validictory

from gmusicapi.newprotocol.shared import Call, Transaction, ValidationException


class WcCall(Call):
    """Abstract base for web client calls."""

    _base_url = 'https://play.google.com/music/'

    #Added to the url after _base_url.
    #Expected to end with a forward slash.
    _suburl = 'services/'

    #Most webclient calls require an xt token in the params.
    #This signals to the session to include it.
    send_xt = True

    @classmethod
    def build_transaction(cls, *args, **kwargs):
        #template out the transaction; most of it is shared.
        return Transaction(
            cls._request_factory({
                'url': cls._base_url + cls._suburl + cls.__name__.lower(),
                'data': 'json=' + quote_plus(
                    json.dumps(cls._build_json(*args,**kwargs)))
            }),
            cls.verify_res_schema,
            cls.verify_res_success
        )

    @classmethod
    def verify_res_schema(cls, res):
        """Use validictory and a static schema (stored in cls.res_schema)."""
        try:
            return validictory.validate(res, cls.res_schema)
        except ValueError as e:
            trace = sys.exc_info()[2]
            raise ValidationException(e.message), None, trace

    @staticmethod
    def verify_res_success(res):
        #Failed responses always have a success=False key.
        #Some successful responses do not have a success=True key, however.
        #TODO remove utils.call_succeeded

        if 'success' in res.keys():
            return res['success']
        else:
            return True

    @classmethod
    def parse_response(cls, text):
        return cls.parse_json(text)


class AddPlaylist(WcCall):
    """Creates a new playlist."""

    method = 'POST'

    res_schema = {"type": "object",
                  "properties": {
                      "id": {"type": "string"},
                      "title": {"type": "string"},
                      "success": {"type": "boolean"},
                  },
                  "additionalProperties": False}

    @staticmethod
    def _build_json(title):
        """
        :param title: the title of the playlist to create.
        """
        return {"title": title}
