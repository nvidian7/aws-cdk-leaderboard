import time
import datetime as pydatetime

# 06/11/2128 @ 8:53am (UTC)
MAX_TIMESTAMP = 5000000000


# get datetime
def get_now():
    return pydatetime.datetime.now()


# 10 digit timestamp
def get_now_timestamp():
    return get_now().timestamp()


# redis의 sortedset value 사전순 정렬을 내림차순으로 유지하기
# 위해서는 timestamp 크기 비교 결과를 반대로 뒤집는 처리가 필요하고,
# 이를 위해서는 충분히 큰 timestamp 값에서 현재 timestamp를 빼서 그 차이를 이용
def get_reverse_timestamp():
    return int(MAX_TIMESTAMP-get_now_timestamp())
