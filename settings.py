import configparser
import argparse
import os


def default_config():
    return """
[compiler]
name = gcc-6
options = -O3

[tests]
timeout_prog = gtimeout
#temporary_folder should contains file in a period until system reboot. Programs stast several times after compilation
#thats why we cannot use /tmp folder, which do not guaratee that file will not suddenly disappear.
temporary_folder = /var/tmp
#Count of test runs for one test file and one solution
count = 10
timeout = 1
force_run_after_timeout = True

[view]
editor_cmd = subl
alpha_select = 0.0
"""

def check_settings():
    if not os.path.isfile('./config.ini'):
        with open('./config.ini', 'w') as ini:
            print("Config doesn't exists. Creating default config file")
            ini.write(default_config())


print("Loading setting")
check_settings()
config = configparser.ConfigParser()
config.read('./config.ini')

