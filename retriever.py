import argparse
import requests

from switches import Switches

# Constants
API_HISTORY_DM = "https://slack.com/api/im.history"

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

# Get message history
params = {
    'token': args.token,
    'channel': args.channel
}
response = requests.get(API_HISTORY_DM, params)
print(response.content)
