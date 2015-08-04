FROM zalando/python:3.4.0-1
MAINTAINER fabian.wollert@zalando.de teng.qiu@zalando.de

ENV KAFKA_VERSION="0.8.2.1" SCALA_VERSION="2.10"
ENV KAFKA_DIR="/opt/kafka_${SCALA_VERSION}-${KAFKA_VERSION}"

RUN apt-get update
RUN apt-get install wget openjdk-7-jre -y --force-yes
RUN pip3 install --upgrade kazoo

ADD download_kafka.sh /tmp/download_kafka.sh
RUN chmod 777 /tmp/download_kafka.sh

RUN /tmp/download_kafka.sh
RUN tar xf /tmp/kafka_${SCALA_VERSION}-${KAFKA_VERSION}.tgz -C /opt

ADD server.properties $KAFKA_DIR/config/server.properties

RUN mkdir -p /data/kafka-logs
RUN chmod -R 777 /data/kafka-logs

ADD find_out_own_id.py /tmp/find_out_own_id.py
#RUN python3 /tmp/find_out_own_id.py -f $KAFKA_DIR/config/server.properties

RUN chmod -R 777 $KAFKA_DIR
WORKDIR $KAFKA_DIR

ADD start_kafka_and_reassign_partitions.py /tmp/start_kafka_and_reassign_partitions.py
ADD rebalance_partitions.py /tmp/rebalance_partitions.py
ADD wait_for_kafka_startup.py /tmp/wait_for_kafka_startup.py
RUN chmod 777 /tmp/start_kafka_and_reassign_partitions.py
CMD /tmp/start_kafka_and_reassign_partitions.py

EXPOSE 9092 8004
