#!/usr/bin/env python3

import requests
import os

def run():
	config_file = os.getenv('KAFKA_DIR') + '/config/server.properties'
	url = 'http://169.254.169.254/latest/dynamic/instance-identity/document'
	try:
		response = requests.get(url)
		json = response.json()
		myid = json['privateIp'].rsplit(".", 1)[1]	
	except requests.exceptions.ConnectionError:
	    myid="1"

	with open(config_file, mode='a', encoding='utf-8') as a_file:
	    a_file.write('broker.id=' + myid)

	return myid
