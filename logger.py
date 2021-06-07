# a module to help out with logging

import os
from datetime import datetime

def log(text):
    print('{} | {} | {}'.format(datetime.now().strftime('%Y/%m/%d-%H:%M:%S'), os.getpid(), text))