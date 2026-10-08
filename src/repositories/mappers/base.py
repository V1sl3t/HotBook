from typing import Any, ClassVar

from pydantic import BaseModel

from src.db import Base


class DataMapper[DBModel: Base, Schema: BaseModel]:
    db_model: ClassVar[type[Any]]
    schema: ClassVar[type[Any]]

    @classmethod
    def map_to_domain_entity(cls, data: Any) -> Any:
        return cls.schema.model_validate(data, from_attributes=True)

    @classmethod
    def map_to_persistence_entity(cls, data: BaseModel) -> Any:
        return cls.db_model(**data.model_dump())
