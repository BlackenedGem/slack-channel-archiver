from enum import Enum
import argparse
import datetime

class Switches:
    # region Switch definitions
    class dateModes(Enum):
        ISO8601 = '%Y-%m-%d'
        UK = '%d/%m/%Y'
    dateMode = dateModes.ISO8601
    dateStart = None
    dateEnd = None
    # endregion

    # Set using arguments
    @classmethod
    def set_switches(cls, args: argparse.Namespace, parser: argparse.ArgumentParser):
        if 'date_format' in args:
            cls.dateMode = cls.convert_enum(cls.dateModes, args.date_format, "date format", parser)
        if 'date_start' in args:
            cls.dateStart = cls.convert_date(args.date_start, parser)
        if 'date_end' in args:
            cls.dateEnd = cls.convert_date(args.date_end, parser)

    # Handle date parsing
    @classmethod
    def convert_date(cls, date_str: str, arg_parser: argparse.ArgumentParser):
        try:
            return datetime.datetime.strptime(date_str, cls.dateMode.value)
        except ValueError as e:
            arg_parser.error(e)


    # Handle parsing switches properly
    @classmethod
    def convert_enum(cls, enum, string: str, switch_str: str, arg_parser: argparse.ArgumentParser):
        try:
            return enum[string.upper()]
        except KeyError:
            # noinspection PyProtectedMember
            arg_parser.error(
                "Could not interpret " + switch_str + ". Available options are: " + cls.list_enum(enum))

    @classmethod
    def list_enum(cls, enum):
        # noinspection PyProtectedMember
        return ', '.join(enum._member_names_)
