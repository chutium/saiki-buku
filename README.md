Introduction
============
Buku (javanese for book) is a Kafka Appliance for STUPS.

Buku uses port ```8004``` as ```JMX_PORT```.

Usage
=====
Create an autoscaling group in AWS, and on each instance of this autoscaling group, after building the docker image, start Buku like this:
```
sudo docker run -d -e ZOOKEEPER_STACK_NAME=local-test -e JMX_PORT=8004 -p 8004:8004 -p 9092:9092 --net=host <IMAGE_ID>
```
Docker run option ```--net=host``` is needed, so kafka can bind the interface from the host, to listen for leader elections. Ref. https://docs.docker.com/articles/networking/#how-docker-networks-a-container

Deployment with STUPS toolbox
-----------------------------

###### Create the docker and push

Push your docker image to STUPS ```Pier One```, see here: http://docs.stups.io/en/latest/user-guide/deployment.html#prepare-the-deployment-artifact

###### Register the Buku app in Yourturn/Kio

Docs: http://docs.stups.io/en/latest/components/yourturn.html

if needed, you need to adjust later in the yaml-file the Stackname or the application_id to suit the one you have put in Yourturn/Kio

###### get our YAML File with the senza definition
```
wget https://raw.githubusercontent.com/zalando/saiki-buku/master/buku.yaml
```

###### execute senza with the definition file

```
senza create buku.yaml <STACK_VERSION> <DOCKER_IMAGE_WITH_VERSION_TAG> <MINT_BUCKET> <SCALYR_LOGGING_KEY> <APPLICATION_ID> <ZOOKEEPER_STACK_NAME> <Hosted_Zone> [--region AWS_REGION]
```

A real world example would be:
```
senza create buku.yaml 1 pierone.example.org/myteam/buku:0.1-SNAPSHOT example-stups-mint-some_id-eu-west-1 some_scalyr_key buku zookeeper-stack example.org. --region eu-west-1
```

An autoscaling group will be created and Buku docker container will be running on all of the EC2 instances in this autoscaling group.

Your Kafka Producer/Consumer can connect to this Buku cluster with its Route53 DNS name: ```<STACK_NAME>.<Hosted_Zone>```, such as: ```buku.example.org```. This is a CNAME record with value of Buku's AppLoadBalancer (ELB), this LoadBalancer is an internal LoadBalancer, so that means, in order to access this Buku cluster, your Producer or Consumer also need to be deployed in the same region's VPC in AWS.

Check the STUPS documention for additional options:
http://docs.stups.io
