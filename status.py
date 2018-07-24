# Class to store list of warnings/errors encountered during execution

class Warnings:
    def __init__(self):
        self.export_json = False
        self.export_text = False
        self.file_failures = 0

    def print_warnings(self, tot_files: int):
        if self.export_json:
            print("JSON export failed")
        if self.export_text:
            print("Text export failed")
        if self.file_failures > 0:
            print(f"Could not download {self.file_failures} files ({tot_files} total)")
