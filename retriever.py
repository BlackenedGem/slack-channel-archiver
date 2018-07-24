import argparse
import os.path
import json

from switches import Switches
from api import Api
from status import Warnings

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
    parser.add_argument('-o', '--output', nargs='?', const='output', default='',
                        help="Output directory to use")
    parser.add_argument('-j', '--json', action='store_const', const='dm.json',
                        help="Output the message history in raw json form")

    # Process basic args
    parsed_args = parser.parse_args()
    Switches.set_switches(parsed_args, parser)
    Api.token = parsed_args.token

    return parsed_args

def get_user_map(message_list):
    user_id_map = {}
    user_ids = set(x['user'] for x in message_list)
    for user_id in user_ids:
        user_id_map[user_id] = Api.get_username(user_id)
    return user_id_map

def write_to_file(file: str, data):
    # Get full path and create directory if it doesn't exist
    loc = os.path.join(args.output, file)
    print(f"Saving data to {loc}")
    os.makedirs(os.path.dirname(loc), exist_ok=True)

    # Write to file and return true/false
    try:
        with open(loc, "w") as f:
            f.write(data)
    except (IOError, FileNotFoundError) as e:
        print(e)
        return False

    return True

# PROGRAM START
args = arg_setup()
status = Warnings()

# Retrieve messages
messages = Api.get_dm_history(args.dm, Switches.date_start, Switches.date_end)
messages.reverse()

# Write to JSON
if args.json is not None:
    print("Exporting raw json")
    status.export_json = not write_to_file(args.json, json.dumps(messages, indent=4))

# Mapping of user ids to display names
user_map = get_user_map(messages)
