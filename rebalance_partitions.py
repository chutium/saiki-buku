from kazoo.client import KazooClient, KazooState
import logging
import json
import random
import os

def state_listener(state):
    if state == KazooState.LOST:
        # Register somewhere that the session was lost
        pass
    elif state == KazooState.SUSPENDED:
        # Handle being disconnected from Zookeeper
        pass
    else:
        # Handle being connected/reconnected to Zookeeper
        pass

def readout_brokerids(zk):
    if zk.exists("/brokers/ids"):
        return zk.get_children("/brokers/ids")
    else:
        print("there are no brokers registrated in this zookeeper cluster, therefore exiting")
        exit(1)

def readout_topics(zk):
    if zk.exists("/brokers/topics"):
        return zk.get_children("/brokers/topics")
    else:
        print("there are no topics registrated in this zookeeper cluster")
        return None

def readout_topic_details(zk, topic):
    if zk.exists("/brokers/topics/" + topic):
        return json.loads(zk.get("/brokers/topics/" + topic)[0].decode('utf-8'))
    else:
        print("no information for topic " + topic + " existing")

def readout_partitions(zk, topic):
    if zk.exists("/brokers/topics/" + topic + "/partitions"):
        return zk.get_children("/brokers/topics/" + topic + "/partitions")
    else:
        print("there are no partitions for topic " + topic + " in this zookeeper cluster")
        return None

def check_partitions(zk, topic):
    if zk.exists("/brokers/topics/" + topic + "/partitions"):
        pass

def check_for_broken_partitions(zk):
    brokers = readout_brokerids(zk)
    tmp_result = {}
    result = {}
    for topic in readout_topics(zk):
        logging.debug("checking topic: " + topic)
        tmp_result[topic] = {}
        result[topic] = {}
        topic_details = readout_topic_details(zk, topic)
        for partition in topic_details['partitions']:
            logging.debug("checking partition: " + partition)
            tmp_result[topic][partition] = {}
            for part_broker_id in topic_details['partitions'][partition]:
                logging.debug("checking if this broker is still existing: " + str(part_broker_id))
                tmp_result[topic][partition][part_broker_id] = False
                for existing_broker in brokers:
                    if int(part_broker_id) == int(existing_broker):
                        tmp_result[topic][partition][part_broker_id] = True
                        break
                logging.debug(tmp_result)
            for part_broker_not_avail in tmp_result[topic][partition]:
                if tmp_result[topic][partition][part_broker_not_avail] == False:
                    result[topic][partition] = part_broker_not_avail
    return result

def get_own_ip():
    import requests
    return requests.get('http://169.254.169.254/latest/dynamic/instance-identity/document').json()['privateIp']

def wait_for_kafka_startup(ip, port = 9092):
    import socket
    from time import sleep
    # TIMEOUT NEEDED!
    while True:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex((ip, port))
        if result == 0:
            return True
        else:
            sleep(10)

def generate_json(zk, replication_factor):
    logging.info("checking for broken topics")
    broken_topics = check_for_broken_partitions(zk)
    logging.debug("broken topics:")
    logging.debug(broken_topics)

    logging.info("reading out broker id's")
    avail_brokers_init = readout_brokerids(zk)

    if len(broken_topics) > 0:
        logging.info("broken topics found, generating new assignment pattern")
        final_result = {'version': 1, 'partitions': []}
        for topic in broken_topics:
            for partition in broken_topics[topic]:
                logging.debug("finding new brokers for topic: " + str(topic) + ", partition: " + str(partition))
                avail_brokers = list(avail_brokers_init)
                broker_list = []
                for i in range(0, replication_factor):
                    broker = avail_brokers[random.randrange(0,len(avail_brokers))]
                    logging.debug("using broker: " + broker + " for topic: " + str(topic) + ", partition: " + str(partition))
                    avail_brokers.remove(broker)
                    logging.debug("available brokers for the rest: " + str(avail_brokers))
                    broker_list.append(int(broker))
                final_result['partitions'].append({'topic': topic, 'partition': int(partition), 'replicas': broker_list})
    return final_result

def write_json_to_zk(zk, final_result):
    logging.info("writing reassigned partitions in ZK")
    zk.create("/admin/reassign_partitions", json.dumps(final_result).encode('utf-8'))

def run():
    REPLICATION_FACTOR=3
    ZOOKEEPER_CONNECT_STRING=os.getenv('ZOOKEEPER_CONN_STRING')
    logging.info("waiting for kafka to start up")
    wait_for_kafka_startup(get_own_ip())

    logging.info("kafka port is open, continuing")


    zk = KazooClient(hosts=ZOOKEEPER_CONNECT_STRING)
    zk.start()
    zk.add_listener(state_listener)

    logging.info("connected to Zookeeper")

    result = generate_json(zk, REPLICATION_FACTOR)
    logging.debug(result)
    write_json_to_zk(zk, result)

    zk.stop()