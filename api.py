import requests
import sys
import json
from jsonschema import validate, ValidationError


class Api:
    # region Constants
    URL_HISTORY_DM = "https://slack.com/api/im.history"
    URL_USER_INFO = "https://slack.com/api/users.info"
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

    token = None

    @classmethod
    def get_username(cls, user_id: str):
        response = cls.get_request(cls.URL_USER_INFO, {'user': user_id})
        cls.validate_response(response, cls.SCHEMA_USER_INFO)
        return response['user']['profile']['display_name']

    # Validate JSON according to schema provided
    @classmethod
    def validate_response(cls, response: dict, schema: dict):
        try:
            validate(response, schema)
        except ValidationError as e:
            print("JSON retrieved is invalid")
            print(e)
            sys.exit(-1)

    # GET requests all have the same processing logic
    # Also remove requirement to send token for everything
    @classmethod
    def get_request(cls, url: str, params: dict):
        # variables
        error_msg = f"Exception with request"
        params['token'] = cls.token

        # Go through obvious failure points
        # noinspection PyBroadException
        try:
            print(f"GET: {url}")
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

        return resp_json
