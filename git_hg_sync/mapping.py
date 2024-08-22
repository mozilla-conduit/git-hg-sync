import re
from dataclasses import dataclass
from functools import cached_property

import pydantic

from git_hg_sync.events import Push


class MappingSource(pydantic.BaseModel):
    url: str
    branch_pattern: str


class MappingDestination(pydantic.BaseModel):
    url: str
    branch: str


@dataclass
class MappingMatch:
    source_commit: str
    destination_url: str
    destination_branch: str


class Mapping(pydantic.BaseModel):
    source: MappingSource
    destination: MappingDestination

    @cached_property
    def _branch_pattern(self) -> re.Pattern:
        return re.compile(self.source.branch_pattern)

    def match(self, event: Push) -> list[MappingMatch]:
        if event.repo_url != self.source.url:
            return []
        matches: list[MappingMatch] = []
        for branch_name, commit in event.branches.items():
            if not self._branch_pattern.match(branch_name):
                continue
            destination_url = re.sub(
                self._branch_pattern, self.destination.url, branch_name
            )
            destination_branch = re.sub(
                self._branch_pattern, self.destination.branch, branch_name
            )
            matches.append(
                MappingMatch(
                    source_commit=commit,
                    destination_url=destination_url,
                    destination_branch=destination_branch,
                )
            )
        return matches
