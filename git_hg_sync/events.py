from typing import Self

from pydantic import (
    BaseModel,
    Field,
    model_validator,
)


class Push(BaseModel):
    repo_url: str
    branches: dict[str, str] | None = Field(
        default_factory=dict
    )  # Mapping between branch names (key) and corresponding commit sha (value)
    tags: dict[str, str] | None = Field(
        default_factory=dict
    )  # Mapping between tag names (key) and corresponding commit sha (value)
    time: int
    pushid: int
    user: str
    push_json_url: str

    @model_validator(mode="after")
    def check_branch_tags(self) -> Self:
        """Check that at least one of branches or tags is not empty."""
        if not self.branches and not self.tags:
            raise ValueError("Either (non-empty) branches or tags is required")
        return self


Event = Push
