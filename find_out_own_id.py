#!/usr/bin/env python3

from kazoo.client import KazooClient, KazooState, NodeExistsError
import requests
import os

def get_broker_unique_id(broker_id):
    ZOOKEEPER_CONNECT_STRING=os.getenv('ZOOKEEPER_CONN_STRING')
    zk = KazooClient(hosts=ZOOKEEPER_CONNECT_STRING, read_only=True)
    zk.start()
    ids = zk.get_children('/brokers/ids')
    while broker_id in ids:
        broker_id = str(int(broker_id) + 1)
    zk.stop()
    return broker_id

def run():
	config_file = os.getenv('KAFKA_DIR') + '/config/server.properties'
	url = 'http://169.254.169.254/latest/dynamic/instance-identity/document'
	response = requests.get(url)
	json = response.json()
	region = json['region']
	instanceId = json['instanceId']
	privateIp = json['privateIp']
	myid = privateIp.rsplit(".", 1)[1]
        broker_unique_id = get_broker_unique_id(myid)

	with open(config_file, mode='a', encoding='utf-8') as a_file:
	    a_file.write('broker.id=' + broker_unique_id)
