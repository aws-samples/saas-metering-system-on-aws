#!/usr/bin/env python3
import os

import aws_cdk as cdk

from saas_metering_demo import (
  KmsKeyStack,
  KinesisFirehoseStack,
  RandomGenApiStack,
  VpcStack,
  AthenaWorkGroupStack,
  AthenaNamedQueryStack,
  MergeSmallFilesLambdaStack
)

AWS_ENV = cdk.Environment(account=os.getenv('CDK_DEFAULT_ACCOUNT'),
  region=os.getenv('CDK_DEFAULT_REGION'))

app = cdk.App()

vpc_stack = VpcStack(app, 'SaaSMeteringDemoVpc',
  env=AWS_ENV)

kms_key_stack = KmsKeyStack(app, 'SaaSMeteringKmsKey')
firehose_stack = KinesisFirehoseStack(app, 'RandomGenApiLogToFirehose', kms_key_stack.kms_key.key_arn)
random_gen_apigw = RandomGenApiStack(app, 'RandomGenApiGw', firehose_stack.firehose_arn)

athena_work_group_stack = AthenaWorkGroupStack(app,
  'SaaSMeteringAthenaWorkGroup',
  kms_key_stack.kms_key.key_arn
)

merge_small_files_stack = MergeSmallFilesLambdaStack(app,
  'RestApiAccessLogMergeSmallFiles',
  firehose_stack.s3_dest_bucket_name,
  firehose_stack.s3_dest_folder_name,
  athena_work_group_stack.athena_work_group_name
)

AthenaNamedQueryStack(app,
  'SaaSMeteringAthenaNamedQueries',
  athena_work_group_stack.athena_work_group_name,
  merge_small_files_stack.s3_json_location,
  merge_small_files_stack.s3_parquet_location
)

app.synth()

