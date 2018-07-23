import requests
import sys
import json


class Api:
    # Constants
    URL_HISTORY_DM = "https://slack.com/api/im.history"
    URL_USERS = "https://slack.com/api/users.info"

    token = None

    @classmethod
    def get_username(cls, user_id: str):
        resonse = requests.get(cls.URL_USERS, {
            'token': cls.token,
            'user': user_id
        })

    # GET requests all have the same processing logic
    # Also remove requirement to send token for everything
    @classmethod
    def get_request(cls, url: str, params: dict):
        # Constant and vars
        ERROR_MSG = f"Exception with GET request for URL: {url}"
        params['token'] = cls.token

        # Go through obvious failure points
        # noinspection PyBroadException
        response = None
        try:
            response = requests.get(url, params)
        except requests.exceptions.RequestException as e:
            print(ERROR_MSG)
            print(e)
            sys.exit(-1)

        if response.status_code != 200:
            print(ERROR_MSG)
            print("Status code: " + response.status_code)
            sys.exit(-1)

        if response.text is None:
            print(ERROR_MSG)
            print("Response is null")
            sys.exit(-1)

        resp_json = json.loads(response.text)
        if 'ok' not in resp_json or 'error' not in resp_json:
            print(ERROR_MSG)
            print("Returned JSON was not in the correct format:")
            print(json.dumps(resp_json, indent=4))
            sys.exit(-1)

        if not resp_json['ok']:
            print(ERROR_MSG)
            print("Response gave 'false' signal for ok. Error provided: " + resp_json['error'])

        return resp_json
