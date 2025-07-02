import traceback

from fastapi import APIRouter
from starlette.responses import StreamingResponse

from gpustack.api.exceptions import InternalServerErrorException, NotFoundException
from gpustack.schemas.docker_cmd import (
    DockerCmd,
    DockerCmdCreate,
    DockerCmdsPublic,
    DockerCmdPublic,
    DockerCmdUpdate,
    DockerCmdState,
)
from gpustack.server.deps import SessionDep, ListParamsDep
from gpustack.server.services import DockerCmdService

router = APIRouter()


@router.post("", response_model=DockerCmdPublic)
async def create_docker_cmd(session: SessionDep, docker_cmd_in: DockerCmdCreate):
    try:
        docker_cmd = await DockerCmd.create(session, docker_cmd_in)
        return docker_cmd
    except Exception as e:
        traceback.print_exc()
        raise InternalServerErrorException(message=f"Failed to create DockerCmd: {e}")


@router.get("", response_model=DockerCmdsPublic)
async def get_workers(
    session: SessionDep,
    params: ListParamsDep,
    name: str = None,
    search: str = None,
    uuid: str = None,
):
    fuzzy_fields = {}
    if search:
        fuzzy_fields = {"name": search}

    fields = {}
    if name:
        fields = {"name": name}
    if uuid:
        fields["worker_uuid"] = uuid

    if params.watch:
        return StreamingResponse(
            DockerCmd.streaming(session, fields=fields, fuzzy_fields=fuzzy_fields),
            media_type="text/event-stream",
        )

    return await DockerCmd.paginated_by_query(
        session=session,
        fields=fields,
        fuzzy_fields=fuzzy_fields,
        page=params.page,
        per_page=params.perPage,
    )


@router.put("/{id}", response_model=DockerCmdPublic)
async def update_docker_cmd(
    session: SessionDep, id: int, docker_cmd_in: DockerCmdUpdate
):
    docker_cmd = await DockerCmd.one_by_id(session, id)
    if not docker_cmd:
        raise NotFoundException(message="docker_cmd not found")

    try:
        if isinstance(docker_cmd_in.state, str):  # 不知道为什么反序列化enum会失败
            docker_cmd_in.state = DockerCmdState(docker_cmd_in.state)
        await DockerCmdService(session).update(docker_cmd, docker_cmd_in)
    except Exception as e:
        raise InternalServerErrorException(message=f"Failed to update docker_cmd: {e}")

    return docker_cmd
