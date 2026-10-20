import uuid
from datetime import datetime

from pydantic import Field, model_validator

from app.constants import Category, Urgency
from app.schemas.common import InputModel, ItemCount, OutputModel, reject_explicit_nulls


class NeedCreate(InputModel):
    category: Category
    quantity_needed: ItemCount
    urgency: Urgency


class NeedUpdate(InputModel):
    """A need's category is fixed; to need something else, add a new need. Needs are
    never deleted: set is_active to false instead."""

    quantity_needed: ItemCount | None = None
    urgency: Urgency | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def check_partial_update(self):
        reject_explicit_nulls(self)
        return self


class NeedOut(OutputModel):
    id: uuid.UUID
    category: Category
    quantity_needed: int = Field(description="A count of items.")
    urgency: Urgency
    is_active: bool
    created_at: datetime
    updated_at: datetime
