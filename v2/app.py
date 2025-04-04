#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import os

import aws_cdk as cdk

from cdk_stacks import (
  RandomGenApiStack,
  FirehoseToIcebergStack,
  FirehoseRoleStack,
  FirehoseDataProcLambdaStack,
  DataLakePermissionsStack,
  S3BucketStack
)

AWS_ENV = cdk.Environment(account=os.getenv('CDK_DEFAULT_ACCOUNT'),
  region=os.getenv('CDK_DEFAULT_REGION'))

app = cdk.App()

s3_dest_bucket = S3BucketStack(app, 'SaaSMeteringDemoDataFirehoseToIcebergS3Path',
  env=AWS_ENV)

firehose_data_transform_lambda = FirehoseDataProcLambdaStack(app,
  'SaaSMeteringDemoFirehoseDataTransformLambdaStack',
  env=AWS_ENV
)
firehose_data_transform_lambda.add_dependency(s3_dest_bucket)

firehose_role = FirehoseRoleStack(app, 'SaaSMeteringDemoFirehoseToIcebergRoleStack',
  firehose_data_transform_lambda.data_proc_lambda_fn,
  s3_dest_bucket.s3_bucket,
  env=AWS_ENV
)
firehose_role.add_dependency(firehose_data_transform_lambda)

grant_lake_formation_permissions = DataLakePermissionsStack(app,
  'SaaSMeteringDemoGrantLFPermissionsOnFirehoseRole',
  firehose_role.firehose_role,
  env=AWS_ENV
)
grant_lake_formation_permissions.add_dependency(firehose_role)

firehose_stack = FirehoseToIcebergStack(app, 'SaaSMeteringDemoRandomGenApiLogToFirehose',
  firehose_data_transform_lambda.data_proc_lambda_fn,
  s3_dest_bucket.s3_bucket,
  firehose_role.firehose_role,
  env=AWS_ENV
)
firehose_stack.add_dependency(grant_lake_formation_permissions)

random_gen_apigw = RandomGenApiStack(app, 'SaaSMeteringDemoRandomGenApiGw',
  firehose_stack.firehose_arn,
  env=AWS_ENV
)
random_gen_apigw.add_dependency(firehose_stack)

app.synth()
