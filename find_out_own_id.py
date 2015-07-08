#!/usr/bin/env python3

import requests
import sys
from optparse import OptionParser

parser = OptionParser()
parser.add_option("-f", "--file", type="string", dest="file", help="which config file should the host to be added on?")

(options, args) = parser.parse_args()

# mandatory options
if options.file is None:   # if filename is not given
    parser.error('file not given')
    sys.exit(2)
else:
    config_file = options.file

url = 'http://169.254.169.254/latest/dynamic/instance-identity/document'
response = requests.get(url)
json = response.json()
region = json['region']
instanceId = json['instanceId']
privateIp = json['privateIp']
myid = privateIp.rsplit(".", 1)[1]

with open(config_file, mode='a', encoding='utf-8') as a_file:
    a_file.write('broker.id=' + myid)
