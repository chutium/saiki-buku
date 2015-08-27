#!/usr/bin/env python3

import subprocess
import os
import rebalance_partitions
import logging
import find_out_own_id
from multiprocessing import Pool
import wait_for_kafka_startup
import generate_zk_conn_str

kafka_dir = os.getenv('KAFKA_DIR')

logging.basicConfig(level=getattr(logging, 'INFO', None))

zk_conn_str = generate_zk_conn_str.run(os.getenv('ZOOKEEPER_STACK_NAME'))
os.environ['ZOOKEEPER_CONN_STRING'] = zk_conn_str

logging.info("Got ZooKeeper connection string: " + zk_conn_str)


def create_broker_properties(zk_conn_str):
    with open(kafka_dir + '/config/server.properties', "r+") as f:
        lines = f.read().splitlines()
        f.seek(0)
        f.truncate()
        f.write('zookeeper.connect=' + zk_conn_str + '\n')
        for line in lines:
            if not line.startswith("zookeeper.connect"):
                f.write(line + '\n')
        f.close()

    logging.info("Broker properties generated with zk connection str: " + zk_conn_str)

create_broker_properties(zk_conn_str)
broker_id = find_out_own_id.run()


def check_broker_id_in_zk(broker_id, process):
    import requests
    from time import sleep
    from kazoo.client import KazooClient
    zk_conn_str = os.getenv('ZOOKEEPER_CONN_STRING')
    while True:
        if os.getenv('WAIT_FOR_KAFKA') != 'no':
            ip = requests.get('http://169.254.169.254/latest/dynamic/instance-identity/document').json()['privateIp']
            wait_for_kafka_startup.run(ip)
            os.environ['WAIT_FOR_KAFKA'] = 'no'

        new_zk_conn_str = generate_zk_conn_str.run(os.getenv('ZOOKEEPER_STACK_NAME'))
        if zk_conn_str != new_zk_conn_str:
            logging.warning("ZooKeeper connection string changed!")
            zk_conn_str = new_zk_conn_str
            os.environ['ZOOKEEPER_CONN_STRING'] = zk_conn_str
            create_broker_properties(zk_conn_str)
            from random import randint
            sleep(randint(1, 20))
            process.kill()
            logging.info("Restarting kafka broker with new ZooKeeper connection string ...")
            process = subprocess.Popen([kafka_dir
                                        + "/bin/kafka-server-start.sh", kafka_dir
                                        + "/config/server.properties"])
            os.environ['WAIT_FOR_KAFKA'] = 'yes'
            continue

        zk = KazooClient(hosts=zk_conn_str)
        zk.start()
        try:
            zk.get("/brokers/ids/" + broker_id)
            logging.info("I'm still in ZK registered, all good!")
            sleep(60)
            zk.stop()
        except:
            logging.warning("I'm not in ZK registered, killing kafka broker process!")
            zk.stop()
            process.kill()
            logging.info("Restarting kafka broker ...")
            process = subprocess.Popen([kafka_dir
                                        + "/bin/kafka-server-start.sh", kafka_dir
                                        + "/config/server.properties"])
            os.environ['WAIT_FOR_KAFKA'] = 'yes'

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
