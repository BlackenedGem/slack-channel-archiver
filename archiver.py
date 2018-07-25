import argparse
import os.path
import sys

from switches import Switches
from api import Api
from status import Status
from slack import Slack

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
    parser.add_argument('-t', '--text', nargs='?', const='dm.txt', default='dm.text',
                        help="Output the message history in human readable form")

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

def get_user_map_new():
    user_id_map = {}

    # Make requests until response_metadata has no cursor
    cursor = None
    while True:
        profiles, cursor = Api.get_profiles(cursor)

        for profile in profiles:
            user_id_map[profile['id']] = profile['profile']['display_name']

        if cursor is None:
            break

    return user_id_map


def write_to_file(file: str, data):
    # Get full path and create directory if it doesn't exist
    loc = os.path.join(args.output, file)
    print(f"Saving data to {loc}")
    os.makedirs(os.path.dirname(loc), exist_ok=True)

    # Write to file and return true/false
    try:
        with open(loc, "w", encoding='utf-8') as f:
            f.write(data)
    except (IOError, FileNotFoundError) as e:
        print(e)
        return False

    return True

# PROGRAM START
args = arg_setup()

# Retrieve messages
messages = Api.get_dm_history(args.dm, Switches.date_start, Switches.date_end)
messages.reverse()

print(get_user_map_new())
sys.exit(1)

# Format text
user_map = get_user_map(messages)
slack = Slack(user_map)
formatted_text = slack.format_messages(messages)

print("")

# Write to JSON
if args.json is not None:
    print("Exporting raw json")
    Status.export_json = not write_to_file(args.json, json.dumps(messages, indent=4))

if args.text is not None:
    print("Exporting text")
    Status.export_text = not write_to_file(args.text, formatted_text)
