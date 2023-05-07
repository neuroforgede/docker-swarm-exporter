#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2023 NeuroForge GmbH & Co. KG <https://neuroforge.de>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from datetime import datetime, timedelta
import docker
from prometheus_client import start_http_server, Counter
import os
import platform
from typing import Any, Optional
import traceback
from threading import Event
import signal

exit_event = Event()

shutdown: bool = False
def handle_shutdown(signal: Any, frame: Any) -> None:
    print_timed(f"received signal {signal}. shutting down...")
    exit_event.set()

signal.signal(signal.SIGINT, handle_shutdown)
signal.signal(signal.SIGTERM, handle_shutdown)


APP_NAME = "Docker engine networks prometheus exporter"

PROMETHEUS_EXPORT_PORT = int(os.getenv('PROMETHEUS_EXPORT_PORT', '9000'))
DOCKER_HOSTNAME = os.getenv('DOCKER_HOSTNAME', platform.node())
SCRAPE_INTERVAL = int(os.getenv('SCRAPE_INTERVAL', '10'))
MAX_RETRIES_IN_ROW = int(os.getenv('MAX_RETRIES_IN_ROW', '10'))

DOCKER_SWARM_NODE = Counter(
    'docker_swarm_node',
    'Total used IPs in network on Host by containers',
    [
        'docker_swarm_node_hostname',
        'docker_swarm_node_platform_architecture',
        'docker_swarm_node_platform_os',
        'docker_swarm_node_engine_engineversion',
        'docker_swarm_node_status_state',
        'docker_swarm_node_status_addr',
        'docker_swarm_node_managerstatus_leader',
        'docker_swarm_node_managerstatus_reachability',
        'docker_swarm_node_managerstatus_addr',
    ]
)

def print_timed(msg):
    to_print = '{} [{}]: {}'.format(
        datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'docker_events',
        msg)
    print(to_print)


def watch_networks():
    client = docker.DockerClient()

    try:
        while not exit_event.is_set():
            nodes = client.nodes.list()
            for node in nodes:

                attrs = node.attrs
                DOCKER_SWARM_NODE.labels(
                    **{
                        'docker_swarm_node_hostname': attrs['Description']['Hostname'],
                        'docker_swarm_node_platform_architecture': attrs['Description']['Platform']['Architecture'],
                        'docker_swarm_node_platform_os': attrs['Description']['Platform']['OS'],
                        'docker_swarm_node_engine_engineversion': attrs['Description']['Engine']['EngineVersion'],
                        'docker_swarm_node_status_state': attrs['Status']['State'],
                        'docker_swarm_node_status_addr': attrs['Status']['Addr'],
                        'docker_swarm_node_managerstatus_leader': attrs['ManagerStatus']['Leader'],
                        'docker_swarm_node_managerstatus_reachability': attrs['ManagerStatus']['Reachability'],
                        'docker_swarm_node_managerstatus_addr': attrs['ManagerStatus']['Addr'],
                    }).inc()


            exit_event.wait(SCRAPE_INTERVAL)
    finally:
        client.close()


if __name__ == '__main__':
    print_timed(f'Start prometheus client on port {PROMETHEUS_EXPORT_PORT}')
    start_http_server(PROMETHEUS_EXPORT_PORT, addr='0.0.0.0')
    
    failure_count = 0
    last_failure: Optional[datetime]
    while not exit_event.is_set():
        try:
            print_timed('Watch networks')
            watch_networks()
        except docker.errors.APIError:
            now = datetime.now()

            traceback.print_exc()

            last_failure = last_failure
            if last_failure < (now - timedelta.seconds(SCRAPE_INTERVAL * 10)):
                print_timed("detected docker APIError, but last error was a bit back, resetting failure count.")
                # last failure was a while back, reset
                failure_count = 0

            failure_count += 1
            if failure_count > MAX_RETRIES_IN_ROW:
                print_timed(f"failed {failure_count} in a row. exit_eventing...")
                exit(1)

            last_failure = now
            print_timed(f"waiting {SCRAPE_INTERVAL} until next cycle")
            exit_event.wait(SCRAPE_INTERVAL)
