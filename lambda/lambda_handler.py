import os
import redis
import json
import traceback
from lambdarest import create_lambda_handler
import sys
from timestamp import get_reverse_timestamp
from leaderboard_exceptions import UserNotFoundException, InvalidRequestException, AccessDeniedException
from leaderboard_scripts import lua_script_get_around, lua_script_get_my_rank, lua_script_put_score, lua_script_delete_score

admin_secret_token = os.environ.get('ADMIN_SECRET_TOKEN')

redis_client = redis.StrictRedis(
    host=os.environ.get('REDIS_HOST'),
    port=os.environ.get('REDIS_PORT'),
    charset="utf-8",
    decode_responses=True)

lambda_handler = create_lambda_handler(error_handler=None)


def leaderboard_str(service_id: str, leader_board_id: str):
    return f'{service_id}:leaderboard:{leader_board_id}'


def leaderboard_timestamp_str(service_id: str, leader_board_id: str):
    return f'{service_id}:leaderboard:{leader_board_id}:timestamp'


def user_properties_key_str(service_id: str, user_id: str):
    return f'{service_id}:user:{user_id}:properties'


@lambda_handler.handle("get", path="/<string:service_id>/leaderboards/<string:leader_board_id>")
def get_leaderboard_status(event, service_id, leader_board_id):
    cardinality = redis_client.hlen(leaderboard_timestamp_str(service_id, leader_board_id))
    return {"cardinality": cardinality}


@lambda_handler.handle("get", path="/<string:service_id>/leaderboards/<string:leader_board_id>/<string:user_id>")
def get_user_score(event, service_id, leader_board_id, user_id):
    data = redis_client.eval(lua_script_get_my_rank, 2,
                             leaderboard_str(service_id, leader_board_id),
                             leaderboard_timestamp_str(service_id, leader_board_id),
                             user_id)

    if data is None:
        raise UserNotFoundException("user not found")

    query_param_dict = event.get("json", {}).get("query", {})
    include_properties = query_param_dict.get("properties", False)

    response = {"userId": data[1], "rank": data[0], "score": data[2]}
    if include_properties:
        properties = redis_client.get(user_properties_key_str(service_id, user_id))
        if properties is not None:
            response["properties"] = json.loads(properties)

    return response


@lambda_handler.handle("delete", path="/<string:service_id>/leaderboards/<string:leader_board_id>/<string:user_id>")
def delete_user_score(event, service_id, leader_board_id, user_id):
    redis_client.eval(lua_script_delete_score, 2,
                      leaderboard_str(service_id, leader_board_id),
                      leaderboard_timestamp_str(service_id, leader_board_id),
                      user_id)
    return

# pick top rank of leader board


@lambda_handler.handle("get", path="/<string:service_id>/leaderboards/<string:leader_board_id>/top")
def get_top_rank_scores(event, service_id, leader_board_id):
    query_param_dict = event.get("json", {}).get("query", {})
    # if exlicit limit query parameter not exists then apply fetch default count
    limit = query_param_dict.get("limit", 100)
    offset = query_param_dict.get("offset", 0)

    if limit <= 0:
        raise ValueError("limit parameter must be positive value.")

    # limit fetch count to prevent too huge fetch
    limit = min(limit, 1000)

    rank_data = redis_client.zrevrange(leaderboard_str(service_id, leader_board_id), offset, offset+limit-1, withscores=True)
    # rank_data = redis_client.zrevrangebyscore(
    #     leader_board_id, "+inf", "-inf", withscores=True, start=0, num=limit)

    response = []

    for idx, data in enumerate(rank_data, start=offset+1):
        response.append({"userId": data[0].split(':')[1], "rank": idx, "score": data[1]})

    include_properties = query_param_dict.get("properties", False)
    if include_properties:
        properties = redis_client.mget(list(map(lambda x: user_properties_key_str(service_id, x['userId']), response)))
        for i, prop in enumerate(properties, start=0):
            if prop is not None:
                response[i]["properties"] = json.loads(prop)

    return response


