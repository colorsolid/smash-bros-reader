from   datetime import datetime
import os
from   sys import __excepthook__
from   time import time
from   traceback import format_exception


BASE_DIR = os.path.realpath(os.path.dirname(__file__))

def log_exception(type, value, tb):
    error = format_exception(type, value, tb)
    filepath = os.path.join(BASE_DIR, 'error.log')
    old_text = '\n'
    if os.path.isfile(filepath):
        with open(filepath, 'r') as logfile:
            old_text += logfile.read()
    timestamp = datetime.fromtimestamp(time()).strftime('%Y-%m-%d %H:%M:%S')
    line = f'[{timestamp}]\n{("".join(error))}'
    new_text = line + old_text
    with open(filepath, 'w+') as logfile:
        logfile.write(new_text)

    __excepthook__(type, value, tb)
