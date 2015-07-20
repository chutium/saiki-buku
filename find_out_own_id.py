#!/usr/bin/env python3

import requests
import os

def run():
	config_file = os.getenv('KAFKA_DIR') + '/config/server.properties'
	url = 'http://169.254.169.254/latest/dynamic/instance-identity/document'
	response = requests.get(url)
	json = response.json()
	region = json['region']
	instanceId = json['instanceId']
	privateIp = json['privateIp']
	myid = privateIp.rsplit(".", 1)[1]

	with open(config_file, mode='a', encoding='utf-8') as a_file:
	    a_file.write('broker.id=' + myid)
