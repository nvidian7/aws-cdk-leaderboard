#!/usr/bin/env python3
import os
import subprocess
import logging
from pathlib import Path
from tg_leaderboard.tg_leaderboard_stack import TgLeaderboardStack
from aws_cdk import (
    core,
    aws_lambda as _lambda,
    aws_apigateway as _apigw,
    aws_elasticache as _elasticache,
    aws_ec2 as _ec2,
    aws_logs as _logs,
    aws_events as _events,
    aws_events_targets as _event_targets
)


class LeaderBoardStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        vpc = _ec2.Vpc.from_lookup(self, id="vpc", vpc_id="vpc-69f45702")
        subnet_group = _elasticache.CfnSubnetGroup(self,
                                                   id="subnet-group",
                                                   description="The redis subnet group",
                                                   subnet_ids=list(map(lambda s: s.subnet_id, vpc.private_subnets)))

        security_group = _ec2.SecurityGroup.from_security_group_id(
            self, id="Security Group", security_group_id="sg-4fd0662b")

        elasticache = _elasticache.CfnCacheCluster(
            self,
            id="LeaderBoardElasticache",
            cache_node_type="cache.t2.micro",
            num_cache_nodes=1,
            engine="redis",
            engine_version="5.0.6",
            cache_parameter_group_name="default.redis5.0",
            cache_subnet_group_name=subnet_group.cache_subnet_group_name,
            vpc_security_group_ids=[security_group.security_group_id])

        elasticache.apply_removal_policy(core.RemovalPolicy.DESTROY)
        elasticache.add_depends_on(subnet_group)

        elasticache_host = elasticache.attr_redis_endpoint_address
        elasticache_port = elasticache.attr_redis_endpoint_port

        lambda_function = _lambda.Function(self, "LeaderBoardFunction",
                                           handler='lambda-handler.handler',
                                           runtime=_lambda.Runtime.PYTHON_3_8,
                                           code=_lambda.Code.from_asset(
                                               'lambda'),
                                           memory_size=128,
                                           vpc=vpc,
                                           security_group=security_group,
                                           timeout=core.Duration.seconds(10),
                                           log_retention=_logs.RetentionDays.ONE_WEEK,
                                           layers=[self.create_dependencies_layer(
                                               "tg-leaderboard", "lambda")]
                                           )

        lambda_function.add_environment("REDIS_HOST", elasticache_host)
        lambda_function.add_environment("REDIS_PORT", elasticache_port)

        base_api = _apigw.RestApi(self, 'LeaderBoardApi',
                                  rest_api_name='LeaderBoardApi')

        root_api = base_api.root
        entity_lambda_integration = _apigw.LambdaIntegration(lambda_function, proxy=True, integration_responses=[
            {
                'statusCode': '200',
                "responseParameters": {
                    'method.response.header.Access-Control-Allow-Origin': "'*'",
                }
            }
        ])

        root_api.add_method('GET', entity_lambda_integration,
                            method_responses=[{
                                'statusCode': '200',
                                'responseParameters': {
                                    'method.response.header.Access-Control-Allow-Origin': True,
                                }
                            }])

        entity = root_api.add_resource("{proxy+}")
        entity.add_method("ANY", _apigw.LambdaIntegration(
            lambda_function))

        self.add_cors_options(root_api)
        # self.enable_cron(lambda_function)

    def create_dependencies_layer(self, project_name, function_name: str) -> _lambda.LayerVersion:
        requirements_file = function_name + "/" + "requirements.txt"
        output_dir = ".lambda_dependencies/" + function_name

        # Install requirements for layer in the output_dir
        if not os.environ.get("SKIP_PIP"):
            # Note: Pip will create the output dir if it does not exist
            subprocess.check_call(
                f"pip install -r {requirements_file} -t {output_dir}/python".split()
            )
        return _lambda.LayerVersion(
            self,
            project_name + "-" + function_name + "-dependencies",
            code=_lambda.Code.from_asset(output_dir)
        )

    def add_cors_options(self, apigw_resource):
        apigw_resource.add_method('OPTIONS', _apigw.MockIntegration(
            integration_responses=[{
                'statusCode': '200',
                'responseParameters': {
                    'method.response.header.Access-Control-Allow-Headers': "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'",
                    'method.response.header.Access-Control-Allow-Origin': "'*'",
                    'method.response.header.Access-Control-Allow-Methods': "'GET,OPTIONS'"
                }
            }],
            passthrough_behavior=_apigw.PassthroughBehavior.WHEN_NO_MATCH,
            request_templates={"application/json": "{\"statusCode\":200}"}
        ),
            method_responses=[{
                'statusCode': '200',
                'responseParameters': {
                    'method.response.header.Access-Control-Allow-Headers': True,
                    'method.response.header.Access-Control-Allow-Methods': True,
                    'method.response.header.Access-Control-Allow-Origin': True,
                }
            }]
        )


def enable_cron(self, lambda_fn):
    # Schedule @ lambda_fn every minute
    rule = _events.Rule(
        self, "Rule",
        schedule=_events.Schedule.cron(
            minute='*',
            hour='*',
            month='*',
            week_day='*',
            year='*'),
    )

    # A toy input event.  You can add multiple inputs/targets, for example
    # scheduling many servers to be scanned by a scheduled lambda in parallel
    input_event = _events.RuleTargetInput.from_object(dict(foo="bar"))
    rule.add_target(_event_targets.LambdaFunction(
        lambda_fn, event=input_event))


test_env = core.Environment(account="854806466257", region="ap-northeast-2")

app = core.App()
LeaderBoardStack(app, "LeaderBoardStack", env=test_env)
app.synth()
