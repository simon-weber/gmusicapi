from proboscis import TestProgram

from gmusicapi.test import local_tests  # flake8: noqa

def main():
    TestProgram().run_and_exit()

if __name__ == '__main__':
    main()
