from pydantic import BaseModel


class Push(BaseModel):
    repo_url: str
    branches: dict[
        str, str
    ]  # Mapping between branch names (key) and corresponding commit sha (value)
    tags: dict[
        str, str
    ]  # Mapping between tag names (key) and corresponding commit sha (value)
    time: int
    pushid: int
    user: str
    push_json_url: str


class Tag(BaseModel):
    repo_url: str
    tag: str
    commit: str
    time: int
    pushid: int
    user: str
    push_json_url: str
