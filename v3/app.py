#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import os

import aws_cdk as cdk

from cdk_stacks import (
  DataLakePermissionsStack,
  FirehoseDataProcLambdaStack,
  FirehoseRoleStack,
  FirehoseToS3TablesStack,
  GlueDatabaseForS3TablesStack,
  RandomGenApiStack,
  S3BucketStack,
  S3TablesStack
)


AWS_ENV = cdk.Environment(account=os.getenv('CDK_DEFAULT_ACCOUNT'),
  region=os.getenv('CDK_DEFAULT_REGION'))

app = cdk.App()

s3table_bucket = S3TablesStack(app, 'SaaSMeteringDemoS3TablesTableBucket',
  env=AWS_ENV)

s3table_resource_link = GlueDatabaseForS3TablesStack(app, 'SaaSMeteringDemoS3TablesResourceLink',
  s3table_bucket.table_bucket_name,
  env=AWS_ENV)
s3table_resource_link.add_dependency(s3table_bucket)

s3_error_output_bucket = S3BucketStack(app, 'SaaSMeteringDemoS3TablesS3ErrorOutputPath',
  env=AWS_ENV)
s3_error_output_bucket.add_dependency(s3table_resource_link)

firehose_data_transform_lambda = FirehoseDataProcLambdaStack(app,
  'SaaSMeteringDemoFirehoseDataTransformLambdaStack',
  env=AWS_ENV
)
firehose_data_transform_lambda.add_dependency(s3_error_output_bucket)

firehose_role = FirehoseRoleStack(app, 'SaaSMeteringDemoFirehoseToS3TablesRole',
  firehose_data_transform_lambda.data_proc_lambda_fn,
  s3_error_output_bucket.s3_bucket,
  env=AWS_ENV
)
firehose_role.add_dependency(firehose_data_transform_lambda)

grant_lake_formation_permissions = DataLakePermissionsStack(app,
  'SaaSMeteringDemoGrantLFPermissionsOnFirehoseRole',
  s3table_bucket.table_bucket_name,
  firehose_role.firehose_role,
  s3table_resource_link.s3table_resource_link,
  env=AWS_ENV
)
grant_lake_formation_permissions.add_dependency(firehose_role)

firehose_stack = FirehoseToS3TablesStack(app, 'SaaSMeteringDemoRandomGenApiLogToFirehose',
  firehose_data_transform_lambda.data_proc_lambda_fn,
  s3_error_output_bucket.s3_bucket,
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
