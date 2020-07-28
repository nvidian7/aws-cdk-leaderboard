
# Simple leaderboard project

## Prepare CDK deploy & development environment

This is a project for mobile game leaderboard service via aws cdk as a IaC(Infrastructure as code).

The `cdk.json` file tells the CDK Toolkit how to execute your app.

This project is set up like a standard Python project.  The initialization
process also creates a virtualenv within this project, stored under the .env
directory.  To create the virtualenv it assumes that there is a `python3`
(or `python` for Windows) executable in your path with access to the `venv`
package. If for any reason the automatic creation of the virtualenv fails,
you can create the virtualenv manually.

To manually create a virtualenv on MacOS and Linux:

```
$ python -m venv .env
```

After the init process completes and the virtualenv is created, you can use the following
step to activate your virtualenv.

```
$ source .env/bin/activate
```

If you are a Windows platform, you would activate the virtualenv like this:

```
% .env\Scripts\activate.bat
```

Once the virtualenv is activated, you can install the required dependencies.

```
$ pip install -r requirements.txt
```

At this point you can now synthesize the CloudFormation template for this code.

```
$ cdk synth
```

To add additional dependencies, for example other CDK libraries, just add
them to your `setup.py` file and rerun the `pip install -r requirements.txt`
command.

### Useful commands

 * `cdk ls`          list all stacks in the app
 * `cdk synth`       emits the synthesized CloudFormation template
 * `cdk deploy`      deploy this stack to your default AWS account/region
 * `cdk diff`        compare deployed stack with current state
 * `cdk docs`        open CDK documentation

# Leaderboard API

Simple Serverless Leaderboard API. It uses

- `AWS API Gateway` and `AWS Lambda` to serve this Web API with Serverless model.
- `Redis` to sort & store score

## Documentation

### GET

#### Get specific user only

Request `GET` to `/{serviceId}/{leaderBoardId}/{userId}`

```bash
$ curl "https://API-DOMAIN/STAGE/service_id/leader_board_id/test"
{
  "rank": 321,
  "userId": "test",
  "score": 123456789123456789
}
```

#### Get `top` with `offset` and `limit` and `properties`

Request `GET` to `/{serviceId}/{leaderBoardId}/top?offset=<number>&limit=<number>&properties=<flag>`.

```bash
$ curl "https://API-DOMAIN/STAGE/service_id/leader_board_id/top?offset=0&limit=10&properties=true"
[{
  "rank": 1,
  "userId": "test",
  "score": 123456789123456789,
  "properties" : {
      "nickname" : "dennis"
  }
}, ...]
```

#### Get `around` with `limit`

Request `GET` to `/{serviceId}/{leaderBoardId}/{userId}/around?limit=<number>&properties=<flag>`

```bash
$ curl "https://API-DOMAIN/STAGE/service_id/leader_board_id/test/around?limit=10&properties=true"
[..., {
  "rank": 321,
  "userId": "test",
  "score": 123456789123456789,
  "properties" : {
      "nickname" : "dennis"
   }
}, ...]
```

### PUT

#### Put user's score

Request `PUT` to `/{serviceId}/{leaderBoardId}`

- **This API doesn't update a record when an old score is higher than a new score.**

```bash
$ curl -XPUT "https://API-DOMAIN/STAGE/service_id/leaderboard_id/test"
{
  "rank": 321,
  "userId": "test",
  "score": 123456789123456789
}
```

### PUT

#### Put service scope user property

Request `PUT` to `/{serviceId}/{userId}`

```bash
$ curl -XPUT "https://API-DOMAIN/STAGE/service_id/test" -d '{ "properties": { "nickname" : "def" } }'
```

### CLEAR

For admin purpose, it supports `CLEAR` command via `DELETE` request.

```bash
curl -XDELETE "https://API-DOMAIN/STAGE/service_id/leaderboard_id" -H "X-Auth: admin-secret-token"
```

But if `process.env.AUTH_KEY` isn't set while deploying, `X-Auth` can be omitted and it can lead very horrible problem, that is resetting all of ranks by anonymous.

## Deployment

1. Initial deploy : `cdk bootstrap` -> `cdk synth` -> `cdk deploy` command from your shell.
2. After editing some codes, deploy this stack via `cdk deploy` command.