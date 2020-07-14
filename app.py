#!/usr/bin/env python3

from aws_cdk import core

from tg_leaderboard.tg_leaderboard_stack import TgLeaderboardStack


app = core.App()
TgLeaderboardStack(app, "tg-leaderboard")

app.synth()
