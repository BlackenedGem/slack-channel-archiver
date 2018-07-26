import datetime
import requests
import sys
import json
import time
from jsonschema import validate, ValidationError

from switches import Switches

class Api:
    # region Constants
    URL_FILE_LIST = "https://slack.com/methods/files.list"
    URL_HISTORY_DM = "https://slack.com/api/im.history"
    URL_USER_LIST = "https://slack.com/api/users.list"

    REQUEST_COUNT_HISTORY = 500
    REQUEST_COUNT_USERS = 0

    # Number of times to retry and wait times (in seconds)
    TIMEOUT_RETRIES = 3
    WAIT_TIME_HISTORY_DM = 1
    WAIT_TIME_USER_LIST = 5
    WAIT_TIME_FILE_LIST = 3

    # region Schemas
    SCHEMA_FILE_LIST = {
        "type": "object",
        "properties": {
            "files": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string"
                        },
                        "size": {
                            "type": "integer"
                        },
                        "url_private_download": {
                            "type": "string"
                        },
                        "created": {
                            "type": "integer"
                        }
                    },
                    "required": [
                        "name",
                        "size",
                        "url_private_download",
                        "created"
                    ]
                }
            },
            "paging": {
                "type": "object",
                "properties": {
                    "total": {
                        "type": "integer"
                    },
                    "page": {
                        "type": "integer"
                    },
                    "pages": {
                        "type": "integer"
                    }
                },
                "required": [
                    "total",
                    "page",
                    "pages"
                ]
            }
        },
        "required": [
            "files",
            "paging"
        ]
    }
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
    SCHEMA_USER_LIST = {
        "type": "object",
        "properties": {
            "members": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "profile": {
                            "type": "object",
                            "properties": {
                                "display_name": {"type": "string"}
                            },
                            "required": ["display_name"]
                        }
                    },
                    "required": ["id", "profile"]
                }
            }
        },
        "required": ["members"]
    }
    # endregion
    # endregion

    token = None

    @classmethod
    def get_profiles(cls, cursor=None):
        params = {'list': cls.REQUEST_COUNT_USERS}
        if cursor is not None:
            params['cursor'] = cursor

        response = cls.get_request(cls.URL_USER_LIST, params, schema=cls.SCHEMA_USER_LIST, timeout=cls.WAIT_TIME_USER_LIST)
        return response['members'], cls.get_cursor(response)

    @classmethod
    def get_dm_history(cls, dm, start_time: datetime, end_time: datetime):
        print("Retrieving messages between " + cls.format_time(start_time) + " - " + cls.format_time(end_time))

        params = {
            'channel': dm,
            'inclusive': True,
            'oldest': start_time.timestamp(),
            'latest': end_time.timestamp(),
            'count': cls.REQUEST_COUNT_HISTORY
        }

        # Build up array repeatedly
        messages = []

        while True:
            # Get next batch of messages
            print(f"Querying slack for messages between {params['oldest']} - {params['latest']}")
            content = cls.get_request(cls.URL_HISTORY_DM, params, schema=cls.SCHEMA_HISTORY_DM, timeout=cls.WAIT_TIME_HISTORY_DM)

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

    @classmethod
    def get_file_list(cls):
        pass

    # GET requests all have the same processing logic
    # Also remove requirement to send token for everything
    @classmethod
    def get_request(cls, url: str, params: dict, schema: dict = None, timeout: int = 5):
        num_tries = 0

        while num_tries < cls.TIMEOUT_RETRIES:
            if num_tries > 0:
                print(f"Retrying... (attempt {num_tries + 1})")
            attempt = cls.get_request_once(url, params, schema)
            num_tries += 1

            if attempt is False:
                continue
            if attempt is True:
                print(f"Waiting for {timeout} second(s)")
                time.sleep(timeout)
                continue

            return attempt

        print(f"Maximum attempts exceeded ({cls.TIMEOUT_RETRIES})")
        sys.exit(-1)

    # Returns False for error
    # Returns True for error with 429 code
    @classmethod
    def get_request_once(cls, url: str, params: dict, schema: dict = None):
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
            return False

        if response.status_code == 429:
            print(error_msg)
            print("Status code: " + str(response.status_code) + " (Too many requests)")
            return True

        if response.status_code != 200:
            print(error_msg)
            print("Status code: " + str(response.status_code))
            return False

        if response.text is None:
            print(error_msg)
            print("Response is null")
            return False

        resp_json = json.loads(response.text)
        if 'ok' not in resp_json or ('ok' not in resp_json and 'error' not in resp_json):
            print(error_msg)
            print("Returned JSON was not in the correct format:")
            print(json.dumps(resp_json, indent=4))
            return False

        if not resp_json['ok']:
            print(error_msg)
            print("Response gave 'false' signal for ok. Error provided: " + resp_json['error'])

        if schema is not None:
            try:
                validate(resp_json, schema)
            except ValidationError as e:
                print(error_msg)
                print(e)
                return False

        return resp_json

    @classmethod
    def get_cursor(cls, data: dict):
        if 'response_metadata' not in data:
            return None
        response_metadata = data['response_metadata']

        if 'next_cursor' not in response_metadata:
            return None

        cursor = response_metadata['next_cursor']
        if cursor is None:
            return None
        if len(cursor) == 0:
            return None
        return cursor

    @classmethod
    def format_time(cls, time: datetime):
        return datetime.datetime.strftime(time, Switches.date_mode.value)
