from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """Base for all API request/response schemas. The wire format (JSON in
    and out) is camelCase, matching CLAUDE.md's TypeScript/React convention;
    Python/DB internals -- field names below, ORM columns, everything else
    -- stay snake_case. populate_by_name=True means snake_case is still
    accepted on input, so nothing server-side breaks if it slips through."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)
