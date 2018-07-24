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
                    help="Date format to use. Supported options: " + Switches.list_enum(Switches.DateModes))
parser.add_argument('-ds', '--date-start',
                    help="Earliest messages to archive (inclusive)")
parser.add_argument('-de', '--date-end',
                    help="Latest messages to archive (inclusive)")

# Process basic args
args = parser.parse_args()
Switches.set_switches(args, parser)
Api.token = args.token

# Retrieve messages
messages = Api.get_dm_history(args.dm, Switches.date_start, Switches.date_end)

# Mapping of user ids to display names
user_map = {}
user_ids = set(x['user'] for x in messages)
for user_id in user_ids:
    user_map[user_id] = Api.get_username(user_id)

