# Simple leaderboard for game service

Amazone AWS CDK(Cloud Development Kit)를 이용한 IaC(Infrastructure as code) 구성

## 환경 구성하기

- Node.js 12.18.2 이상
- Python 3.7 이상
- AWS CLI 2 이상

CDK를 통한 IaC 구성에 어떤 언어를 사용하더라도 aws cdk command line tool 자체는 npm을 통한 global 설치가 필요합니다.

```bash
npm install -g aws-cdk
```

이 프로젝트는 표준 Python 프로젝트 형태로 구성되어있습니다. 시작하기 전에 virtualenv를 설정하여 이 프로젝트의 개발&배포 환경이 전역적인 Python 환경에 영향을 주지 않도록 설정합니다.

프로젝트 디렉토리의 최상위에 virtualenv를 .env라는 이름으로 생성합니다.

```bash
$ python -m venv .env
```

virtualenv가 생성되었으면, 활성화 해줍니다. 이 단계는 개발&배포가 필요할때마다 반복적으로 수행되어야합니다.

```bash
$ source .env/bin/activate
```

만약 Windows를 사용하고 있다면, batch 파일을 통해서 virtualenv를 활성화 합니다.

```bash
% .env\Scripts\activate.bat
```

virtualenv가 활성화 되었으면, requirements.txt에 서술되어있는 dependency들을 venv에 설치합니다.

```bash
$ pip install -r requirements.txt
```

프로젝트 디렉토리 루트의 environment.py에 세부 설정을 수정합니다.

```python
# Service metadata
SERVICE_ID = "shadow-of-eclipse"
ADMIN_SECRET_TOKEN = "secret-token"

# AWS configuration
AWS_VPC_ID = "vpc-69f45702"
AWS_SECURITY_GROUP_ID = "sg-4fd0662b"
AWS_ACCOUNT_ID = "123456789000"
AWS_DEFAULT_REGION = "ap-northeast-2"

# Leaderboard configuration
DEFAULT_FETCH_COUNT = 100
MAX_FETCH_COUNT = 1000
```

엄밀하게는 IaC라고 할 수 없지만, 기존에 이미 사용하고 있던 AWS 계정과의 통합을 목표로하였기 때문에 추가적인 VPC와 SecurityGroup을 생성하지 않고 사용중인 계정의 vpc와 security group을 lookup 하여 lambda 및 elasticache를 통합합니다. 때문에 설정파일에서 배포 대상이 될 기존 계정의 vpc와 security group 식별자를 정확히 설정하여야 합니다. 기존에 사용하던 vpc 및 security group이 없다면 aws console이나 aws-cli를 통하여 수동으로 생성 후 통합을 시도하세요.

여기까지 진행했으면 이 프로젝트를 위해서 정의된 CloudFormation 문법을 생성해 볼 수 있습니다. 

```bash
$ cdk synth
```

프로젝트에 추가 의존성이 필요한 경우 프로젝트 디렉토리 최상위의 requirements.txt에 의존성을 추가할 수 있습니다. 

```bash
$ pip install pyredis
$ pip install flask
```

이 파일에는 배포 및 구성을 위한 AWS CDK 의존성과 lambda 로직 개발환경을 위한 AWS SDK, 기타 서드파티 모듈 의존성이 모두 추가됩니다.  하지만 배포 과정에서 lambda asset이 패키징되어 로컬 개발환경의 서드파티 모듈의 의존성이 함께 배포되지 않기 때문에, 이 프로젝트에서는 별도의 의존성 lambda layer를 추가로 생성&배포합니다. 

Python AWS CDK 모듈들은 lambda asset에 포함될 필요가 없으므로, 가벼운 의존성 lambda layer생성을 위해 runtime에서만 필요한 모듈의 명세를 작성할 필요가 있습니다. 

이 lambda runtime 만을 위한 python 모듈 의존성은 lambda/requirements.txt 파일에 수동으로 추가되어야 합니다.

