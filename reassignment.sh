#!/bin/bash
sleep 60
cd /tmp
unset JMX_PORT

brokers=$(echo "ls /brokers/ids" | /opt/kafka_${SCALA_VERSION}-${KAFKA_VERSION}/bin/zookeeper-shell.sh $ZOOKEEPER_CONN_STRING | tail -n1)
brokers=${brokers:1}
brokers=${brokers::-1}
brokers=$(echo $brokers | tr -d '[[:space:]]')

rm -rf topics
mkdir topics
cd topics
for t in $(/opt/kafka_${SCALA_VERSION}-${KAFKA_VERSION}/bin/kafka-topics.sh --zookeeper $ZOOKEEPER_CONN_STRING --list | grep -v "marked for deletion")
do
  echo "{\"topics\":[" > $t.json
  echo "{\"topic\": \""$t"\"}" >> $t.json
  echo "],\"version\":1}" >> $t.json
  /opt/kafka_${SCALA_VERSION}-${KAFKA_VERSION}/bin/kafka-reassign-partitions.sh --topics-to-move-json-file $t.json --broker-list $brokers --zookeeper $ZOOKEEPER_CONN_STRING --generate | tail -n1 > $t_reassignment.json
  /opt/kafka_${SCALA_VERSION}-${KAFKA_VERSION}/bin/kafka-reassign-partitions.sh --zookeeper $ZOOKEEPER_CONN_STRING --reassignment-json-file $t_reassignment.json --execute
  sleep 10
done
