import argparse
import os.path
import json
import sys

from api import Api
from files import Files
from slack import Slack
from status import Status
from switches import Switches

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
                        help="Latest messages to archive (exclusive)")

    # Export args
    parser.add_argument('-o', '--output', nargs='?', const='output', default='',
                        help="Output directory to use for exports (excluding files)")
    parser.add_argument('-j', '--json', nargs='?', const='dm.json',
                        help="Output the message history in raw json form")
    parser.add_argument('-t', '--text', nargs='?', const='dm.txt',
                        help="Output the message history in human readable form")

    # File args
    parser.add_argument('-f', '--files', nargs='?', const='output_files',
                        help="Download files found in JSON to the directory")
    parser.add_argument('-fo', '--files-overwrite', action='store_true',
                        help="Overwrite files if they exist")

    # Process basic args
    parsed_args = parser.parse_args()
    Switches.set_switches(parsed_args, parser)
    Api.token = parsed_args.token

    return parsed_args

def get_user_map():
    print("Retrieving user mappings")
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
    Files.make_dirs(loc)

    # Write to file and return true/false
    try:
        with open(loc, "w", encoding='utf-8') as f:
            f.write(data)
    except (IOError, FileNotFoundError) as e:
        print(e)
        return False

    return True

def download_files():
    print("Analysing JSON for uploaded files (as files.list does not support DMs)")
    files = Files.get_files(messages)
    print(f"Found {len(files)} file(s) from {len(messages)} messages")

    if len(files) == 0:
        return

    # Download files
    print("")
    for file in files:
        success = Files.download_file(file, args.files, user_map, overwrite=args.files_overwrite)

        if success:
            Status.tot_files += 1
        else:
            Status.file_failures += 1

    # Status messages
    print("File download complete")
    if Status.files_already_exist == 0:
        return
    if args.files_overwrite:
        print(f"{Status.files_already_exist} files were overwritten")
    else:
        print(f"{Status.files_already_exist} files were not downloaded as files with the same name already existed")

# PROGRAM START
args = arg_setup()

# Retrieve messages
messages = Api.get_dm_history(args.dm, Switches.date_start, Switches.date_end)
messages.reverse()

# Get user map
print("")
user_map = get_user_map()
slack = Slack(user_map)

# Write to JSON
if args.json is not None:
    print("Exporting raw json")
    Status.export_json = not write_to_file(args.json, json.dumps(messages, indent=4))

# Write to txt
if args.text is not None:
    print("Formatting text")
    formatted_text = slack.format_messages(messages)
    print("Exporting text")
    Status.export_text = not write_to_file(args.text, formatted_text)

if args.files is not None:
    download_files()

Status.print_warnings()
