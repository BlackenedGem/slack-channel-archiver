import re
import os.path
import urllib.request

from slack import Slack

class Files:
    @classmethod
    def get_files(cls, messages, user_map: dict):
        files = []

        for msg in messages:
            file = Slack.get_file_obj_from_msg(msg)

            if file is not None:
                files.append(file)

        return files

    @classmethod
    def download_file(cls, file, file_dir, user_map: dict):
        download_url = file['url_private_download']

        file_size = cls.bytes_to_str(file['size'])
        file_user = Slack.get_username(file, user_map)

        file_name = file['name']
        file_name = re.sub('[\\\/:*?"<>|]', '', file_name)

        save_name = Slack.format_timestamp(file['timestamp'], full=True, min_divide_char=';')
        save_name += f"- {file_user} - {file_name}"

        print("Downloading file from '" + download_url + "' (" + file_size + ")")

        return cls.download(download_url, file_dir + save_name)

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
    def download(source: str, save_loc: str):
        if not os.path.exists(save_loc):
            try:
                urllib.request.urlretrieve(source, save_loc)
            except Exception as e:
                print(e)
                return False
        else:
            print("File already exists in download location '" + save_loc + "'")

        return True
