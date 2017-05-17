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
#Количество вызовов программы для одного теста
count = 10
timeout = 2
force_run_after_timeout = True

[view]
editor_cmd = subl
alpha_select = 0.02
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

