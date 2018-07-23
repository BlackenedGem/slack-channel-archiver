import argparse
import requests

from switches import Switches

# Constants
API_HISTORY_DM = "https://slack.com/api/im.history"

# Get args
parser = argparse.ArgumentParser()
parser.add_argument('token')
parser.add_argument('channel')
args = parser.parse_args()
Switches.set_switches(args, parser)

# Get message history
params = {
    'token': args.token,
    'channel': args.channel
}
response = requests.get(API_HISTORY_DM, params)
print(response.content)