| 경로                                           | 용도                          |
| ---------------------------------------------- | ----------------------------- |
| {projectRootDirectory}/requirements.txt        | CDK + 3rd Party python module |
| {projectRootDirectory}/lambda/requirements.txt | Only 3rd Party python module  |



## 배포하기

### 최초 배포

최초 배포시에는 bootstrap 명령을 통해서 배포를 위한 aws s3 bucket 등이 생성되어야 합니다.

```bash
$ cdk bootstrap
$ cdk synth
$ cdk deploy
```

이후에는 `cdk deploy` 명령어를 통해서 반복적으로 배포할 수 있습니다.

```bash
cdk deploy
```

### CDK Command Line Tool 명령어

 * `cdk ls`          list all stacks in the app
 * `cdk synth`       emits the synthesized CloudFormation template
 * `cdk deploy`      deploy this stack to your default AWS account/region
 * `cdk diff`        compare deployed stack with current state
 * `cdk docs`        open CDK documentation

더 자세한 정보는 [aws-cdk](https://docs.aws.amazon.com/cdk/latest/guide/getting_started.html) 문서를 참조하세요.

# Limitation

- 0 이하 값의 저장 및 정렬을 지원하지 않습니다.
- 명시적인 리더보드의 생성/삭제 시점이 없기 때문에, 리더보드 고유의 옵션 저장을 지원하지 않습니다. (정렬방식, 리셋주기 등)
- 상대적으로 작은 값이 상위의 순위를 가지는 오름차순 정렬을 지원하지 않습니다. ( 타임어택 랭킹 )
- 동점자의 상대 정렬은 먼저 해당 점수를 달성한 시간순 정렬로 고정됩니다.

# Leaderboard API

- `AWS API Gateway` 와 `AWS Lambda` 로 구성된 서버리스 모델로 별도의 Computing 인스턴스 관리가 필요 없습니다.
- 유저별 점수의 저장 및 정렬은 `Redis` 를 이용합니다.

## Endpoints

- `GET` /{serviceId}/leaderboards/{leaderBoardId}
- `GET` /{serviceId}/leaderboards/{leaderBoardId}/{userId}
- `GET` /{serviceId}/leaderboards/{leaderBoardId}/top
- `GET` /{serviceId}/leaderboards/{leaderBoardId}/{userId}/around
- `PUT` /{serviceId}/users/{userId}
- `PUT` /{serviceId}/leaderboards/{leaderBoardId}/{userId}
- `DELETE` /{serviceId}/leaderboards/{leaderBoardId}/{userId}
- `DELETE` /{serviceId}/leaderboards/{leaderBoardId}

## URL Query Parameter

### limit=(number)

한번에 획득할 수 있는 랭킹 데이터의 수를 제한합니다. 명시적으로 지정하지 않은 경우에는 `environment.py` 에 설정된 기본값 (`DEFAULT_FETCH_COUNT`)을 따릅니다.  최대값은 `environment.py` 의 `MAX_FETCH_COUNT` 값으로 제한되며 그 이상의 값을 지정해도 내부적으로 최대값으로 처리됩니다.

### offset=(number)

top 랭킹 조회에서 획득을 시작할 offset을 입력합니다. 예를 들어 10을 입력한 경우 10위부터 상위점수 랭킹을 획득합니다. 최대 cardinality 보다 큰 값을 입력했을 경우 비어있는 json array가 반환됩니다.

### properties=(boolean)

랭킹 정보를 획득시에 서비스 범위 안에서 유효한 유저의 custom property를 포함합니다. 별도로 지정하지 않을시 `false`이며 property를 같이 조회하는 않는 쪽이 성능상 이점이 큽니다.

## Common Response

- `HTTP 400 Error` : 잘못된 요청이나 범위를 벗어난 요청인 경우의 응답입니다 ( 예를들면, 최고 점수 갱신 API에 음수를 입력 )
- `HTTP 403 Error` : 관리용으로 제공하는 `리더보드 삭제 API`의 `token` 인증이 실패한 경우
- `HTTP 404 Error` : 존재하지 않는 유저의 점수와 랭킹을 요청한 경우입니다. 잘못된 URL호출이 아닌 API에서 404 Error를 응답하는 경우에는 response body에 포함된 `message` 필드를 참조하여 문제를 해결하세요.
- `HTTP 500 Error` : 기타 식별되지 않은 모든 예외와 에러는 500 을 반환합니다.

## Example

### GET

#### 리더보드의 metadata를 획득 

현재는 해당 리더보드에 등록된 user의 수(cardinality)만 제공합니다.

Request `GET` to `/{serviceId}/leaderboards/{leaderBoardId}`

```bash
$ curl "https://API-DOMAIN/STAGE/{serviceId}/leaderboards/{leaderBoardId}"
{
  "cardinality" : 331
}
```

#### 특정 유저의 점수 획득

Request `GET` to `/{serviceId}/leaderboards/{leaderBoardId}/{userId}?properties=<flag>`

```bash
$ curl "https://API-DOMAIN/STAGE/{serviceId}/leaderboards/{leaderBoardId}/{userId}"
{
  "rank": 321,
  "userId": "{userId}",
  "score": 123456789123456789,
  "properties" : {
      "nickname" : "dennis"
  }
}
```

#### 최상위 랭킹 획득

Request `GET` to `/{serviceId}/leaderboards/{leaderBoardId}/top?offset=<number>&limit=<number>&properties=<flag>`.

```bash
$ curl "https://API-DOMAIN/STAGE/{serviceId}/leaderboards/{leaderBoardId}/top?offset=0&limit=10&properties=true"
[{
  "rank": 1,
  "userId": "{userId}",
  "score": 123456789123456789,
  "properties" : {
      "nickname" : "dennis"
  }
}, ...]
```

#### 특정 유저 주변에 위치한 랭킹 정보 획득

Request `GET` to `/{serviceId}/leaderboards/{leaderBoardId}/{userId}/around?limit=<number>&properties=<flag>`

```bash
$ curl "https://API-DOMAIN/STAGE/{serviceId}/leaderboards/{leaderBoardId}/{userId}/around?limit=10&properties=true"
[..., {
  "rank": 321,
  "userId": "{userId}",
  "score": 123456789123456789,
  "properties" : {
      "nickname" : "John Doe"
   }
}, ...]
```

### PUT

#### 유저의 최고 점수 갱신

갱신에 성공한 경우 갱신되기 이전의 점수를 응답으로 회신합니다. ( 유저의 개인 최대 스코어 갱신등에 유용하게 쓰일 수 있습니다. )

Request `PUT` to `/{serviceId}/leaderboards/{leaderBoardId}/{userId}`

- **이 API는 기록된 점수 보다 낮은 점수로는 갱신하지 않습니다.**

Request

```bash
$ curl -XPUT "https://API-DOMAIN/STAGE/{serviceId}/leaderboards/{leaderBoardId}/{userId}" \ 
-d '{
  "score" : 100
}'
```

Response

```bash
{
    "prevScore": 0
}
```

#### 서비스에 범위의 유저 속성 갱신

부분 업데이트가 아닌 유저의 property 전체를 업데이트합니다.

Request `PUT` to `/{serviceId}/users/{userId}`

```bash
$ curl -XPUT "https://API-DOMAIN/STAGE/{serviceId}/users/{userId}" \ 
-d '{ "properties": { "nickname" : "John Doe" } }'
```

### DELETE

#### 유저 점수 삭제

Request `DELETE` to `/{serviceId}/leaderboards/{leaderBoardId}/{userId}`

```bash
$ curl -XDELETE "https://API-DOMAIN/STAGE/{serviceId}/leaderboards/{leaderBoardId}/{userId}"
```

#### 리더보드 제거

관리목적으로 리더보드 자체를 삭제하는 기능을 제공합니다. 이 요청은 다른 요청과 다르게 environment.py에 설정하는 secret token 값을 헤더에 포함하여 요청합니다.

```bash
$ curl -XDELETE "https://API-DOMAIN/STAGE/{serviceId}/leaderboards/{leaderBoardId}" -H "X-Auth: admin-secret-token"
```
