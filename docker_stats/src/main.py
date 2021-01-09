import json
import os
import time

import docker
from graphitesend import GraphiteClient


def flatten_json(y):
    out = {}

    def flatten(x, name=''):
        if type(x) is dict:
            for a in x:
                flatten(x[a], name + a + '.')
        elif type(x) is list:
            i = 0
            for a in x:
                flatten(a, name + str(i) + '.')
                i += 1
        else:
            out[name[:-1]] = x

    flatten(y)
    return out


def json_to_list(json_stat, container_name):
    rs = []
    for stat in json_stat:
        value = json_stat[stat]
        state_name = f"{container_name}.{stat}"
        if isinstance(value, (int, float)):
            rs.append((state_name, value))
    return rs


def main():
    try:
        GRAPHITE_SERVER = os.environ["GRAPHITE_SERVER"]
    except:
        GRAPHITE_SERVER = "127.0.0.1"

    try:
        GRAPHITE_PORT = os.environ["GRAPHITE_PORT"]
    except:
        GRAPHITE_PORT = 2003
    
    try:
        SLEEP = os.environ["SLEEP"]
    except:
        SLEEP = 60

    client = docker.from_env()
    graph_client = GraphiteClient(graphite_server=GRAPHITE_SERVER, graphite_port=GRAPHITE_PORT, prefix="docker.stats")

    while True:
        for container in client.containers.list():
            print(container.name)
            json_state = flatten_json(json.loads(next(container.stats()).decode("utf-8")))
            metrics = json_to_list(json_state, container.name)
            graph_client.send_list(metrics)
        time.sleep(SLEEP)


if __name__ == "__main__":
    main()
