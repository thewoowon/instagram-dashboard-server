import uuid
import pkgutil
import importlib
from sqlalchemy import Column, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import as_declarative, declared_attr
import app.models


@as_declarative()
class Base:
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    @declared_attr
    def __tablename__(cls) -> str:
        return cls.__name__.lower()


def load_all_models():
    for _, module_name, _ in pkgutil.iter_modules(app.models.__path__):
        importlib.import_module(f"app.models.{module_name}")


load_all_models()
