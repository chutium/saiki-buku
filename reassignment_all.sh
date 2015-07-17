#!/bin/bash
sleep 60
cd /tmp
unset JMX_PORT

brokers=$(echo "ls /brokers/ids" | /opt/kafka_${SCALA_VERSION}-${KAFKA_VERSION}/bin/zookeeper-shell.sh $ZOOKEEPER_CONN_STRING | tail -n1)
brokers=${brokers:1}
brokers=${brokers::-1}
brokers=$(echo $brokers | tr -d '[[:space:]]')

echo "{\"topics\":[" > topics.json
/opt/kafka_${SCALA_VERSION}-${KAFKA_VERSION}/bin/kafka-topics.sh --zookeeper $ZOOKEEPER_CONN_STRING --list | grep -v "marked for deletion" | awk '{print "{\"topic\": \""$1"\"},"}' >> topics.json
echo "{\"topic\": \"dummy_topic\"}],\"version\":1}" >> topics.json

/opt/kafka_${SCALA_VERSION}-${KAFKA_VERSION}/bin/kafka-reassign-partitions.sh --zookeeper $ZOOKEEPER_CONN_STRING --topics-to-move-json-file topics.json --broker-list $brokers --generate | tail -n1 > reassignment_all.json
/opt/kafka_${SCALA_VERSION}-${KAFKA_VERSION}/bin/kafka-reassign-partitions.sh --zookeeper $ZOOKEEPER_CONN_STRING --reassignment-json-file reassignment_all.json --execute
