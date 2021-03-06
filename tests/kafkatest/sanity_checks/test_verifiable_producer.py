# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from ducktape.mark import parametrize
from ducktape.mark.resource import cluster
from ducktape.tests.test import Test
from ducktape.utils.util import wait_until

from kafkatest.services.kafka import KafkaService
from kafkatest.services.verifiable_producer import VerifiableProducer
from kafkatest.services.zookeeper import ZookeeperService
from kafkatest.utils import is_version
from kafkatest.version import LATEST_0_8_2, LATEST_0_9, TRUNK, KafkaVersion


class TestVerifiableProducer(Test):
    """Sanity checks on verifiable producer service class."""
    def __init__(self, test_context):
        super(TestVerifiableProducer, self).__init__(test_context)

        self.topic = "topic"
        self.zk = ZookeeperService(test_context, num_nodes=1)
        self.kafka = KafkaService(test_context, num_nodes=1, zk=self.zk,
                                  topics={self.topic: {"partitions": 1, "replication-factor": 1}})

        self.num_messages = 1000
        # This will produce to source kafka cluster
        self.producer = VerifiableProducer(test_context, num_nodes=1, kafka=self.kafka, topic=self.topic,
                                           max_messages=self.num_messages, throughput=1000)

    def setUp(self):
        self.zk.start()
        self.kafka.start()

    @cluster(num_nodes=3)
    @parametrize(producer_version=str(LATEST_0_8_2))
    @parametrize(producer_version=str(LATEST_0_9))
    @parametrize(producer_version=str(TRUNK))
    def test_simple_run(self, producer_version=TRUNK):
        """
        Test that we can start VerifiableProducer on trunk or against the 0.8.2 jar, and
        verify that we can produce a small number of messages.
        """
        node = self.producer.nodes[0]
        node.version = KafkaVersion(producer_version)
        self.producer.start()
        wait_until(lambda: self.producer.num_acked > 5, timeout_sec=5,
             err_msg="Producer failed to start in a reasonable amount of time.")

        # using version.vstring (distutils.version.LooseVersion) is a tricky way of ensuring
        # that this check works with TRUNK
        # When running VerifiableProducer 0.8.X, both trunk version and 0.8.X should show up because of the way
        # verifiable producer pulls in some trunk directories into its classpath
        if node.version <= LATEST_0_8_2:
            assert is_version(node, [node.version.vstring, TRUNK.vstring])
        else:
            assert is_version(node, [node.version.vstring])

        self.producer.wait()
        num_produced = self.producer.num_acked
        assert num_produced == self.num_messages, "num_produced: %d, num_messages: %d" % (num_produced, self.num_messages)


