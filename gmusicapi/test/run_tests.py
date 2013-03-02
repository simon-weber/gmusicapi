import logging
import sys

from proboscis import TestProgram

# these need to be imported for proboscis test discovery
from gmusicapi.test import local_tests, server_tests  # flake8: noqa
from gmusicapi.test.utils import NoticeLogging

def main():
    # warnings typically signal a change in protocol,
    # so fail the build if anything >= warning are sent,

    root_logger = logging.getLogger('gmusicapi')

    noticer = NoticeLogging()
    noticer.setLevel(logging.WARNING)
    root_logger.addHandler(noticer)

    # proboscis does not have an exit=False equivalent,
    # so SystemExit must be caught instead (we need
    # to check the log noticer)
    try:
        TestProgram().run_and_exit()
    except SystemExit as e:
        print
        if noticer.seen_message:
            print '(failing build due to log warnings)'
            sys.exit(1)

        if e.code is not None:
            sys.exit(e.code)

if __name__ == '__main__':
    main()
