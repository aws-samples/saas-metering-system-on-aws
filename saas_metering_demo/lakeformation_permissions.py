import aws_cdk as cdk

from aws_cdk import (
  Stack,
  aws_lakeformation
)
from constructs import Construct

class DataLakePermissionsStack(Stack):

  def __init__(self, scope: Construct, construct_id: str, job_role, **kwargs) -> None:
    super().__init__(scope, construct_id, **kwargs)

    #XXXX: The role assumed by cdk is not a data lake administrator.
    # So, deploying PrincipalPermissions meets the error such as:
    # "Resource does not exist or requester is not authorized to access requested permissions."
    # In order to solve the error, it is necessary to promote the cdk execution role to the data lake administrator.
    # For example, https://github.com/aws-samples/data-lake-as-code/blob/mainline/lib/stacks/datalake-stack.ts#L68
    cfn_data_lake_settings = aws_lakeformation.CfnDataLakeSettings(self, "CfnDataLakeSettings",
      admins=[aws_lakeformation.CfnDataLakeSettings.DataLakePrincipalProperty(
        data_lake_principal_identifier=cdk.Fn.sub(self.synthesizer.cloud_formation_execution_role_arn)
      )]
    )

    athena_database_info = self.node.try_get_context('merge_small_files_lambda_env')
    old_database_name = athena_database_info['OLD_DATABASE']
    new_database_name = athena_database_info['NEW_DATABASE']

    for idx, database_name in enumerate(list(set([old_database_name, new_database_name]))):
      cfn_principal_permissions = aws_lakeformation.CfnPrincipalPermissions(self, f"LFPermissionsOnDatabase{idx}",
        permissions=["CREATE_TABLE", "SELECT", "INSERT", "DELETE", "DESCRIBE", "ALTER", "DROP"],
        permissions_with_grant_option=[],
        principal=aws_lakeformation.CfnPrincipalPermissions.DataLakePrincipalProperty(
          data_lake_principal_identifier=job_role.role_arn
        ),
        resource=aws_lakeformation.CfnPrincipalPermissions.ResourceProperty(
          database=aws_lakeformation.CfnPrincipalPermissions.DatabaseResourceProperty(
            catalog_id=cdk.Aws.ACCOUNT_ID,
            name=database_name
          )
        )
      )
      cfn_principal_permissions.apply_removal_policy(cdk.RemovalPolicy.DESTROY)
      #XXX: In order to keep resource destruction order,
      # set dependency between CfnDataLakeSettings and CfnPrincipalPermissions
      cfn_principal_permissions.add_dependency(cfn_data_lake_settings)
      cdk.CfnOutput(self, f'{self.stack_name}_PrincipalOnDatabase{idx}',
        value=cfn_principal_permissions.attr_principal_identifier)

    for idx, database_name in enumerate(list(set([old_database_name, new_database_name]))):
      cfn_principal_permissions = aws_lakeformation.CfnPrincipalPermissions(self, f"LFPermissionsOnTable{idx}",
        permissions=["SELECT", "INSERT", "DELETE", "DESCRIBE", "ALTER", "DROP"],
        permissions_with_grant_option=[],
        principal=aws_lakeformation.CfnPrincipalPermissions.DataLakePrincipalProperty(
          data_lake_principal_identifier=job_role.role_arn
        ),
        resource=aws_lakeformation.CfnPrincipalPermissions.ResourceProperty(
          #XXX: Can't specify a TableWithColumns resource and a Table resource
          table=aws_lakeformation.CfnPrincipalPermissions.TableResourceProperty(
            catalog_id=cdk.Aws.ACCOUNT_ID,
            database_name=database_name,
            # name="ALL_TABLES",
            table_wildcard={}
          )
        )
      )
      cfn_principal_permissions.apply_removal_policy(cdk.RemovalPolicy.DESTROY)

      #XXX: In order to keep resource destruction order,
      # set dependency between CfnDataLakeSettings and CfnPrincipalPermissions
      cfn_principal_permissions.add_dependency(cfn_data_lake_settings)

      cdk.CfnOutput(self, f'{self.stack_name}_PrincipalOnTable{idx}',
        value=cfn_principal_permissions.attr_principal_identifier)
