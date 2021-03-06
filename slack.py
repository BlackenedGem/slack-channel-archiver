import datetime
import sys
import re

from switches import Switches
from status import Status

class Slack:
    # region CONSTANTS
    SLACK_HTML_ENCODING = {'&amp;': '&',
                           '&lt;': '<',
                           '&gt;': '>'}

    SUBTYPES_CUSTOM = ('me_message',
                       'thread_broadcast')

    SUBTYPES_NO_PREFIX = ('channel_archive',
                          'channel_join',
                          'channel_leave',
                          'channel_name',
                          'channel_purpose',
                          'channel_topic',
                          'channel_unarchive',
                          'pinned_item')

    ATTACHMENT_FIELDS = ('fields',
                         'subtext',
                         'text',
                         'title',
                         'title_link')

    INDENTATION = "        "  # 8 spaces
    INDENTATION_SHORT = "     "  # 5 spaces
    CHAR_PIPE = '|'
    # endregion

    def __init__(self, user_map: dict, conv_map: dict, process_threads: bool = False):
        self.user_map = user_map
        self.conv_map = conv_map
        self.__last_date = None
        self.__last_user = None
        self.thread_msgs = None
        self.process_channel_threads = process_threads

    def format_messages(self, messages, process_children=False):
        self.thread_msgs = self.get_thread_msgs(messages)

        # Reset last date/user
        self.__last_date = None
        self.__last_user = None

        # Build and return data
        formatted_data = []
        for msg in messages:
            # Do not process thread child messages, they will either be processed by reply_broadcast or the parent message
            if (not ('thread_ts' in msg and msg['thread_ts'] != msg['ts']))\
                or ('subtype' in msg and msg['subtype'] == 'thread_broadcast')\
                    or process_children:
                formatted_data.append(self.format_message(msg))

        formatted_data = "".join(formatted_data)

        return formatted_data.strip()

    def format_message(self, msg):
        prefix_str = "\n"

        # Get timestamp
        timestamp = msg['ts']
        dt = datetime.datetime.fromtimestamp(float(timestamp))
        date = dt.date()

        # Denote change in date if new date
        if self.__last_date is None or self.__last_date < date:
            prefix_str += "\n -- " + date.strftime(Switches.date_mode.value) + " -- \n\n"
            self.__last_date = date

        # Timestamp
        timestamp_str = self.format_timestamp(timestamp)
        body_str = ""

        # Get subtype and username
        subtype = None
        if 'subtype' in msg:
            subtype = msg['subtype']
        username = self.get_username(msg, self.user_map)

        # user is new (and date has not changed), add a newline to the prefix
        if self.__last_user != username and prefix_str == "\n":
            prefix_str = "\n" + prefix_str

        # Do stuff based on the subtype
        if subtype in Slack.SUBTYPES_NO_PREFIX:
            body_str += self.format_msg_text(msg, include_ampersand=False)
        elif subtype in Slack.SUBTYPES_CUSTOM:
            body_str = self.format_msg_custom_type(body_str, msg, subtype, username)
        else:
            # Standard message
            if self.__last_user != username:
                timestamp_str = Slack.INDENTATION + username + ":\n" + timestamp_str

            body_str += self.format_msg_text(msg)

        # If message contains files then add that
        file_str = self.get_file_str(msg, username)
        if file_str != "":
            if body_str != "":
                body_str += "\n" + Slack.INDENTATION
            body_str += file_str

        # If message contains replies, then add them as a thread
        if 'thread_ts' in msg and 'replies' in msg and len(msg['replies']) > 0:
            body_str += "\n\n" + Slack.INDENTATION_SHORT + "T: "
            body_str += self.add_thread_msgs(msg)

        # Update last_user
        self.__last_user = username

        return prefix_str + timestamp_str + body_str

    def format_msg_text(self, msg, include_ampersand=True):
        ret_str = ""

        # Plain text
        if 'text' in msg:
            ret_str += self.improve_message_text(msg['text'], include_ampersand)

        # Attachments
        ret_str += self.add_attachments(msg)

        return ret_str

    def format_msg_custom_type(self, body_str, msg, subtype, username):
        ret = body_str

        if subtype == 'me_message':
            if self.__last_user != username:
                ret += username + ": "
            ret += "_" + self.format_msg_text(msg) + "_"

        elif subtype == 'thread_broadcast':
            if self.process_channel_threads:
                # Standard message
                if self.__last_user != username:
                    ret = Slack.INDENTATION + username + ":\n" + ret

                ret += self.format_msg_text(msg)
            else:
                ret += username + " replied to a thread:\n" + Slack.INDENTATION + self.format_msg_text(msg)

        return ret

    def get_file_str(self, msg, msg_user):
        files = self.get_file_objs_from_msg(msg)
        if files is None:
            return ""

        # Extract info
        ret_str = []

        for file in files:
            file_user = self.get_username(file, self.user_map)
            upload = msg.get('upload', False)

            # Default to share
            if upload:
                file_str = f"{msg_user} uploaded a file: "
            else:
                if file_user == msg_user:
                    file_str = f"{msg_user} shared their file: "
                else:
                    file_str = f"{msg_user} shared a file by {file_user}: "

            if file['mode'] == "tombstone":
                file_str += "File deleted"
            elif file.get('title', "") == "":
                file_str += "No title given"
            else:
                file_str += "'" + file['title'] + "'"
            ret_str.append(file_str)

        return ("\n" + Slack.INDENTATION).join(ret_str)

    @staticmethod
    def get_file_objs_from_msg(msg):
        if 'files' not in msg:
            return None

        # Get file object
        files = msg['files']
        if len(files) != 1:
            print(f"Encountered a file array with {len(files)} files, this support is experimental")

        return files

    @staticmethod
    def get_file_link(msg):
        ret_str = "<"

        if 'file' in msg:
            file_json = msg['file']

            if 'permalink' in file_json:
                ret_str += file_json['permalink']

            ret_str += "|"

            if 'name' in file_json:
                ret_str += file_json['name']

        ret_str += ">"
        return ret_str

    def format_attachment(self, a, user):
        body_str = ""
        ret_str = ""

        # Only process attachments that contain at least 1 supported field
        if not any(field in Slack.ATTACHMENT_FIELDS for field in a):
            return body_str

        # Pretext should appear as standard text
        if 'pretext' in a:
            ret_str = self.improve_message_text(a['pretext'])

        # Add title (include link if exists)
        title_str = ""
        if 'title_link' in a:
            title_str = "<" + a['title_link'] + ">"

            if 'title' in a:
                title_str = title_str[:-1] + "|" + a['title'] + ">"
        elif 'title' in a:
            title_str = a['title']

        if title_str != "":
            body_str += self.improve_message_text(title_str)

            # Text isn't required, but it's highly likely
            if 'text' in a:
                body_str += "\n" + Slack.INDENTATION

        # Add text
        if 'text' in a:
            body_str += self.improve_message_text(a['text']) + "\n"

        # Add fields
        if 'fields' in a:
            # Remove the newline from the text in the attachment
            if body_str.endswith("\n"):
                body_str = body_str[:-1]

            # Combine fields
            fields = a['fields']
            field_str = ""
            for f in fields:
                if 'title' in f:
                    field_str += f['title'] + "\n"

                field_str += f['value'] + "\n\n"
            field_str = field_str.strip()

            # Improve text and add to return string
            field_str = self.improve_message_text(field_str)
            if body_str == "":
                body_str = field_str
            else:
                body_str += "\n\n" + Slack.INDENTATION + field_str

        file_msg = self.get_file_str(a, user)
        if file_msg != "":
            body_str += "\n" + Slack.INDENTATION + file_msg

        # Denote the attachment by adding A: inline with the timestamp
        ret_str += "\n" + Slack.INDENTATION_SHORT + "A: " + body_str

        return ret_str

    def add_attachments(self, msg):
        ret_str = ""

        if 'attachments' in msg:
            attachments = msg['attachments']

            for a in attachments:
                ret_str += self.format_attachment(a, self.get_username(msg, self.user_map))

        # Last attachment should not add a newline, this is the easiest way to get rid of it
        if ret_str.endswith("\n"):
            ret_str = ret_str[:-1]

        return ret_str

    def improve_message_text(self, msg: str, include_ampersand=True):
        msg = self.improve_user_mentions(msg, include_ampersand)
        self.improve_channel_mentions(msg)

        # Replace HTML encoded characters
        for i in Slack.SLACK_HTML_ENCODING:
            msg = msg.replace(i, Slack.SLACK_HTML_ENCODING[i])

        # Improve indentation (use spaces instead of tabs, I expect most people to view the data using a monospaced font)
        # At least this works for notepad and notepad++
        msg = msg.replace("\n", "\n" + Slack.INDENTATION)

        return msg

    def improve_user_mentions(self, msg: str, include_ampersand=True):
        # Use regex to find user mentions
        # Format 1, no pipe
        mentions = re.finditer('<@U([^|>]+)>', msg)
        for match in mentions:
            new_text = ""
            if include_ampersand:
                new_text += "@"

            user_id = match.group()[2:-1]

            if user_id == 'SLACKBOT':
                new_text += "Slackbot"
            elif user_id in self.user_map:
                new_text += self.user_map[user_id]
            else:
                new_text += user_id

            msg = msg.replace(match.group(), new_text)

        # Format 2, pipe
        mentions = re.finditer('<@U([^|]+)[^>]+>', msg)
        for match in mentions:
            new_text = match.group()[2:-1]
            new_text = new_text.split("|")
            new_text = new_text[1]
            new_text = "@" + new_text

            msg = msg.replace(match.group(), new_text)

        return msg

    def improve_channel_mentions(self, msg: str):
        # Use regex to find channel mentions
        # Format 1, no pipe
        mentions = re.finditer('<#([GC])([^|>]+)>', msg)
        for match in mentions:
            new_text = "#"
            conv_id = match.group()[2:-1]

            if conv_id in self.conv_map:
                new_text += self.conv_map[conv_id]
            else:
                new_text += conv_id

            msg = msg.replace(match.group(), new_text)

        # Format 2, pipe
        mentions = re.finditer('<#([GC])([^|]+)[^>]+>', msg)
        for match in mentions:
            new_text = match.group()[2:-1]
            new_text = new_text.split("|")
            new_text = new_text[1]
            new_text = "#" + new_text

            msg = msg.replace(match.group(), new_text)

        return msg

    @staticmethod
    def get_username(msg, user_map: dict):
        # Prefer user over username field, since this is an ID and username can be present but blank
        if 'user' in msg:
            username = msg['user']

            if username == "USLACKBOT":
                return 'Slackbot'
            else:
                return user_map[username]

        if 'username' in msg:
            return msg['username']

        return "Unknown"

    def add_thread_msgs(self, parent):
        # Combine messages into array
        thread = []
        for child in parent['replies']:
            child_ts = child['ts']

            if child_ts not in self.thread_msgs:
                Status.thread_msgs_not_found += 1
                continue
            child_msg = self.thread_msgs[child_ts]
            thread.append(child_msg)

        # Create a new export object to format the messages for us
        s = Slack(self.user_map, self.conv_map)
        s.process_channel_threads = True
        thread_str = s.format_messages(thread, process_children=True)

        # Strip thread_str of leading/trailing whitespace, and add extra indentation
        thread_str = thread_str.strip()
        thread_str = thread_str.replace("\n", "\n" + Slack.INDENTATION_SHORT + Slack.CHAR_PIPE + "  ")
        thread_str += "\n"

        return thread_str

    @staticmethod
    def format_timestamp(ts, full=False, min_divide_char=':', no_slashes=False):
        time_format = Switches.date_mode.value
        if no_slashes:
            time_format = time_format.replace("\\", "-")
            time_format = time_format.replace("/", "-")

        dt = datetime.datetime.fromtimestamp(float(ts))
        date = dt.date()
        time = dt.time()

        time_str = "["
        if full:
            time_str += date.strftime(time_format) + " - "

        time_str += str(time.hour).rjust(2, '0') + min_divide_char + str(time.minute).rjust(2, '0') + "] "
        return time_str

    @staticmethod
    def get_thread_msgs(data):
        msgs = {}

        for msg in data:
            if 'thread_ts' not in msg:
                continue

            # Do not save the parent
            if msg['thread_ts'] != msg['ts']:
                msgs[msg['ts']] = msg

        return msgs
