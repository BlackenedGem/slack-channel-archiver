import re
import os.path
import requests

from slack import Slack
from status import Status

class Files:
    @classmethod
    def download_file(cls, token, file, file_dir, user_map: dict, overwrite=False, ):
        download_url = file['url_private_download']

        file_size = cls.bytes_to_str(file['size'])
        file_user = Slack.get_username(file, user_map)

        file_name = file['title']
        if not file_name.endswith(file['filetype']):
            file_name += "." + file['filetype']
        file_name = file_name.replace(':', ';')
        file_name = re.sub('[\\\/*?"<>|]', '', file_name)

        save_name = Slack.format_timestamp(file['timestamp'], full=True, min_divide_char=';', no_slashes=True)
        save_name += f"- {file_name}"
        save_loc = os.path.join(file_dir, file_user, save_name)
        Files.make_dirs(save_loc)

        print("Downloading file from '" + download_url + "' (" + file_size + ")")
        return cls.download(download_url, save_loc, overwrite, token)

    @staticmethod
    def bytes_to_str(size: int, precision=2):
        # https://stackoverflow.com/a/32009595
        suffixes = ['B', 'KB', 'MB', 'GB', 'TB']
        suffix_index = 0
        while size > 1024 and suffix_index < 4:
            suffix_index += 1  # increment the index of the suffix
            size = size / 1024.0  # apply the division
        return "%.*f%s" % (precision, size, suffixes[suffix_index])

    @staticmethod
    def download(source: str, save_loc: str, overwrite: bool, token: str):
        if os.path.exists(save_loc):
            Status.files_already_exist += 1

            if not overwrite:
                print("File already exists in download location '" + save_loc + "'")
                return True
            else:
                print("File already exists, overwriting")

        try:
            response = requests.get(source, headers={"Authorization": "Bearer " + token})
            if not isinstance(response, requests.Response):
                return False

            with open(save_loc, "wb") as f:
                f.write(response.content)
        except Exception as e:
            print("ERROR: " + str(e))
            return False

        return True

    @staticmethod
    def make_dirs(loc):
        directory = os.path.dirname(loc)
        if directory == "":
            return

        os.makedirs(directory, exist_ok=True)
