"""
Mock version of appdirs for use in cases without the real version
"""

try:
    from appdirs import AppDirs
    my_appdirs = AppDirs('gmusicapi', 'Simon Weber')
except ImportError:
    print('warning: could not import appdirs; will use current directory')

    class FakeAppDirs:
        to_spoof = {base + '_dir' for base in
                    ('user_data', 'site_data', 'user_config', 'site_config', 'user_cache',
                     'user_log')}

        def __getattr__(self, name):
            if name in self.to_spoof:
                return '.'  # current dir
            else:
                raise AttributeError

    my_appdirs = FakeAppDirs()
