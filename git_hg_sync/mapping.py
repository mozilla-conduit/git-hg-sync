from dataclasses import dataclass

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

    def match(self, event: Push) -> list[MappingMatch]:
        if event.repo_url != self.source.url:
            return []
        matches: list[MappingMatch] = []
        for branch_name, commit in event.branches.items():
            if branch_name == self.source.branch_pattern:
                matches.append(
                    MappingMatch(
                        source_commit=commit,
                        destination_url=self.destination.url,
                        destination_branch=self.destination.branch,
                    )
                )
        return matches
