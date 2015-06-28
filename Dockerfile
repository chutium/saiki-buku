FROM zalando/ubuntu:14.04.1-1
MAINTAINER fabian.wollert@zalando.de teng.qiu@zalando.de

ENV KAFKA_VERSION="0.8.2.1" SCALA_VERSION="2.10"

RUN apt-get update
RUN apt-get install python3 python3-pip wget openjdk-7-jre -y --force-yes
RUN easy_install-3.4 pip
RUN pip3 install boto3

ADD download_kafka.sh /tmp/download_kafka.sh
RUN chmod 777 /tmp/download_kafka.sh

RUN /tmp/download_kafka.sh
RUN tar xf /tmp/kafka_${SCALA_VERSION}-${KAFKA_VERSION}.tgz -C /opt

ADD server.properties /opt/kafka_${SCALA_VERSION}-${KAFKA_VERSION}/config/server.properties

RUN mkdir -p /data/kafka-logs
RUN chmod -R 777 /data/kafka-logs

ADD find_out_own_id.py /tmp/find_out_own_id.py
#RUN python3 /tmp/find_out_own_id.py -f /opt/kafka_${SCALA_VERSION}-${KAFKA_VERSION}/config/server.properties

RUN chmod -R 777 /opt/kafka_${SCALA_VERSION}-${KAFKA_VERSION}/
WORKDIR /opt/kafka_${SCALA_VERSION}-${KAFKA_VERSION}/

ADD add_zk_config_and_start.sh /tmp/add_zk_config_and_start.sh
RUN chmod 777 /tmp/add_zk_config_and_start.sh
CMD /tmp/add_zk_config_and_start.sh

EXPOSE 9092 8004
