
# SaaS Metering system on AWS demo project!

This SaaS Metering system allows Software-as-a-Service (SaaS) providers to accurately meter and bill their customers based on precise **API usage**. This fully-managed service streamlines tracking and monetizing SaaS offerings by enabling **usage-based billing models**.

**Key features**:

1. **Usage-Based Billing**: Bill customers only for what they use based on API calls, data transfers, or custom metrics aligned with your business model.
2. **Seamless Integration**: Integrate with existing AWS infrastructure to instrument applications and capture real-time usage data.
3. **Automated Billing**: Automate billing and invoicing processes, reducing overhead.
4. **Scalability and Reliability**: Highly scalable and reliable service to support SaaS business growth.
5. **Flexible Pricing Models**: Easily extensible to support pay-per-use, tiered pricing, and custom pricing rules.

This SaaS Metering system can unlock new revenue streams, improve customer satisfaction, and provide a competitive edge in the SaaS market through accurate usage-based billing. Getting started is straightforward with this solution. SaaS providers can now streamline billing processes, optimize pricing strategies, and drive business growth with this new AWS service.

This repository provides you cdk scripts and sample codes on how to implement a simple SaaS metering system.

Below diagram shows what we are implementing.

![saas-metering-arch](./saas-metering-iceberg-arch.svg)

The `cdk.json` file tells the CDK Toolkit how to execute your app.

This project is set up like a standard Python project.  The initialization
process also creates a virtualenv within this project, stored under the `.venv`
directory.  To create the virtualenv it assumes that there is a `python3`
(or `python` for Windows) executable in your path with access to the `venv`
package. If for any reason the automatic creation of the virtualenv fails,
you can create the virtualenv manually.

To manually create a virtualenv on MacOS and Linux:

```
$ python3 -m venv .venv
```

After the init process completes and the virtualenv is created, you can use the following
step to activate your virtualenv.

```
$ source .venv/bin/activate
```

If you are a Windows platform, you would activate the virtualenv like this:

```
% .venv\Scripts\activate.bat
```

Once the virtualenv is activated, you can install the required dependencies.

```
(.venv) $ pip install -r requirements.txt
```

To add additional dependencies, for example other CDK libraries, just add
them to your `setup.py` file and rerun the `pip install -r requirements.txt`
command.

### Deploy

At this point you can now synthesize the CloudFormation template for this code.

Before synthesizing the CloudFormation, you should set approperly the cdk context configuration file, `cdk.context.json`.

In this project, we use the following cdk context:
<pre>
{
  "data_firehose_configuration": {
    "stream_name": "random-gen",
    "buffering_hints": {
      "interval_in_seconds": 60,
      "size_in_mbs": 128
    },
    "transform_records_with_aws_lambda": {
      "buffer_size": 3,
      "buffer_interval": 300,
      "number_of_retries": 3
    },
    "destination_iceberg_table_configuration": {
      "database_name": "restapi_access_log_iceberg_db",
      "table_name": "restapi_access_log_iceberg"
    },
    "output_prefix": "restapi_access_log_iceberg_db/restapi_access_log_iceberg",
    "error_output_prefix": "error/year=!{timestamp:yyyy}/month=!{timestamp:MM}/day=!{timestamp:dd}/hour=!{timestamp:HH}/!{firehose:error-output-type}"
  }
}
</pre>

:warning: You can set `s3_bucket` to store access logs for yourself. Otherwise, an `apigw-access-log-to-firehose-{region}-{account-id}` bucket will be created automatically. The `{region}` and `{account-id}` of `s3_bucket` option are replaced based on your AWS account profile. (e.g., `apigw-access-log-to-firehose-us-east-1-123456789012`)

<pre>
(.venv) $ export CDK_DEFAULT_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
(.venv) $ export CDK_DEFAULT_REGION=$(aws configure get region)
(.venv) $ cdk synth --all
</pre>

Now let's try to deploy.

## List all CDK Stacks

```
(.venv) $ cdk list
SaaSMeteringDemoDataFirehoseToIcebergS3Path
SaaSMeteringDemoFirehoseDataTransformLambdaStack
SaaSMeteringDemoFirehoseToIcebergRoleStack
SaaSMeteringDemoGrantLFPermissionsOnFirehoseRole
SaaSMeteringDemoRandomGenApiLogToFirehose
SaaSMeteringDemoRandomGenApiGw
```

Use `cdk deploy` command to create the stack shown above.

## Set up Delivery Stream

1. Create a S3 bucket for Apache Iceberg table
   <pre>
   (.venv) $ cdk deploy --require-approval never SaaSMeteringDemoDataFirehoseToIcebergS3Path
   </pre>
