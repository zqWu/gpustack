import json
import requests


def test_1():
    _json = {
        "image": "alpine:latest",
        "port_map": json.dumps({"9901": "9902"}),
        "entrypoint": None,
        "cmd": "tail -f /dev/null",
    }
    _url = "http://localhost:9055/v1/docker-cmds"
    response = requests.post(_url, json=_json)
    print(response.text)


def test_2():
    _json = {
        "image": "quay.io/jupyter/scipy-notebook:2024-05-27",
        "port_map": json.dumps({"10002": "8888"}),
        "env": json.dumps(
            {
                "JUPYTER_TOKEN": "abcd123499",
                "FOO": "bar",  # 仅测试
            }
        ),
    }
    _url = "http://localhost:9055/v1/docker-cmds"
    response = requests.post(_url, json=_json)
    print(response.text)
