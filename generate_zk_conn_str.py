#!/usr/bin/env python3

import boto3
import requests


def run(stack_name):
    url = 'http://169.254.169.254/latest/dynamic/instance-identity/document'
    private_ips = []

    try:
        response = requests.get(url)
        json = response.json()
        region = json['region']

        elb = boto3.client('elb', region_name=region)
        ec2 = boto3.client('ec2', region_name=region)

        response = elb.describe_instance_health(LoadBalancerName=stack_name)

        for instance in response['InstanceStates']:
            if instance['State'] == 'InService':
                private_ips.append(ec2.describe_instances(
                    InstanceIds=[instance['InstanceId']])['Reservations'][0]['Instances'][0]['PrivateIpAddress'])

    except requests.exceptions.ConnectionError:
        private_ips = [stack_name]

    zk_conn_str = ''
    for ip in private_ips:
        zk_conn_str += ip + ':2181,'

    return zk_conn_str[:-1]
