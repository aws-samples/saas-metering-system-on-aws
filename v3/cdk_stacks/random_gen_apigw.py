#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import os

import aws_cdk as cdk

from aws_cdk import (
  Stack,
  aws_apigateway,
  aws_cognito,
  aws_iam,
  aws_lambda,
  aws_logs,
)
from constructs import Construct


class RandomGenApiStack(Stack):

  def __init__(self, scope: Construct, construct_id: str, firehose_arn, **kwargs) -> None:
    super().__init__(scope, construct_id, **kwargs)

    user_pool = aws_cognito.UserPool(self, 'UserPool',
      user_pool_name='UserPoolForApiGateway',
      removal_policy=cdk.RemovalPolicy.DESTROY,
      self_sign_up_enabled=True,
      sign_in_aliases={'email': True},
      auto_verify={'email': True},
      password_policy={
        'min_length': 8,
        'require_lowercase': False,
        'require_digits': False,
        'require_uppercase': False,
        'require_symbols': False,
      },
      account_recovery=aws_cognito.AccountRecovery.EMAIL_ONLY
    )

    user_pool_client = aws_cognito.UserPoolClient(self, 'UserPoolClient',
      user_pool=user_pool,
      auth_flows={
        'admin_user_password': True,
        'user_password': True,
        'custom': True,
        'user_srp': True
      },
      supported_identity_providers=[aws_cognito.UserPoolClientIdentityProvider.COGNITO]
    )

    apigw_auth = aws_apigateway.CognitoUserPoolsAuthorizer(self, 'RandomStringsApiAuthorizer',
      cognito_user_pools=[user_pool]
    )

    #XXX: CloudWatch Logs role ARN must be set in account settings to enable logging
    cloudwatch_role = aws_iam.Role(self, 'ApiGatewayCloudWatchRole',
      assumed_by=aws_iam.ServicePrincipal('apigateway.amazonaws.com'),
      managed_policies=[
        aws_iam.ManagedPolicy.from_aws_managed_policy_name('service-role/AmazonAPIGatewayPushToCloudWatchLogs')
      ]
    )
    cloudwatch_role.apply_removal_policy(cdk.RemovalPolicy.DESTROY)

    #XXX: CloudWatch Logs role ARN must be set in account settings to enable logging
    apigw_account = aws_apigateway.CfnAccount(self, 'ApiGatewayAccount',
      cloud_watch_role_arn=cloudwatch_role.role_arn
    )
    apigw_account.apply_removal_policy(cdk.RemovalPolicy.DESTROY)

    random_gen_lambda_fn = aws_lambda.Function(self, 'RandomStringsLambdaFn',
      runtime=aws_lambda.Runtime.PYTHON_3_9,
      function_name="RandomStrings",
      handler="random_strings.lambda_handler",
      description='Function that returns strings randomly generated',
      code=aws_lambda.Code.from_asset(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src/main/python/RestAPIs')),
      timeout=cdk.Duration.minutes(5)
    )

    random_gen_api_log_group = aws_logs.LogGroup(self, 'RandomGenApiLogs')

    #XXX: For more information about $context variables, see
    # https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-mapping-template-reference.html#context-variable-reference
    #XXX: Using aws_apigateway.AccessLogFormat.custom(json.dumps({..}))
    # or aws_apigateway.AccessLogFormat.json_with_standard_fields()
    # make json's all attributes string data type even if they are numbers
    # So, it's better to define access log format in the string like this.
    # Don't forget the new line to make JSON Lines.
    access_log_format = '''{"request_id": "$context.requestId",\
 "ip": "$context.identity.sourceIp",\
 "user": "$context.authorizer.claims['cognito:username']",\
 "request_time": $context.requestTimeEpoch,\
 "http_method": "$context.httpMethod",\
 "resource_path": "$context.resourcePath",\
 "status": $context.status,\
 "protocol": "$context.protocol",\
 "response_length": $context.responseLength}\n'''

    random_strings_rest_api = aws_apigateway.LambdaRestApi(self, 'RandomStringsApi',
      rest_api_name="random-strings",
      handler=random_gen_lambda_fn,
      proxy=False,
      deploy=True,
      deploy_options=aws_apigateway.StageOptions(stage_name="dev",
        data_trace_enabled=True,
        logging_level=aws_apigateway.MethodLoggingLevel.INFO,
        metrics_enabled=True,
        #XXX: You can't use Kinesis Data Firehose as the access_log_destination
        access_log_destination=aws_apigateway.LogGroupLogDestination(random_gen_api_log_group),
        access_log_format=aws_apigateway.AccessLogFormat.custom(access_log_format)
      ),
      endpoint_export_name='RestApiEndpoint'
    )

    random_strings_rest_api_deployment = aws_apigateway.Deployment(self, "RandomStringsApiGwDeployment",
      api=random_strings_rest_api)

    #XXX: In order to set Kinesis Data Firehose to access log destination, use aws_apigateway.CfnStage(...) construct
    random_strings_rest_api_stage = aws_apigateway.CfnStage(self, "RandomStringsApiGwStage",
      rest_api_id=random_strings_rest_api.rest_api_id,
      access_log_setting=aws_apigateway.CfnStage.AccessLogSettingProperty(
        destination_arn=firehose_arn,
        format=access_log_format
      ),
      deployment_id=random_strings_rest_api_deployment.deployment_id,
      method_settings=[aws_apigateway.CfnStage.MethodSettingProperty(
        http_method="*",
        logging_level="ERROR",
        metrics_enabled=True,
        resource_path="/*"
      )],
      stage_name="prod"
    )

    #XXX: should add the lambda invoke permission for the apigateway stage
    # https://aws.amazon.com/premiumsupport/knowledge-center/api-gateway-rest-api-lambda-integrations/
    random_gen_lambda_fn.add_permission(id='RandomStringsApiLambdaPermission',
      principal=aws_iam.ServicePrincipal("apigateway.amazonaws.com"),
      action="lambda:InvokeFunction",
      source_arn=f'arn:aws:execute-api:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}:{random_strings_rest_api.rest_api_id}/{random_strings_rest_api_stage.stage_name}/GET/random/strings'
    )

    random_gen = random_strings_rest_api.root.add_resource("random")
    random_strings_gen = random_gen.add_resource("strings")
    random_strings_gen.add_method('GET',
      aws_apigateway.LambdaIntegration(
        handler=random_gen_lambda_fn
      ),
      authorization_type=aws_apigateway.AuthorizationType.COGNITO,
      authorizer=apigw_auth
    )

    cdk.CfnOutput(self, 'UserPoolId', value=user_pool.user_pool_id)
    cdk.CfnOutput(self, 'UserPoolClientId', value=user_pool_client.user_pool_client_id)
    cdk.CfnOutput(self, 'RestApiAccessLogToFirehoseARN', value=firehose_arn)
    cdk.CfnOutput(self, 'RestApiAccessLogGroupName', value=random_gen_api_log_group.log_group_name)
    cdk.CfnOutput(self, 'RestApiEndpoint',
      value=f'https://{random_strings_rest_api.rest_api_id}.execute-api.{cdk.Aws.REGION}.amazonaws.com/{random_strings_rest_api_stage.stage_name}',
      export_name=f'RestApiEndpoint-Prod')
