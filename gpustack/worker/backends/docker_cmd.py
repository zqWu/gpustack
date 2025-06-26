import json
import shlex
import subprocess
import time
from datetime import datetime

from gpustack.schemas import DockerCmd
import logging
import threading

from gpustack.client.generated_clientset import ClientSet
from gpustack.config.config import Config
from gpustack.schemas.docker_cmd import DockerCmdState

logger = logging.getLogger(__name__)
lock = threading.Lock()


class DockerBackend:
    def __init__(
        self,
        clientset: ClientSet,
        dc: DockerCmd,
        cfg: Config,
    ):
        self._clientset = clientset
        self._docker_cmd = dc
        self._cfg = cfg
        self._container_name = f"gpustack_job_{generate_date_string()}_{short_uuid()}"

    def start(self):
        ex = start_docker(self._docker_cmd, self._container_name)
        if not ex:
            self._docker_cmd.state = DockerCmdState.RUNNING
            self._clientset.docker_cmds.update(self._docker_cmd.id, self._docker_cmd)
        return ex, self._container_name

    def is_alive(self):
        # 负责监控
        raise NotImplementedError


def generate_date_string():
    now = datetime.now()
    date_string = now.strftime("%Y%m%d-%H%M%S")
    return date_string


def short_uuid(length: int = 4):
    import uuid

    return str(uuid.uuid4())[:length]


def start_docker(dc: DockerCmd, container_name: str):
    # 实现 docker run -d --name gpustack_foo alpine:latest tail -f /dev/null
    # 已经确定这些参数合法, docker=/usr/bin/docker
    # 设定 Docker 命令和参数
    docker_command = "/usr/bin/docker"
    image_name = dc.image
    entrypoint = dc.entrypoint
    _entrypoint = f"--entrypoint {entrypoint}" if entrypoint else ""
    command = dc.cmd or ""
    _env = ""
    if dc.env:
        _dict = json.loads(dc.env)
        for k, v in _dict.items():
            _env = f"{_env} -e {k}={v}"

    _port_map = ""
    if dc.port_map:
        _dict = json.loads(dc.port_map)
        for k, v in _dict.items():
            _port_map = f"{_port_map} -p {k}:{v}"

    # 构建完整的命令
    cmd = f"{docker_command} run -d {_env} {_port_map} --name {container_name} {_entrypoint} {image_name} {command}"
    print(f"{cmd}")
    try:
        # 使用 subprocess 执行命令
        result = subprocess.run(
            shlex.split(cmd), check=True, capture_output=True, text=True
        )
        print(f"Container started successfully: {result.stdout.strip()}")
    except subprocess.CalledProcessError as e:
        print(f"Error starting container: {e.stderr.strip()}")
        return e


def _test():
    dc: DockerCmd = DockerCmd(image="alpine:latest", cmd="tail -f /dev/null")
    start_docker(dc, container_name="run_by_gpustack_001")
    while True:
        time.sleep(1000)


if __name__ == "__main__":
    _test()
