import datetime

import requests
import sys
import json
from jsonschema import validate, ValidationError

from switches import Switches

class Api:
    # region Constants
    URL_HISTORY_DM = "https://slack.com/api/im.history"
    URL_USER_INFO = "https://slack.com/api/users.info"

    REQUEST_COUNT = 500

    # region Schemas
    SCHEMA_HISTORY_DM = {
        "type": "object",
        "properties": {
            "messages": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string"},
                        "ts": {"type": "string"},
                        "user": {"type": "string"},
                        "text": {"type": "string"}
                    },
                    "required": ["type", "ts"]
                }
            },
            "has_more": {"type": "boolean"}
        },
        "required": ["messages", "has_more"]
    }
    SCHEMA_USER_INFO = {
        "type": "object",
        "properties": {
            "user": {
                "type": "object",
                "properties": {
                    "profile": {
                        "type": "object",
                        "properties": {
                            "display_name": {"type": "string"}
                        },
                        "required": ["display_name"]
                    }
                },
                "required": ["profile"]
            }
        },
        "required": ["user"]
    }
    # endregion
    # endregion

    token = None

    @classmethod
    def get_username(cls, user_id: str):
        print(f"Retrieving display name for user ID: {user_id}")
        response = cls.get_request(cls.URL_USER_INFO, {'user': user_id}, cls.SCHEMA_USER_INFO)
        return response['user']['profile']['display_name']

    @classmethod
    def get_dm_history(cls, dm, start_time: datetime, end_time: datetime):
        print("Retrieving messages between " + cls.format_time(start_time) + " - " + cls.format_time(end_time))

        params = {
            'channel': dm,
            'inclusive': True,
            'oldest': start_time.timestamp(),
            'latest': end_time.timestamp(),
            'count': cls.REQUEST_COUNT
        }

        # Build up array repeatedly
        messages = []

        while True:
            # Get next batch of messages
            print(f"Querying slack for messages between {params['oldest']} - {params['latest']}")
            content = cls.get_request(cls.URL_HISTORY_DM, params, cls.SCHEMA_HISTORY_DM)

            next_messages = content['messages']
            if len(next_messages) == 0:
                break

            # Make sure first/last messages don't overlap
            if len(messages) > 0 and next_messages[0]['ts'] == messages[-1]['ts']:
                messages.extend(next_messages[1:])
            else:
                messages.extend(next_messages)

            # Update params and print status if there are more messages to get
            if not content['has_more']:
                print("Retrieved " + str(len(messages)) + " messages")
                break

            print("Messages retrieved so far: " + str(len(messages)))
            params['latest'] = next_messages[-1]['ts']

        return messages

    # GET requests all have the same processing logic
    # Also remove requirement to send token for everything
    @classmethod
    def get_request(cls, url: str, params: dict, schema: dict = None):
        # variables
        error_msg = f"Exception with request for URL: {url}"
        params['token'] = cls.token

        # Go through obvious failure points
        # noinspection PyBroadException
        try:
            response = requests.get(url, params)
        except requests.exceptions.RequestException as e:
            print(error_msg)
            print(e)
            sys.exit(-1)

        if response.status_code != 200:
            print(error_msg)
            print("Status code: " + response.status_code)
            sys.exit(-1)

        if response.text is None:
            print(error_msg)
            print("Response is null")
            sys.exit(-1)

        resp_json = json.loads(response.text)
        if 'ok' not in resp_json or ('ok' not in resp_json and 'error' not in resp_json):
            print(error_msg)
            print("Returned JSON was not in the correct format:")
            print(json.dumps(resp_json, indent=4))
            sys.exit(-1)

        if not resp_json['ok']:
            print(error_msg)
            print("Response gave 'false' signal for ok. Error provided: " + resp_json['error'])

        if schema is not None:
            try:
                validate(resp_json, schema)
            except ValidationError as e:
                print(error_msg)
                print(e)
                sys.exit(-1)

        return resp_json

    @classmethod
    def format_time(cls, time: datetime):
        return datetime.datetime.strftime(time, Switches.date_mode.value)