2. Create a table with partitioned data in Amazon Athena

   Go to [Athena](https://console.aws.amazon.com/athena/home) on the AWS Management console.<br/>
   * (step 1) Create a database

      In order to create a new database called `restapi_access_log_iceberg_db`, enter the following statement in the Athena query editor and click the **Run** button to execute the query.

      <pre>
      CREATE DATABASE IF NOT EXISTS restapi_access_log_iceberg_db;
      </pre>

   * (step 2) Create a table

      Copy the following query into the Athena query editor.

      Update `LOCATION` to your S3 bucket name and execute the query to create a new table.
      <pre>
      CREATE TABLE restapi_access_log_iceberg_db.restapi_access_log_iceberg (
         `request_id` string,
         `ip` string,
         `user` string,
         `request_time` timestamp,
         `http_method` string,
         `resource_path` string,
         `status` string,
         `protocol` string,
         `response_length` int
      )
      LOCATION 's3://apigw-access-log-to-firehose-<i>{region}</i>-<i>{account_id}</i>/restapi_access_log_iceberg_db/restapi_access_log_iceberg'
      TBLPROPERTIES (
         'table_type'='iceberg',
         'format'='parquet',
         'write_compression'='snappy',
         'optimize_rewrite_delete_file_threshold'='10'
      );
      </pre>
      If the query is successful, a table named `restapi_access_log_iceberg` is created and displayed on the left panel under the **Tables** section.

      If you get an error, check if (a) you have updated the `LOCATION` to the correct S3 bucket name, (b) you have `restapi_access_log_iceberg_db` selected under the Database dropdown, and (c) you have `AwsDataCatalog` selected as the **Data source**.
3. Create a lambda function to process the streaming data.
   <pre>
   (.venv) $ cdk deploy --require-approval never SaaSMeteringDemoFirehoseDataTransformLambdaStack
   </pre>
4. To allow Data Firehose to ingest data into the Apache Iceberg table, create an IAM role and grant permissions to the role.
   <pre>
   (.venv) $ cdk deploy --require-approval never \
                 SaaSMeteringDemoFirehoseToIcebergRoleStack \
                 SaaSMeteringDemoGrantLFPermissionsOnFirehoseRole
   </pre>

   :information_source: If you fail to create the table, give Athena users access permissions on `restapi_access_log_iceberg_db` through [AWS Lake Formation](https://console.aws.amazon.com/lakeformation/home), or you can grant Amazon Data Firehose to access `restapi_access_log_iceberg_db` by running the following command:
   <pre>
   (.venv) $ aws lakeformation grant-permissions \
                 --principal DataLakePrincipalIdentifier=arn:aws:iam::<i>{account-id}</i>:role/<i>role-id</i> \
                 --permissions CREATE_TABLE DESCRIBE ALTER DROP \
                 --resource '{ "Database": { "Name": "<i>restapi_access_log_iceberg_db</i>" } }'
   (.venv) $ aws lakeformation grant-permissions \
                 --principal DataLakePrincipalIdentifier=arn:aws:iam::<i>{account-id}</i>:role/<i>role-id</i> \
                 --permissions SELECT DESCRIBE ALTER INSERT DELETE DROP \
                 --resource '{ "Table": {"DatabaseName": "<i>restapi_access_log_iceberg_db</i>", "TableWildcard": {}} }'
   </pre>
5. Deploy Amazon Data Firehose.
   <pre>
   (.venv) $ cdk deploy --require-approval never SaaSMeteringDemoRandomGenApiLogToFirehose
   </pre>

## Create RESTful APIs endpoint

<pre>
(.venv) $ cdk deploy --require-approval never SaaSMeteringDemoRandomGenApiGw
</pre>

## Run Test

1. Register a Cognito User, using the aws cli
   <pre>
   USER_POOL_CLIENT_ID=$(aws cloudformation describe-stacks --stack-name <i>SaaSMeteringDemoRandomGenApiGw</i> | jq -r '.Stacks[0].Outputs[] | select(.OutputKey == "UserPoolClientId") | .OutputValue')

   aws cognito-idp sign-up \
     --client-id <i>${USER_POOL_CLIENT_ID}</i> \
     --username "<i>user-email-id@domain.com</i>" \
     --password "<i>user-password</i>"
   </pre>
   Note: You can find `UserPoolClientId` with the following command:
   <pre>
   aws cloudformation describe-stacks --stack-name <i>SaaSMeteringDemoRandomGenApiGw</i> | jq -r '.Stacks[0].Outputs[] | select(.OutputKey == "UserPoolClientId") | .OutputValue'
   </pre>
   :information_source: `SaaSMeteringDemoRandomGenApiGw` is the CDK stack name to create a user pool.

2. Confirm the user, so they can log in:
   <pre>
   USER_POOL_ID=$(aws cloudformation describe-stacks --stack-name <i>SaaSMeteringDemoRandomGenApiGw</i> | jq -r '.Stacks[0].Outputs | map(select(.OutputKey == "UserPoolId")) | .[0].OutputValue')

   aws cognito-idp admin-confirm-sign-up \
     --user-pool-id <i>${USER_POOL_ID}</i> \
     --username "<i>user-email-id@domain.com</i>"
   </pre>
   At this point if you look at your cognito user pool, you would see that the user is confirmed and ready to log in:
   ![amazon-cognito-user-pool-users](../assets/amazon-cognito-user-pool-users.png)

   Note: You can find `UserPoolId` with the following command:
   <pre>
   aws cloudformation describe-stacks --stack-name <i>SaaSMeteringDemoRandomGenApiGw</i> | jq -r '.Stacks[0].Outputs | map(select(.OutputKey == "UserPoolId")) | .[0].OutputValue'
   </pre>

3. Log the user in to get an identity JWT token
   <pre>
   USER_POOL_CLIENT_ID=$(aws cloudformation describe-stacks --stack-name <i>SaaSMeteringDemoRandomGenApiGw</i> | jq -r '.Stacks[0].Outputs[] | select(.OutputKey == "UserPoolClientId") | .OutputValue')

   aws cognito-idp initiate-auth \
     --auth-flow USER_PASSWORD_AUTH \
     --auth-parameters USERNAME="<i>user-email-id@domain.com</i>",PASSWORD="<i>user-password</i>" \
     --client-id <i>${USER_POOL_CLIENT_ID}</i>
   </pre>

4. Invoke REST API method
   <pre>
   $ APIGW_INVOKE_URL=$(aws cloudformation describe-stacks --stack-name <i>SaaSMeteringDemoRandomGenApiGw</i> | jq -r '.Stacks[0].Outputs | map(select(.OutputKey == "RestApiEndpoint")) | .[0].OutputValue')
   $ MY_ID_TOKEN=$(aws cognito-idp initiate-auth --auth-flow USER_PASSWORD_AUTH --auth-parameters USERNAME="<i>user-email-id@domain.com</i>",PASSWORD="<i>user-password</i>" --client-id <i>your-user-pool-client-id</i> | jq -r '.AuthenticationResult.IdToken')
   $ curl -X GET "${APIGW_INVOKE_URL}/random/strings?len=7" --header "Authorization: ${MY_ID_TOKEN}"
   </pre>

   The response is:
   <pre>
   ["weBJDKv"]
   </pre>

5. Generate test requests and run them.
   <pre>
   $ source .venv/bin/activate
   (.venv) $ pip install -U "requests>=2.31.0" "boto3>=1.34.61"
   (.venv) $ python ../tests/run_test.py \
                --apigw-invoke-url 'https://<i>{your-api-gateway-id}</i>.execute-api.<i>{region}</i>.amazonaws.com/prod' \
                --auth-token ${MY_ID_TOKEN} \
                --max-count 10
   </pre>

6. Check the access logs in S3

   After `5~10` minutes, you can see that the access logs have been delivered by **Kinesis Data Firehose** to **S3** and stored in a folder structure by year, month, day, and hour.

   ![iceberg-table](../assets/access-log-iceberg-table.png)
   ![iceberg-table-data-level-01](../assets/access-log-iceberg-data-level-01.png)
   ![iceberg-table-data-level-02](../assets/access-log-iceberg-data-level-02.png)

7. Run test query

   Go to [Athena](https://console.aws.amazon.com/athena/home) on the AWS Management console.

   Enter the following SQL statement and execute the query.
   <pre>
   SELECT COUNT(*)
   FROM restapi_access_log_iceberg_db.restapi_access_log_iceberg;
   </pre>

## Clean Up

Delete the CloudFormation stack by running the below command.
<pre>
(.venv) $ cdk destroy --force --all
</pre>

## Useful commands

 * `cdk ls`          list all stacks in the app
 * `cdk synth`       emits the synthesized CloudFormation template
 * `cdk deploy`      deploy this stack to your default AWS account/region
 * `cdk diff`        compare deployed stack with current state
 * `cdk docs`        open CDK documentation

Enjoy!

## References

 * [Amazon API Gateway - Logging API calls to Kinesis Data Firehose](https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-logging-to-kinesis.html)
 * [Setting up CloudWatch logging for a REST API in API Gateway](https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-logging.html)
 * [Amazon API Gateway - $context Variables for data models, authorizers, mapping templates, and CloudWatch access logging](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-mapping-template-reference.html#context-variable-reference)
 * [Amazon AIP Gateway - Integrate a REST API with an Amazon Cognito user pool](https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-enable-cognito-user-pool.html)
 * [Building fine-grained authorization using Amazon Cognito, API Gateway, and IAM (2021-05-21)](https://aws.amazon.com/ko/blogs/security/building-fine-grained-authorization-using-amazon-cognito-api-gateway-and-iam/)
 * [How to resolve "Invalid permissions on Lambda function" errors from API Gateway REST APIs](https://aws.amazon.com/premiumsupport/knowledge-center/api-gateway-rest-api-lambda-integrations/)
 * [AWS Lake Formation - Create a data lake administrator](https://docs.aws.amazon.com/lake-formation/latest/dg/getting-started-setup.html#create-data-lake-admin)
 * [AWS Lake Formation Permissions Reference](https://docs.aws.amazon.com/lake-formation/latest/dg/lf-permissions-reference.html)
 * [Tutorial: Schedule AWS Lambda Functions Using CloudWatch Events](https://docs.aws.amazon.com/AmazonCloudWatch/latest/events/RunLambdaSchedule.html)
 * [Amazon Athena Workshop](https://athena-in-action.workshop.aws/)
 * [Curl Cookbook](https://catonmat.net/cookbooks/curl)

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.

