#!/usr/bin/env python3

import subprocess
import os
import rebalance_partitions
from subprocess import Popen
import logging
import find_out_own_id
from multiprocessing import Pool

kafka_dir = os.getenv('KAFKA_DIR')

logging.basicConfig(level=getattr(logging, 'INFO', None))

f = open(kafka_dir + '/config/server.properties', 'a')
f.write('\n')
f.write('zookeeper.connect=' + os.getenv('ZOOKEEPER_CONN_STRING'))
f.write('\n')
f.close()

find_out_own_id.run()

if os.getenv('REASSIGN_PARTITIONS') == 'yes':
    pool = Pool()
    logging.info("starting reassignment script")
    pool.apply_async(rebalance_partitions.run)

logging.info("starting kafka server ...")
subprocess.call([kafka_dir + "/bin/kafka-server-start.sh", kafka_dir + "/config/server.properties"])

if os.getenv('REASSIGN_PARTITIONS') == 'yes':
    pool.close()
    pool.join()
