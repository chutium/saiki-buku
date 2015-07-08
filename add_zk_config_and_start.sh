#!/bin/bash

echo "writing config with zk info"
echo "" >> /opt/kafka_${SCALA_VERSION}-${KAFKA_VERSION}/config/server.properties
echo zookeeper.connect=$ZOOKEEPER_CONN_STRING >> /opt/kafka_${SCALA_VERSION}-${KAFKA_VERSION}/config/server.properties
echo "" >> /opt/kafka_${SCALA_VERSION}-${KAFKA_VERSION}/config/server.properties
echo "writing id to config_file"
/tmp/find_out_own_id.py -f /opt/kafka_${SCALA_VERSION}-${KAFKA_VERSION}/config/server.properties

exec /opt/kafka_${SCALA_VERSION}-${KAFKA_VERSION}/bin/kafka-server-start.sh /opt/kafka_${SCALA_VERSION}-${KAFKA_VERSION}/config/server.properties
