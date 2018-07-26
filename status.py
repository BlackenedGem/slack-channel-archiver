# Class to store list of warnings/errors encountered during execution

class Status:
    # Stats
    tot_files = 0

    # Errors
    export_json = False
    export_text = False
    file_failures = 0

    # Warnings
    thread_msgs_not_found = 0

    @classmethod
    def num_errors(cls):

        num = cls.file_failures
        if cls.export_json:
            num += 1
        if cls.export_text:
            num += 1

        return num

    @classmethod
    def num_warnings(cls):
        return cls.thread_msgs_not_found

    @classmethod
    def print_warnings(cls):
        errors = cls.num_errors()
        warns = cls.num_warnings()

        if errors == 0 and warns == 0:
            print("\nProgram finished successfully")
            return

        print(f"\nProgram finished with {errors} errors and {warns} warnings")
        if errors > 0:
            print("ERRORS:")

        if cls.export_json:
            print("JSON export failed")
        if cls.export_text:
            print("Text export failed")
        if cls.file_failures > 0:
            print(f"Could not download {cls.file_failures} files ({cls.tot_files} total)")

        if warns == 0:
            return

        print("WARNINGS:")
        if cls.thread_msgs_not_found > 0:
            print(f"Could not find {cls.thread_msgs_not_found} thread messages")
