import argparse
import requests

from switches import Switches

# Get args
parser = argparse.ArgumentParser()
parser.add_argument('token')
parser.add_argument('channel')
args = parser.parse_args()


Switches.set_switches(args, parser)

# Get message history
print(Switches.dateMode)
# Get files
print(args)
