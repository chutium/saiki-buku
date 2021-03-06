from kazoo.client import KazooClient, KazooState, NodeExistsError, NoNodeError
from time import sleep
import logging
import json
import os
import wait_for_kafka_startup


class NotEnoughBrokersException(Exception):
    def __init__(self):
        logging.warning("NotEnoughBrokersException")
        import sys
        sys.stdout.flush()


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


def check_for_broken_partitions(zk_dict):
    brokers = zk_dict['broker']
    tmp_result = {}
    result = {}
    for topic in zk_dict['topics']:
        logging.debug("checking topic: " + topic['name'])
        tmp_result[topic['name']] = {}
        for partition in topic['partitions']:
            logging.debug("checking partition: " + str(partition))
            tmp_result[topic['name']][partition] = {}
            for part_broker_id in topic['partitions'][partition]:
                logging.debug("checking if this broker is still existing: " + str(part_broker_id))
                tmp_result[topic['name']][partition][part_broker_id] = False
                for existing_broker in brokers:
                    if int(part_broker_id) == int(existing_broker):
                        tmp_result[topic['name']][partition][part_broker_id] = True
                        break
            for part_broker_not_avail in tmp_result[topic['name']][partition]:
                if tmp_result[topic['name']][partition][part_broker_not_avail] is False:
                    if topic['name'] not in result:
                        result[topic['name']] = {}
                    result[topic['name']][partition] = part_broker_not_avail
    return result


def get_own_ip():
    import requests
    return requests.get('http://169.254.169.254/latest/dynamic/instance-identity/document').json()['privateIp']


def generate_json(zk_dict, replication_factor, broken_topics=False):
    ignore_existing = False
    if broken_topics is True:
        logging.info("checking for broken topics")
        topics_to_reassign = check_for_broken_partitions(zk_dict)
    else:
        logging.info("reassigning all topics")
        topics_to_reassign = {}
        for topic in zk_dict['topics']:
            for partition in topic['partitions']:
                if 'name' not in topics_to_reassign[topic]:
                    topics_to_reassign[topic['name']] = {}
                topics_to_reassign[topic['name']][partition] = 0
        ignore_existing = True
    logging.debug("topics_to_reassign:")
    logging.debug(topics_to_reassign)

    if len(topics_to_reassign) > 0:
        logging.debug(topics_to_reassign)
        logging.info("topics_to_reassign found, generating new assignment pattern")
        logging.info("reading out broker id's")
        avail_brokers_init = zk_dict['broker']

        if len(avail_brokers_init) < replication_factor:
            raise NotEnoughBrokersException

        logging.debug("Available Brokers: " + str(len(avail_brokers_init)))
        logging.debug("Replication Factor: " + str(replication_factor))
        final_result = {'version': 1, 'partitions': []}
        logging.info("generating now ")
        for topic in topics_to_reassign:
            for partition in topics_to_reassign[topic]:
                logging.debug("finding new brokers for topic: " + str(topic) + ", partition: " + str(partition))
                avail_brokers = list(avail_brokers_init)
                broker_list = []
                for i in range(0, replication_factor):
                    broker = get_best_broker(zk_dict, list(avail_brokers), final_result, ignore_existing)
                    logging.debug("using broker: "
                                  + broker
                                  + " for topic: "
                                  + str(topic)
                                  + ", partition: "
                                  + str(partition))
                    avail_brokers.remove(broker)
                    logging.debug("available brokers for the rest: " + str(avail_brokers))
                    broker_list.append(int(broker))
                final_result['partitions'].append({'topic': topic,
                                                   'partition': int(partition),
                                                   'replicas': broker_list})
        return final_result
    else:
        logging.info("no broken topics found")
        return {}


def get_broker_weight(zk_dict, new_assignment, broker, ignore_existing=False):
    broker_weight = 0
    if ignore_existing is False:
        for topic in zk_dict['topics']:
            for partition in topic['partitions']:
                i = len(topic['partitions'][partition])
                # every topic gets a weight, based on the position in the array.
                # first topic is the leader, so its gets the heighest weight
                for part_broker_id in topic['partitions'][partition]:
                    if int(part_broker_id) == int(broker):
                        broker_weight = broker_weight + 2 ** i
                    i = i - 1
    # also incorporate the new assignments, which are not yet written in zookeeper
    for partition_na in new_assignment['partitions']:
        i = len(partition_na['replicas'])
        for brokers_na in partition_na['replicas']:
            # logging.debug(brokers_na)
            # logging.debug(broker)
            if int(brokers_na) == int(broker):
                broker_weight = broker_weight + 2 ** i
                # logging.debug(broker_weight)
            i = i - 1
    return broker_weight


