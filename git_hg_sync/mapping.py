import re
from collections.abc import Sequence
from dataclasses import dataclass
from functools import cached_property
from typing import TypeAlias

import pydantic

from git_hg_sync.events import Push

DEFAULT_TAG_MESSAGE_SUFFIX = "a=tagging CLOSED TREE DONTBUILD"


@dataclass
class SyncBranchOperation:
    # Source (git)
    source_commit: str

    # Destination (hg)
    destination_branch: str


@dataclass
class SyncTagOperation:
    # Source (git)
    source_commit: str

    # Destination (hg)
    tag: str
    tags_destination_branch: str
    tag_message_suffix: str


SyncOperation: TypeAlias = SyncBranchOperation | SyncTagOperation


@dataclass
class MappingMatch:
    destination_url: str
    operation: SyncBranchOperation | SyncTagOperation


class Mapping(pydantic.BaseModel):
    source_url: str

    def match(self, event: Push) -> Sequence[MappingMatch]:
        raise NotImplementedError()


# Branch Mapping


class BranchMapping(Mapping):
    branch_pattern: str
    destination_url: str
    destination_branch: str

    @cached_property
    def _branch_pattern(self) -> re.Pattern:
        return re.compile(self.branch_pattern)

    def match(self, event: Push) -> Sequence[MappingMatch]:
        if event.repo_url != self.source_url:
            return []
        matches: list[MappingMatch] = []
        for branch_name, commit in event.branches.items():
            if not self._branch_pattern.match(branch_name):
                continue
            destination_url = re.sub(
                self._branch_pattern, self.destination_url, branch_name
            )
            destination_branch = re.sub(
                self._branch_pattern, self.destination_branch, branch_name
            )
            matches.append(
                MappingMatch(
                    destination_url=destination_url,
                    operation=SyncBranchOperation(
                        source_commit=commit,
                        destination_branch=destination_branch,
                    ),
                )
            )
        return matches


# Tag Mapping


class TagMapping(Mapping):
    tag_pattern: str
    destination_url: str
    tags_destination_branch: str
    tag_message_suffix: str = DEFAULT_TAG_MESSAGE_SUFFIX

    @cached_property
    def _tag_pattern(self) -> re.Pattern:
        return re.compile(self.tag_pattern)

    def match(self, event: Push) -> Sequence[MappingMatch]:
        if event.repo_url != self.source_url:
            return []
        matches: list[MappingMatch] = []
        for tag_name, commit in event.tags.items():
            if not self._tag_pattern.match(tag_name):
                continue
            destination_url = re.sub(self._tag_pattern, self.destination_url, tag_name)
            matches.append(
                MappingMatch(
                    destination_url=destination_url,
                    operation=SyncTagOperation(
                        tag=tag_name,
                        source_commit=commit,
                        tags_destination_branch=self.tags_destination_branch,
                        tag_message_suffix=self.tag_message_suffix,
                    ),
                )
            )
        return matches
