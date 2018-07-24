import argparse
import os.path
import json

from switches import Switches
from api import Api

def arg_setup():
    # Required args
    parser = argparse.ArgumentParser()
    parser.add_argument('token',
                        help="Slack authorisation token")
    parser.add_argument('dm',
                        help="ID of the direct message chat")

    # Date args
    parser.add_argument('-df', '--date-format',
                        help="Date format to use. Supported options: " + Switches.list_enum(Switches.DateModes))
    parser.add_argument('-ds', '--date-start',
                        help="Earliest messages to archive (inclusive)")
    parser.add_argument('-de', '--date-end',
                        help="Latest messages to archive (inclusive)")

    # Export args
    parser.add_argument('-o', '--output', nargs='?', const='', default='',
                        help="Output directory to use")
    parser.add_argument('-j', '--json', action='store_const', const='dm.json',
                        help="Output the message history in raw json form")

    # Process basic args
    parsed_args = parser.parse_args()
    Switches.set_switches(parsed_args, parser)
    Api.token = parsed_args.token

    return parsed_args

args = arg_setup()

# Retrieve messages and write to json if requested
messages = Api.get_dm_history(args.dm, Switches.date_start, Switches.date_end)
messages.reverse()

if args.json is not None:
    out_file = os.path.join(args.output + args.json)
    print("Writing raw JSON to: " + out_file)

    # noinspection PyBroadException
    try:
        open(out_file, 'w').write(json.dumps(messages, indent=4))
    except Exception as e:
        print(e)

# Mapping of user ids to display names
user_map = {}
user_ids = set(x['user'] for x in messages)
for user_id in user_ids:
    user_map[user_id] = Api.get_username(user_id)

print(json.dumps(messages, indent=4))
