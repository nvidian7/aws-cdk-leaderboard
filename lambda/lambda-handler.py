import os
import lib.redis as redis
import json
import traceback
import time
from lib.lambdarest import create_lambda_handler
import sys

lua_script_get_my_rank = """
local rank = redis.call('ZREVRANK', KEYS[1], ARGV[1])
if not rank then
  -- Key or member not found
  return nil
end

local score = redis.call('ZSCORE', KEYS[1], ARGV[1])
return {rank+1, ARGV[1], tostring(score)}
"""

lua_script_get_around = """
local rank = redis.call('ZREVRANK', KEYS[1], ARGV[1])
if not rank then
  -- Key or member not found
  return nil
end

local r1, r2 = rank-ARGV[2], rank+ARGV[2]
if r1 < 0 then
  r1 = 0
end

local member, score
local range = redis.call('ZREVRANGE', KEYS[1], r1, r2, 'WITHSCORES')

local data = {}
for i=r1,(r1+#range/2)-1 do
  data[#data+1] = i+1
  data[#data+1] = range[((i-r1)*2)+1]
  data[#data+1] = tostring(range[((i-r1)*2)+2])
end

return data
"""

redis_client = redis.StrictRedis(
    host=os.environ.get('REDIS_HOST'),
    port=os.environ.get('REDIS_PORT'),
    charset="utf-8",
    decode_responses=True)

LeaderBoardId = "lambda-test"

lambda_handler = create_lambda_handler(error_handler=None)


class UserNotFoundException(Exception):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg


@lambda_handler.handle("get", path="/<string:leader_board_id>/<string:user_id>")
def get_user_score(event, leader_board_id, user_id):
    data = redis_client.eval(
        lua_script_get_my_rank, 1, leader_board_id, user_id)

    if data is None:
        raise UserNotFoundException("user not found")

    return {data[1]: {"rank": data[0], "score": data[2]}}


@lambda_handler.handle("get", path="/<string:leader_board_id>/top")
def get_top_rank_scores(event, leader_board_id):
    query_param_dict = event.get("json", {}).get("query", {})

    # if exlicit limit query parameter not exists then apply fetch default count
    limit = query_param_dict.get("limit", 100)
    offset = query_param_dict.get("offset", 0)

    if limit <= 0:
        raise ValueError("limit parameter must be positive value.")

    # to pervent too huge fetch limit fetch count
    limit = min(limit, 1000)

    rank_data = redis_client.zrevrange(
        leader_board_id, offset, offset+limit-1, withscores=True)
    # rank_data = redis_client.zrevrangebyscore(
    #     leader_board_id, "+inf", "-inf", withscores=True, start=0, num=limit)

    response = []

    for idx, data in enumerate(rank_data, start=offset+1):
        response.append({data[0]: {"rank": idx, "score": data[1]}})

    return response


@lambda_handler.handle("get", path="/<string:leader_board_id>/<string:user_id>/around")
def get_around_rank_scores(event, leader_board_id, user_id):
    query_param_dict = event.get("json", {}).get("query", {})

    # if exlicit limit query parameter not exists then apply fetch default count
    limit = query_param_dict.get("limit", 1)

    if limit <= 0:
        raise ValueError("limit parameter must be positive value.")

    # to pervent too huge fetch limit fetch count
    limit = min(limit, 10)

    # rank_data = redis_client.zrevrangebyscore(
    #     leader_board_id, "+inf", "-inf", withscores=True, start=0, num=limit)
    response = []

    rank_data = redis_client.eval(
        lua_script_get_around, 1, leader_board_id, user_id, limit)

    for data in [rank_data[i:(i+3)] for i in range(0, len(rank_data), 3)]:
        response.append({data[1]: {"rank": data[0], "score": data[2]}})

    return response


@lambda_handler.handle("put", path="/<string:leader_board_id>/<string:user_id>/<int:score>")
def put_score(event, leader_board_id, user_id, score):
    #timestamp = 5000000000 - int(time.time())
    #str(score) + "." + str(timestamp)
    redis_client.zadd(leader_board_id, ch=True, mapping={
                      user_id: score})
    return


@lambda_handler.handle("post", path="/<string:leader_board_id>/<string:user_id>/<string:delta>")
def incr_score(event, leader_board_id, user_id, delta):
    redis_client.zincrby(leader_board_id, int(delta), user_id)
    return


@lambda_handler.handle("get")
def default_handle(event):
    return {"this": "will be json dumped"}


def handler(event, context):
    try:
        return lambda_handler(event=event)
    except ValueError as verror:
        return {
            "statusCode": "400",
            "body": json.dumps({
                "message": str(verror)
            })
        }
    except UserNotFoundException as kerror:
        return {
            "statusCode": "404",
            "body": json.dumps({
                "message": str(kerror)
            })
        }
    except Exception as ex:
        traceback.print_exc()
        return {
            "statusCode": "500",
            "body": json.dumps({
                "message": str(ex)
            })
        }
    # rank_data = redis_client.zrevrangebyscore(
    #     LeaderBoardId, "+inf", "-inf", withscores=True, start=0, num=50)

    # return {
    #     # 'path': event['path'],
    #     # 'method': event['httpMethod'],
    #     'statusCode': '200',
    #     'headers': {},
    #     'body': json.dumps(event),
    #     'isBase64Encoded': False
    # }