@lambda_handler.handle("get", path="/<string:service_id>/leaderboards/<string:leader_board_id>/<string:user_id>/around")
def get_around_rank_scores(event, service_id, leader_board_id, user_id):
    query_param_dict = event.get("json", {}).get("query", {})

    # if exlicit limit query parameter not exists then apply fetch default count
    limit = query_param_dict.get("limit", 1)

    if limit <= 0:
        raise ValueError("limit parameter must be positive value.")

    # limit count for prevent huge fetch
    limit = min(limit, 10)

    # rank_data = redis_client.zrevrangebyscore(
    #     leader_board_id, "+inf", "-inf", withscores=True, start=0, num=limit)
    response = []

    rank_data = redis_client.eval(lua_script_get_around, 2,
                                  leaderboard_str(service_id, leader_board_id), leaderboard_timestamp_str(service_id, leader_board_id),
                                  user_id, limit)

    if rank_data is None:
        return []

    for data in [rank_data[i:(i+3)] for i in range(0, len(rank_data), 3)]:
        response.append({"userId": data[1].split(":")[1], "rank": data[0], "score": data[2]})

    include_properties = query_param_dict.get("properties", False)
    if include_properties:
        properties = redis_client.mget(list(map(lambda x: user_properties_key_str(service_id, x['userId']), response)))
        for i, prop in enumerate(properties, start=0):
            if prop is not None:
                response[i]["properties"] = json.loads(prop)

    return response


@lambda_handler.handle("put", path="/<string:service_id>/leaderboards/<string:leader_board_id>/<string:user_id>")
def put_score(event, service_id, leader_board_id, user_id):
    if event["body"] is None:
        raise InvalidRequestException("request parameter invalid")

    body = json.loads(event["body"])

    if "score" not in body:
        raise InvalidRequestException(
            "'score' parameter not exists in request body")

    if body["score"] == 0:
        return

    if body["score"] < 0:
        raise ValueError("score parameter must be positive value.")

    prev_score = redis_client.eval(lua_script_put_score, 2,
                                   leaderboard_str(service_id, leader_board_id),
                                   leaderboard_timestamp_str(service_id, leader_board_id),
                                   user_id, body["score"], get_reverse_timestamp())

    return {"prevScore": prev_score}

    # lboard_user_id = redis_client.hget(leaderboard_timestamp_str(
    #     service_id, leader_board_id), user_id)

    # # exist prev value
    # if lboard_user_id is not None:
    #     prev_score = redis_client.zscore(leaderboard_str(
    #         service_id, leader_board_id), lboard_user_id)
    #     if prev_score is not None and body["score"] <= prev_score:
    #         return

    # update_timestamp = get_now_timestamp()
    # redis_client.hset(leaderboard_timestamp_str(
    #     service_id, leader_board_id), user_id, update_timestamp)
    # stamped_user_id = timestamp_user_id(user_id, update_timestamp)
    # redis_client.zadd(leaderboard_str(
    #     service_id, leader_board_id), ch=True, mapping={stamped_user_id: body["score"]})
    return


# @lambda_handler.handle("post", path="/<string:service_id>/<string:leader_board_id>/<string:user_id>")
# def incr_score(event, service_id, leader_board_id, user_id):
#     if event["body"] is None:
#         raise InvalidRequestException("request parameter invalid")

#     body = json.loads(event["body"])

#     if "delta" not in body:
#         raise InvalidRequestException(
#             "'delta' parameter not exists in request body")

#     redis_client.zincrby(leaderboard_str(
#         service_id, leader_board_id), body["delta"], user_id)
#     return

@lambda_handler.handle("put", path="/<string:service_id>/users/<string:user_id>")
def put_user_property(event, service_id, user_id):
    body = json.loads(event["body"])
    if "properties" in body:
        redis_client.set(user_properties_key_str(service_id, user_id), json.dumps(body["properties"]))
    return


@lambda_handler.handle("delete", path="/<string:service_id>/leaderboards/<string:leader_board_id>")
def delete_leader_board(event, service_id, leader_board_id):
    auth_token = event.get("headers", {}).get("X-Auth", "")

    if auth_token != admin_secret_token:
        raise AccessDeniedException("Invalid authentication")

    redis_client.delete(leaderboard_str(service_id, leader_board_id), leaderboard_timestamp_str(service_id, leader_board_id))
    return

# for debug purpose


# @lambda_handler.handle("get")
# def get_default_handle(event):
#     return event


def handler(event, context):
    try:
        return lambda_handler(event=event)
    except (ValueError, InvalidRequestException) as verror:
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
    except AccessDeniedException as perror:
        return {
            "statusCode": "403",
            "body": json.dumps({
                "message": str(perror)
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
