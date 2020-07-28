# pick specific user's score and rank
lua_script_get_my_rank = """
local stored_update_timestamp = redis.call('HGET', KEYS[2], ARGV[1])

if not stored_update_timestamp then
  return nil
end

local rank = redis.call('ZREVRANK', KEYS[1], stored_update_timestamp .. ":" .. ARGV[1])
if not rank then
  -- Key or member not found
  return nil
end

local score = redis.call('ZSCORE', KEYS[1], stored_update_timestamp .. ":" .. ARGV[1])
return {rank+1, ARGV[1], tonumber(score)}
"""


lua_script_get_around = """
local stored_update_timestamp = redis.call('HGET', KEYS[2], ARGV[1])

if not stored_update_timestamp then
  return nil
end

local rank = redis.call('ZREVRANK', KEYS[1], stored_update_timestamp .. ":" .. ARGV[1])
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
  data[#data+1] = tonumber(range[((i-r1)*2)+2])
end

return data
"""


lua_script_put_score = """
local leaderboard_id, timestamp_hash_set_id = KEYS[1], KEYS[2]
local user_id, new_score, timestamp = ARGV[1], tonumber(ARGV[2]), ARGV[3]
local stored_update_timestamp = redis.call('HGET', timestamp_hash_set_id, user_id)

if new_score <= 0 then
  return
end

local prev_score
if stored_update_timestamp then
  prev_score = redis.call('ZSCORE', leaderboard_id, stored_update_timestamp .. ":" .. user_id)
end

if not prev_score then
  prev_score = 0
end

prev_score = tonumber(prev_score)

if new_score > prev_score then
  if prev_score > 0 and stored_update_timestamp then
    redis.call('ZREM', leaderboard_id, stored_update_timestamp .. ":" .. user_id)
  end
  redis.call('ZADD', leaderboard_id, new_score, timestamp .. ":" .. user_id)
  redis.call('HSET', timestamp_hash_set_id, user_id, timestamp)
end
"""
