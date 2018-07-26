import datetime
import requests
import sys
import json
import time
from jsonschema import validate, ValidationError

from switches import Switches

class Api:
    # region Constants
    URL_FILE_LIST = "https://slack.com/api/files.list"
    URL_HISTORY_DM = "https://slack.com/api/im.history"
    URL_USER_LIST = "https://slack.com/api/users.list"

    REQUEST_COUNT_HISTORY = 500
    REQUEST_COUNT_FILES = 100
    REQUEST_COUNT_USERS = 0

    # Number of times to retry and wait times (in seconds)
    TIMEOUT_RETRIES = 3
    WAIT_TIME_TIER_2 = 5
    WAIT_TIME_TIER_3 = 3
    WAIT_TIME_TIER_4 = 1

    # region Schemas
    SCHEMA_FILE_LIST = {
        "$schema": "http://json-schema.org/draft-04/schema#",
        "type": "object",
        "properties": {
            "files": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "created": {
                            "type": "integer"
                        },
                        "title": {
                            "type": "string"
                        },
                        "filetype": {
                            "type": "string"
                        },
                        "user": {
                            "type": "string"
                        },
                        "size": {
                            "type": "integer"
                        },
                        "url_private_download": {
                            "type": "string"
                        },
                        "ims": {
                            "type": "array",
                            "items": {
                                "items": {}
                            }
                        }
                    },
                    "required": [
                        "created",
                        "title",
                        "filetype",
                        "user",
                        "size",
                        "url_private_download",
                        "ims"
                    ]
                }
            },
            "paging": {
                "type": "object",
                "properties": {
                    "total": {
                        "type": "integer"
                    },
                    "count": {
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
                    "count",
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

        response = cls.get_request(cls.URL_USER_LIST, params, schema=cls.SCHEMA_USER_LIST, timeout=cls.WAIT_TIME_TIER_2)
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
            content = cls.get_request(cls.URL_HISTORY_DM, params, schema=cls.SCHEMA_HISTORY_DM, timeout=cls.WAIT_TIME_TIER_4)

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
    def get_file_list(cls, dm, start_time: datetime, end_time: datetime):
        page = 1
        params = {
            'count': cls.REQUEST_COUNT_FILES,
            'ts_from': start_time.timestamp(),
            'ts_to': end_time.timestamp()
        }

        num_files = 0
        file_list = []
        while True:
            # Get next page of files
            params['page'] = page
            print(f"Querying slack for page {page} of ALL files between {params['ts_from']} - {params['ts_to']}")
            response = cls.get_request(cls.URL_FILE_LIST, params, cls.SCHEMA_FILE_LIST)

            num_files += response['paging']['count']
            tot_files = response['paging']['total']
            print(f"Retrieved data about {num_files}/{tot_files} files")

            # Add files to list, filtering on ims
            for file in response['files']:
                if dm in file['ims']:
                    file_list.append(file)

            # Decide whether to continue or not
            if num_files == 0 or response['paging']['page'] == response['paging']['pages']:
                break
            page += 1

        return file_list

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
        error_msg = f"Exception with request for URL: {url}"
        response = cls.request_base(url, params)
        if not isinstance(response, requests.Response):
            return response

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

    # Base for request.get and handling basic errors
    @classmethod
    def request_base(cls, url: str, params: dict, headers=None):
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

        return response

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
    def format_time(cls, datetime_obj: datetime):
        return datetime.datetime.strftime(datetime_obj, Switches.date_mode.value)
