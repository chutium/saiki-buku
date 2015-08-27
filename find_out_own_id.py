#!/usr/bin/env python3

from kazoo.client import KazooClient, NoNodeError
import requests
import os


def get_broker_unique_id(broker_id):
    zookeeper_connect_string = os.getenv('ZOOKEEPER_CONN_STRING')
    zk = KazooClient(hosts=zookeeper_connect_string, read_only=True)
    zk.start()
    try:
        ids = zk.get_children('/brokers/ids')
    except NoNodeError:
        return broker_id
    while broker_id in ids:
        broker_id = str(int(broker_id) + 1)
    zk.stop()
    return broker_id


def run():
    config_file = os.getenv('KAFKA_DIR') + '/config/server.properties'
    url = 'http://169.254.169.254/latest/dynamic/instance-identity/document'
    try:
        response = requests.get(url)
        json = response.json()
        myid = json['privateIp'].rsplit(".", 1)[1]
    except requests.exceptions.ConnectionError:
        myid = "1"

    broker_unique_id = get_broker_unique_id(myid)
    with open(config_file, mode='a', encoding='utf-8') as a_file:
        a_file.write('broker.id=' + broker_unique_id + '\n')

    return broker_unique_id
