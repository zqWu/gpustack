from enum import Enum
from typing import Optional
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column
from sqlmodel import Field, SQLModel, Text

from gpustack.mixins import TimestampsMixin
from gpustack.mixins.active_record import ActiveRecordMixin
from gpustack.schemas.common import PaginatedList

Base = declarative_base()


class DockerCmdState(str, Enum):
    # INITIALIZING = "initializing"
    PENDING = "pending"
    # STARTING = "starting"
    RUNNING = "running"
    SCHEDULED = "scheduled"
    # ERROR = "error"
    # DOWNLOADING = "downloading"
    # ANALYZING = "analyzing"
    # UNREACHABLE = "unreachable"


class DockerCmdBase(SQLModel, ActiveRecordMixin):
    id: Optional[int] = Field(default=None, primary_key=True)
    image: str
    port_map: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    entrypoint: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    cmd: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    env: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    # replicas: int = Field(default=1, ge=0)
    # ready_replicas: int = Field(default=0, ge=0)


class DockerCmd(DockerCmdBase, TimestampsMixin, table=True):
    __tablename__ = 'docker_cmds'
    worker_id: Optional[int] = Field(default=None)
    state: DockerCmdState = Field(default=DockerCmdState.PENDING)


class DockerCmdCreate(DockerCmdBase):
    pass


class DockerCmdUpdate(DockerCmd):
    pass


class DockerCmdPublic(DockerCmd):
    pass


DockerCmdsPublic = PaginatedList[DockerCmdPublic]
