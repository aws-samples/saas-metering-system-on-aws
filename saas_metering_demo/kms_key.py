#!/usr/bin/env python3

import aws_cdk as cdk

from aws_cdk import (
  Stack,
  aws_kms
)
from constructs import Construct

class KmsKeyStack(Stack):

  def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
    super().__init__(scope, construct_id, **kwargs)

    self.kms_key = aws_kms.Key(self, "MyEncryptionKey",
      alias='SaaSMeteringDemo',
      # enable_key_rotation=False,
      removal_policy=cdk.RemovalPolicy.DESTROY)

    cdk.CfnOutput(self, 'KmsKeyId', value=self.kms_key.key_id,
      export_name=f'{self.stack_name}-KmsKeyId')
    cdk.CfnOutput(self, 'KmsKeyArn', value=self.kms_key.key_arn,
      export_name=f'{self.stack_name}-KmsKeyArn')

