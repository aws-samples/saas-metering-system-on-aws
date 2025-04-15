#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
#vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import base64
import collections
import json
import logging
import os
from datetime import datetime


LOGGER = logging.getLogger()
if len(LOGGER.handlers) > 0:
  # The Lambda environment pre-configures a handler logging to stderr.
  # If a handler is already configured, `.basicConfig` does not execute.
  # Thus we set the level directly.
  LOGGER.setLevel(logging.INFO)
else:
  logging.basicConfig(level=logging.INFO)


DESTINATION_DATABASE_NAME = os.environ['IcebergDatabaseName']
DESTINATION_TABLE_NAME = os.environ['IcebergTableName']
DESTINATION_TABLE_UNIQUE_KEYS = os.environ.get('IcebergTableUniqueKeys', None)


def lambda_handler(event, context):
  counter = collections.Counter(total=0, valid=0, invalid=0)
  firehose_records_output = {'records': []}

  unique_keys_exist = True if DESTINATION_TABLE_UNIQUE_KEYS else False
  otf_metadata_operation = 'insert' if not unique_keys_exist else 'update'

  for record in event['records']:
    counter['total'] += 1

    payload = base64.b64decode(record['data']).decode('utf-8')
    is_valid = True
    try:
      json_value = json.loads(payload)
      json_value['request_time'] = datetime.fromtimestamp(json_value['request_time']/1000).strftime('%Y-%m-%dT%H:%M:%SZ')
      payload = json.dumps(json_value)
    except Exception as _:
      is_valid = False
    counter['valid' if is_valid else 'invalid'] += 1

    firehose_record = {
      'data': base64.b64encode(payload.encode('utf-8')),
      'recordId': record['recordId'],
      'result': 'Ok' if is_valid else 'ProcessingFailed', # [Ok, Dropped, ProcessingFailed]
      'metadata': {
        'otfMetadata': {
          'destinationDatabaseName': DESTINATION_DATABASE_NAME,
          'destinationTableName': DESTINATION_TABLE_NAME,
          'operation': otf_metadata_operation
        }
      }
    }

    firehose_records_output['records'].append(firehose_record)

  LOGGER.info(', '.join("{}={}".format(k, v) for k, v in counter.items()))

  return firehose_records_output


if __name__ == '__main__':
  import pprint

  record_list = [
    ('Ok', {
      "request_id": "685f946b-99b5-4281-9ea1-c46373b50a6d",
      "ip": "210.117.121.42",
      "user": "0498a4d8-40b1-70cb-b99d-aff1d09dde75",
      "request_time": 1743740705172,
      "http_method": "GET",
      "resource_path": "/random/strings",
      "status": 200,
      "protocol": "HTTP/1.1",
      "response_length": 20
    }),
    ('ProcessingFailed', {
      "request_id": "685f946b-99b5-4281-9ea1-c46373b50a6d",
      "ip": "210.117.121.42",
      "user": "0498a4d8-40b1-70cb-b99d-aff1d09dde75",
      # invalid datetime format
      "request_time": "1743740705172",
      "http_method": "GET",
      "resource_path": "/random/strings",
      "status": 200,
      "protocol": "HTTP/1.1",
      "response_length": 20
    }),
    ('ProcessingFailed', {
      # missing required data
      # "request_id": "685f946b-99b5-4281-9ea1-c46373b50a6d",
      "ip": "210.117.121.42",
      "user": "0498a4d8-40b1-70cb-b99d-aff1d09dde75",
      "request_time": 1743740705172,
      "http_method": "GET",
      "resource_path": "/random/strings",
      "status": 200,
      "protocol": "HTTP/1.1",
      "response_length": 20
    }),
    ('ProcessingFailed', {
      "request_id": "685f946b-99b5-4281-9ea1-c46373b50a6d",
      # mismatched data type
      "ip": 212234672,
      "user": "0498a4d8-40b1-70cb-b99d-aff1d09dde75",
      "request_time": 1743740705172,
      "http_method": "GET",
      "resource_path": "/random/strings",
      "status": 200,
      "protocol": "HTTP/1.1",
      "response_length": 20
    }),
    ('ProcessingFailed', {
      # mismatched column name
      "requestId": "685f946b-99b5-4281-9ea1-c46373b50a6d",
      # mismatched data type
      "ip": "202.165.71.49",
      "user": "0498a4d8-40b1-70cb-b99d-aff1d09dde75",
      # mismatched column name
      "requestTime": 1743740705172,
      # mismatched column name
      "httpMethod": "GET",
      # mismatched column name
      "resourcePath": "/random/strings",
      "status": 200,
      "protocol": "HTTP/1.1",
      # mismatched column name
      "responseLength": 20
    })
  ]

  for correct_result, record in record_list:
    event = {
      "invocationId": "invocationIdExample",
      "deliveryStreamArn": "arn:aws:kinesis:EXAMPLE",
      "region": "us-east-1",
      "records": [
        {
          "recordId": "49546986683135544286507457936321625675700192471156785154",
          "approximateArrivalTimestamp": 1495072949453,
          "data": base64.b64encode(json.dumps(record).encode('utf-8'))
        }
      ]
    }

    res = lambda_handler(event, {})
    print(f"\n>> {correct_result} == {res['records'][0]['result']}?",  res['records'][0]['result'] == correct_result)
    pprint.pprint(res)
