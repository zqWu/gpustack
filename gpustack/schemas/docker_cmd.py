from datetime import datetime
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
    PENDING = "pending"
    STARTING = "starting"
    RUNNING = "running"
    SCHEDULED = "scheduled"
    ERROR = "error"


class DockerCmdBase(SQLModel):
    image: str
    port_map: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    entrypoint: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    cmd: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    env: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))


class DockerCmd(DockerCmdBase, ActiveRecordMixin, TimestampsMixin, table=True):
    __tablename__ = 'docker_cmds'
    id: Optional[int] = Field(default=None, primary_key=True)
    worker_id: Optional[int] = Field(default=None)
    state: DockerCmdState = Field(default=DockerCmdState.PENDING)


class DockerCmdCreate(DockerCmdBase):
    pass


class DockerCmdUpdate(DockerCmdBase):
    state: Optional[DockerCmdState]
    worker_id: Optional[int]


class DockerCmdPublic(DockerCmdBase):
    id: int
    state: DockerCmdState
    worker_id: Optional[int]
    created_at: datetime
    created_at: datetime


DockerCmdsPublic = PaginatedList[DockerCmdPublic]
