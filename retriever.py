import argparse

from switches import Switches
from api import Api

# Setup argparse
parser = argparse.ArgumentParser()
parser.add_argument('token',
                    help="Slack authorisation token")
parser.add_argument('dm',
                    help="ID of the direct message chat")
parser.add_argument('-df', '--date-format',
                    help="Date format to use. Support options: " + Switches.list_enum(Switches.dateModes))
parser.add_argument('-ds', '--date-start',
                    help="Earliest messages to archive (inclusive)")
parser.add_argument('-de', '--date-end',
                    help="Latest messages to archive (inclusive)")

# Process basic args
args = parser.parse_args()
Switches.set_switches(args, parser)
Api.token = args.token

# Retrieve users

Api.get_request(Api.URL_USERS, {})