def get_best_broker(zk_dict, available_brokers, new_assignment, ignore_existing=False):
    # logging.debug("new assignment: " + str(new_assignment))
    if len(available_brokers) == 1:
        logging.debug("only one broker available: " + str(available_brokers))
        return available_brokers[0]
    else:
        lowest_broker = {'id': 0, 'weight': 0}
        logging.debug("this brokers are available for this vote: " + str(available_brokers))
        for broker in available_brokers:
            logging.debug("getting weight for broker " + str(broker))
            weight = get_broker_weight(zk_dict, new_assignment, broker, ignore_existing)
            logging.debug("broker_weight " + str(weight))
            if lowest_broker['id'] == 0 or lowest_broker['weight'] > weight:
                lowest_broker['id'] = broker
                lowest_broker['weight'] = weight
        return lowest_broker['id']


def write_json_to_zk(zk, final_result):
    logging.info("writing reassigned partitions in ZK")
    count_steps_left = len(final_result['partitions'])
    for step in final_result['partitions']:
        if count_steps_left % 20 == 0 or count_steps_left == len(final_result['partitions']):
            logging.info("steps left: " + str(count_steps_left))
        logging.info("trying to write zk node for repairing " + str(step))
        timeout_count = 0
        done = False
        while timeout_count < 1800 and done is False:
            try:
                zk.create("/admin/reassign_partitions",
                          json.dumps({'version': 1, 'partitions': [step]}).encode('utf-8'))
                done = True
                logging.info("done")
                count_steps_left = count_steps_left - 1
                sleep(0.5)
            except NodeExistsError:
                try:
                    check = zk.get("/admin/reassign_partitions")
                    if check[0] == b'{"version": 1, "partitions": []}':
                        zk.delete("/admin/reassign_partitions", recursive=True)
                    else:
                        # only output message every 10mins
                        if timeout_count % 300 == 0:
                            logging.info("there seems to be a reassigning already taking place: "
                                         + str(check[0].decode('utf-8')))
                            logging.info("waiting ...")
                        timeout_count = timeout_count + 1
                        sleep(2)
                except NoNodeError:
                    pass
                    # logging.info("NoNodeError")
    if done is False:
        logging.warning("Reassignment was not successfull due to timeout issues of the previous reassignment")


def get_zk_dict(zk):
    result = {'topics': [], 'broker': []}
    for topic in readout_topics(zk):
        result['topics'].append({'name': topic, 'partitions': readout_topic_details(zk, topic)['partitions']})
    for broker in readout_brokerids(zk):
        result['broker'].append(broker)
    return result


def run():
    replication_factor = 3
    zookeeper_connect_string = os.getenv('ZOOKEEPER_CONN_STRING')
    logging.info("waiting for kafka to start up")
    if os.getenv('WAIT_FOR_KAFKA') != 'no':
        wait_for_kafka_startup.run(get_own_ip())
    else:
        sleep(10)

    logging.info("kafka port is open, continuing")

    zk = KazooClient(hosts=zookeeper_connect_string)
    zk.start()
    zk.add_listener(state_listener)

    logging.info("connected to Zookeeper")

    zk_dict = get_zk_dict(zk)
    result = generate_json(zk_dict, replication_factor, broken_topics=True)
    if result != {}:
        logging.info("JSON generated")
        logging.info("there are " + str(len(result['partitions'])) + " partitions to repair")
        logging.debug(result)
        if os.getenv('WRITE_TO_JSON') != 'no':
            write_json_to_zk(zk, result)
    else:
        logging.info("no JSON generated")
        needed = True
        for broker in zk_dict['broker']:
            if int(get_broker_weight(zk_dict, {'partitions': []}, broker)) == 0:
                needed = True
        if needed is True:
            result = generate_json(zk_dict, replication_factor, broken_topics=False)
            if result != {}:

                logging.info("JSON generated")
                if os.getenv('WRITE_TO_JSON') != 'no':
                    write_json_to_zk(zk, result)
        else:
            logging.info("no unused Broker found")

    zk.stop()
    logging.info("exiting")
