#!/usr/bin/env python3

import subprocess
import os
import rebalance_partitions
import logging
import find_out_own_id
from multiprocessing import Pool
import wait_for_kafka_startup

kafka_dir = os.getenv('KAFKA_DIR')

logging.basicConfig(level=getattr(logging, 'INFO', None))

f = open(kafka_dir + '/config/server.properties', 'a')
f.write('\n')
f.write('zookeeper.connect=' + os.getenv('ZOOKEEPER_CONN_STRING'))
f.write('\n')
f.close()

broker_id = find_out_own_id.run()


def check_broker_id_in_zk(broker_id, process):
    import requests
    from time import sleep
    if os.getenv('WAIT_FOR_KAFKA') != 'no':
        ip = requests.get('http://169.254.169.254/latest/dynamic/instance-identity/document').json()['privateIp']
        wait_for_kafka_startup.run(ip)
    else:
        sleep(10)
    while True:
        from kazoo.client import KazooClient
        zk = KazooClient(hosts=os.getenv('ZOOKEEPER_CONN_STRING'))
        zk.start()
        try:
            zk.get("/brokers/ids/" + broker_id)
            logging.info("I'm still in ZK registered, all good!")
            sleep(10)
            zk.stop()
        except:
            logging.warning("I'm not in ZK registered, shutting down!")
            zk.stop()
            process.kill()
            exit(1)

pool = Pool()

if os.getenv('REASSIGN_PARTITIONS') == 'yes':
    logging.info("starting reassignment script")
    pool.apply_async(rebalance_partitions.run)

logging.info("starting kafka server ...")
kafka_process = subprocess.Popen([kafka_dir + "/bin/kafka-server-start.sh", kafka_dir + "/config/server.properties"])

pool.apply_async(check_broker_id_in_zk, [broker_id, kafka_process])

if os.getenv('REASSIGN_PARTITIONS') == 'yes':
    pool.close()
    pool.join()

kafka_process.wait()
