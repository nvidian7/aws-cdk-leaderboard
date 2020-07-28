import time
import datetime as pydatetime


# get datetime
def get_now():
    return pydatetime.datetime.now()


# 10 digit timestamp
def get_now_timestamp():
    return int(get_now().timestamp())


def get_reverse_timestamp():
    return int(5000000000-get_now_timestamp())
