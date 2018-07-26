import re
import os.path
import urllib.request

from slack import Slack

class Files:
    @classmethod
    def download_file(cls, file, user, file_dir):
        download_url = file['url_private_download']

        file_size = cls.bytes_to_str(file['size'])

        file_name = file['name']
        file_name = re.sub('[\\\/:*?"<>|]', '', file_name)

        save_name = Slack.format_timestamp(file['timestamp'], full=True, min_divide_char=';')
        save_name += f"- {user} - {file_name}"

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
