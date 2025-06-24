import asyncio
from datetime import datetime, timedelta, timezone
import importlib
import json
import logging
import math
from typing import Any, AsyncGenerator, Callable, List, Optional, Union, overload, Tuple

from fastapi.encoders import jsonable_encoder
from sqlalchemy import func
from sqlmodel import SQLModel, and_, asc, col, desc, or_, select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm.exc import FlushError
from sqlalchemy.ext.asyncio import AsyncEngine
from gpustack.schemas.common import PaginatedList, Pagination
from gpustack.server.bus import Event, EventType, event_bus


logger = logging.getLogger(__name__)


class ActiveRecordMixin:
    """ActiveRecordMixin provides a set of methods to interact with the database."""

    __config__ = None

    @property
    def primary_key(self):
        """Return the primary key of the object."""

        return self.__mapper__.primary_key_from_instance(self)

    @classmethod
    async def first(cls, session: AsyncSession):
        """Return the first object of the model."""

        statement = select(cls)
        result = await session.exec(statement)
        return result.first()

    @classmethod
    async def one_by_id(cls, session: AsyncSession, id: int):
        """Return the object with the given id. Return None if not found."""

        return await session.get(cls, id)

    @classmethod
    async def first_by_field(cls, session: AsyncSession, field: str, value: Any):
        """Return the first object with the given field and value. Return None if not found."""

        return await cls.first_by_fields(session, {field: value})

    @classmethod
    async def one_by_field(cls, session: AsyncSession, field: str, value: Any):
        """Return the object with the given field and value. Return None if not found."""

        return await cls.one_by_fields(session, {field: value})

    @classmethod
    async def first_by_fields(cls, session: AsyncSession, fields: dict):
        """
        Return the first object with the given fields and values.
        Return None if not found.
        """

        statement = select(cls)
        for key, value in fields.items():
            statement = statement.where(getattr(cls, key) == value)

        result = await session.exec(statement)
        return result.first()

    @classmethod
    async def one_by_fields(cls, session: AsyncSession, fields: dict):
        """Return the object with the given fields and values. Return None if not found."""

        statement = select(cls)
        for key, value in fields.items():
            statement = statement.where(getattr(cls, key) == value)

        result = await session.exec(statement)
        return result.first()

    @classmethod
    async def all_by_field(cls, session: AsyncSession, field: str, value: Any):
        """
        Return all objects with the given field and value.
        Return an empty list if not found.
        """
        statement = select(cls).where(getattr(cls, field) == value)
        result = await session.exec(statement)
        return result.all()

    @classmethod
    async def all_by_fields(
        cls,
        session: AsyncSession,
        fields: dict = {},
        extra_conditions: Optional[List] = None,
    ):
        """
        Return all objects with the given fields and values.
        Return an empty list if not found.
        """

        statement = select(cls)
        for key, value in fields.items():
            statement = statement.where(getattr(cls, key) == value)

        if extra_conditions:
            statement = statement.where(and_(*extra_conditions))

        result = await session.exec(statement)
        return result.all()

    @classmethod
    async def paginated_by_query(
        cls,
        session: AsyncSession,
        fields: Optional[dict] = None,
        fuzzy_fields: Optional[dict] = None,
        extra_conditions: Optional[List] = None,
        page: int = 1,
        per_page: int = 100,
        order_by: Optional[List[Tuple[str, str]]] = None,
    ) -> PaginatedList[SQLModel]:
        """
        Return a paginated and optionally sorted list of objects matching the given query criteria.

        Args:
            session (AsyncSession): The SQLAlchemy async session used to interact with the database.
            fields (Optional[dict]): Exact match filters as key-value pairs.
            fuzzy_fields (Optional[dict]): Fuzzy match filters using the SQL `LIKE` operator.
            page (int): Page number for pagination, starting from 1. Default is 1.
            per_page (int): Number of items per page. Default is 100.
            order_by (Optional[List[Tuple[str, str]]]): Sorting criteria as a list of tuples,
                each containing a field name and sort direction ("asc" or "desc").
                If not provided, defaults to `created_at DESC`.

        Returns:
            PaginatedList[SQLModel]: A paginated list of matching objects with pagination metadata.
        """

        statement = select(cls)
        if fields:
            conditions = [
                col(getattr(cls, key)) == value for key, value in fields.items()
            ]
            statement = statement.where(and_(*conditions))

        if fuzzy_fields:
            fuzzy_conditions = [
                func.lower(getattr(cls, key)).like(f"%{str(value).lower()}%")
                for key, value in fuzzy_fields.items()
            ]
            statement = statement.where(or_(*fuzzy_conditions))

        if extra_conditions:
            statement = statement.where(and_(*extra_conditions))

        if not order_by:
            order_by = [("created_at", "desc")]

        for field, direction in order_by:
            column = col(getattr(cls, field))
            statement = statement.order_by(
                asc(column) if direction.lower() == "asc" else desc(column)
            )

        if page is not None and per_page is not None:
            statement = statement.offset((page - 1) * per_page).limit(per_page)
        items = (await session.exec(statement)).all()

        count_statement = select(func.count(cls.id))
        if fields:
            conditions = [
                col(getattr(cls, key)) == value for key, value in fields.items()
            ]
            count_statement = count_statement.where(and_(*conditions))

        if fuzzy_fields:
            fuzzy_conditions = [
                col(getattr(cls, key)).like(f"%{value}%")
                for key, value in fuzzy_fields.items()
            ]
            count_statement = count_statement.where(or_(*fuzzy_conditions))

        if extra_conditions:
            count_statement = count_statement.where(and_(*extra_conditions))

        count = (await session.exec(count_statement)).one()
        total_page = math.ceil(count / per_page)
        pagination = Pagination(
            page=page,
            perPage=per_page,
            total=count,
            totalPage=total_page,
        )

        return PaginatedList[cls](items=items, pagination=pagination)

    @classmethod
    def convert_without_saving(
        cls, source: Union[dict, SQLModel], update: Optional[dict] = None
    ) -> SQLModel:
        """
        Convert the source to the model without saving to the database.
        Return None if failed.
        """

        if isinstance(source, SQLModel):
            obj = cls.from_orm(source, update=update)
        elif isinstance(source, dict):
            obj = cls.parse_obj(source, update=update)
        return obj

    @classmethod
    async def create(
        cls,
        session: AsyncSession,
        source: Union[dict, SQLModel],
        update: Optional[dict] = None,
    ) -> Optional[SQLModel]:
        """Create and save a new record for the model."""

        obj = cls.convert_without_saving(source, update)
        if obj is None:
            return None

        await obj.save(session)
        await cls._publish_event(EventType.CREATED, obj)
        return obj

    @classmethod
    async def create_or_update(
        cls,
        session: AsyncSession,
        source: Union[dict, SQLModel],
        update: Optional[dict] = None,
    ) -> Optional[SQLModel]:
        """Create or update a record for the model."""

        obj = cls.convert_without_saving(source, update)
        if obj is None:
            return None
        pk = cls.__mapper__.primary_key_from_instance(obj)
        if pk[0] is not None:
            existing = await session.get(cls, pk)
            if existing is None:
                return None
            else:
                await existing.update(session, obj)
                return existing
        else:
            return await cls.create(session, obj)

    @classmethod
    async def count(cls, session: AsyncSession) -> int:
        """Return the number of records in the model."""

        return len(await cls.all(session))

    async def refresh(self, session: AsyncSession):
        """Refresh the object from the database."""

        await session.refresh(self)

    async def save(self, session: AsyncSession):
        """Save the object to the database. Raise exception if failed."""

        session.add(self)
        try:
            await session.commit()
            await session.refresh(self)
        except (IntegrityError, OperationalError, FlushError) as e:
            await session.rollback()
            raise e

    async def update(
        self, session: AsyncSession, source: Union[dict, SQLModel, None] = None
    ):
        """Update the object with the source and save to the database."""

        if isinstance(source, SQLModel):
            source = source.model_dump(exclude_unset=True)
        elif source is None:
            source = {}

        for key, value in source.items():
            setattr(self, key, value)
        await self.save(session)
        await self._publish_event(EventType.UPDATED, self)

    async def delete(self, session: AsyncSession):
        """Delete the object from the database."""

        if self._has_cascade_delete():
            if hasattr(self, "deleted_at"):
                # timestamp is stored without timezone in db
                self.deleted_at = datetime.now(timezone.utc).replace(tzinfo=None)
                await self.save(session)
            await self._handle_cascade_delete(session)

        await session.delete(self)
        await session.commit()
        await self._publish_event(EventType.DELETED, self)

    async def _handle_cascade_delete(self, session: AsyncSession):
        """Handle cascading deletes for all defined relationships."""
        for rel in self.__mapper__.relationships:
            if rel.cascade.delete:
                # Load the related objects
                await session.refresh(self)
                related_objects = getattr(self, rel.key)

                # Delete each related object
                if isinstance(related_objects, list):
                    for related_object in related_objects:
                        await related_object.delete(session)
                elif related_objects:
                    await related_objects.delete(session)

    def _has_cascade_delete(self):
        """Check if the model has cascade delete relationships."""
        return any(rel.cascade.delete for rel in self.__mapper__.relationships)

    @classmethod
    async def all(cls, session: AsyncSession):
        """Return all objects of the model."""

        result = await session.exec(select(cls))
        return result.all()

    @classmethod
    async def delete_all(cls, session: AsyncSession):
        """Delete all objects of the model."""

        for obj in await cls.all(session):
            await obj.delete(session)
            await cls._publish_event(EventType.DELETED, obj)

    @classmethod
    async def _publish_event(cls, event_type: str, data: Any):
        try:
            print(f"{__file__} 数据库操作后, publish {cls.__name__}::{event_type}")
            await event_bus.publish(
                cls.__name__.lower(), Event(type=event_type, data=data)
            )
        except Exception as e:
            logger.error(f"Failed to publish event: {e}")

    @overload
    @classmethod
    async def subscribe(
        cls, session_or_engine: AsyncSession
    ) -> AsyncGenerator[Event, None]: ...

    @overload
    @classmethod
    async def subscribe(
        cls, session_or_engine: AsyncEngine
    ) -> AsyncGenerator[Event, None]: ...

    @classmethod
    async def subscribe(
        cls, session_or_engine: Union[AsyncSession, AsyncEngine], whoami: str = None
    ) -> AsyncGenerator[Event, None]:
        if isinstance(session_or_engine, AsyncSession):
            items = await cls.all(session_or_engine)
            print(f"{__file__} 扫表 {cls.__name__}, 发布event create")
            for item in items:
                yield Event(type=EventType.CREATED, data=item)
            await session_or_engine.close()
        elif isinstance(session_or_engine, AsyncEngine):
            async with AsyncSession(session_or_engine) as session:
                items = await cls.all(session)
                print(f"{__file__} 扫表 {cls.__name__}, 发布event create")
                for item in items:
                    yield Event(type=EventType.CREATED, data=item)
        else:
            raise ValueError("Invalid session or engine.")

        subscriber = event_bus.subscribe(cls.__name__.lower())
        heartbeat_interval = timedelta(seconds=15 * 1000)
        last_event_time = datetime.now(timezone.utc)

        try:
            while True:
                try:
                    event = await asyncio.wait_for(
                        subscriber.receive(), timeout=heartbeat_interval.total_seconds()
                    )
                    print(f"{__file__} {whoami} 收到事件 {cls.__name__}, {event}")
                    yield event
                except asyncio.TimeoutError:
                    if (
                        datetime.now(timezone.utc) - last_event_time
                        >= heartbeat_interval
                    ):
                        yield Event(type=EventType.HEARTBEAT, data=None)
                        last_event_time = datetime.now(timezone.utc)
        finally:
            event_bus.unsubscribe(cls.__name__.lower(), subscriber)

    @classmethod
    async def streaming(
        cls,
        session: AsyncSession,
        fields: Optional[dict] = None,
        fuzzy_fields: Optional[dict] = None,
        filter_func: Optional[Callable[[Any], bool]] = None,
    ) -> AsyncGenerator[str, None]:
        """Stream events matching the given criteria as JSON strings."""
        async for event in cls.subscribe(session, whoami=cls.__name__):
            if event.type == EventType.HEARTBEAT:
                yield "\n\n"
                continue

            if not cls._match_fields(event, fields):
                continue

            if not cls._match_fuzzy_fields(event, fuzzy_fields):
                continue

            if filter_func and not filter_func(event.data):
                continue

            event.data = cls._convert_to_public_class(event.data)
            yield cls._format_event(event)

    @classmethod
    def _match_fields(cls, event: Any, fields: Optional[dict]) -> bool:
        """Match fields using AND condition."""
        for key, value in (fields or {}).items():
            if getattr(event.data, key, None) != value:
                return False
        return True

    @classmethod
    def _match_fuzzy_fields(cls, event: Any, fuzzy_fields: Optional[dict]) -> bool:
        """Match fuzzy fields using OR condition."""
        for key, value in (fuzzy_fields or {}).items():
            attr_value = str(getattr(event.data, key, "")).lower()
            if str(value).lower() in attr_value:
                return True
        return not fuzzy_fields

    @classmethod
    def _convert_to_public_class(cls, data: Any) -> Any:
        """Convert the instance to the corresponding Public class if it exists."""
        class_module = importlib.import_module(cls.__module__)
        public_class = getattr(class_module, f"{cls.__name__}Public", None)
        return public_class.model_validate(data) if public_class else data

    @staticmethod
    def _format_event(event: Any) -> str:
        """Format the event as a JSON string."""
        return json.dumps(jsonable_encoder(event), separators=(",", ":")) + "\n\n"
