#!/usr/bin/env python
from __future__ import unicode_literals
import argparse
import logging
import pprint

LOGGER = logging.getLogger(__name__)


def execute(args):
    with open(args.filename) as f:
        lines = f.readlines()
    lines = [l.strip('\n').encode('utf-8') for l in lines]
    pprint.pprint(lines)


def main():
    parser = argparse.ArgumentParser()

    class SetLoggingLevel(argparse.Action):

        def __call__(self, parser, namespace, values, option_string=None):
            setattr(namespace, self.dest, getattr(logging, values))
            LOGGER.setLevel(getattr(namespace, self.dest))

    parser.add_argument(
        '-l', '--logging-level',
        default=logging.WARNING,
        action=SetLoggingLevel,
        help='Set the logging level',
        choices=[
            'DEBUG',
            'INFO',
            'WARN',
            'WARNING',
            'ERROR',
            'CRITICAL',
            'FATAL',
            ],
        )
    parser.add_argument('filename')
    args = parser.parse_args()
    execute(args)


if __name__ == '__main__':
    main()
