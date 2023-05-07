# Docker Swarm exporter (Docker Swarm)

*Docker Swarm exporter* exposes information about the Docker Swarm it is running inside of.
Needs to be deployed to a manager.

The following metrics are supported:
- docker_swarm_node

Proudly made by [NeuroForge](https://neuroforge.de/) in Bayreuth, Germany.

## Use in a Docker Swarm deployment

Deploy:

```yaml
version: "3.8"

services:
  docker-swarm-exporter:
    image: ghcr.io/neuroforgede/docker-swarm-exporter:0.1.0
    networks:
      - net
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
    deploy:
      mode: replicated
      replicas: 1
      resources:
        limits:
          memory: 256M
        reservations:
          memory: 128M
      placement:
        constraints:
          - node.role==manager
```

prometheus.yml

```yaml
# ...
scrape_configs:
  - job_name: 'docker-swarm-exporter'
    dns_sd_configs:
    - names:
      - 'tasks.docker-swarm-exporter'
      type: 'A'
      port: 9000
```

sample rules:

```yaml
# ...
  - alert: node_down
    expr: rate(docker_swarm_node_total{docker_swarm_node_status_state!='ready'}[60s]) > 0
    for: 5m
    labels:
      severity: critical
    annotations:
      description: Node {{ $labels.docker_swarm_node_description_hostname }} seems to be down.
      summary: Node {{ $labels.docker_swarm_node_description_hostname }} seems to be down.

  - alert: manager_not_reachable
    expr: rate(docker_swarm_node_total{docker_swarm_node_spec_role='manager', docker_swarm_node_managerstatus_reachability!="reachable"}[60s]) > 0
    for: 5m
    labels:
      severity: critical
    annotations:
      description: Manager {{ $labels.docker_swarm_node_description_hostname }} is not reachable.
      summary: Manager {{ $labels.docker_swarm_node_description_hostname }} is not reachable.
```

A monitoring solution based on the original swarmprom that includes this can be found at our [Swarmsible Stacks repo](https://github.com/neuroforgede/swarmsible-stacks)
