from __future__ import annotations

from dataclasses import dataclass
from functools import reduce
from typing import Iterable


@dataclass(frozen=True)
class AuthorityEnvelope:
    subject: str
    actions: frozenset[str]
    resources: frozenset[str]
    max_depth: int


def compose_authority(envelopes: Iterable[AuthorityEnvelope]) -> AuthorityEnvelope:
    """Return the conservative intersection of every required authority envelope."""

    items = tuple(envelopes)
    if not items:
        raise ValueError("at least one authority envelope is required")

    actions = reduce(frozenset.intersection, (item.actions for item in items))
    resources = reduce(frozenset.intersection, (item.resources for item in items))
    max_depth = min(item.max_depth for item in items)

    return AuthorityEnvelope(
        subject="composition:" + "->".join(item.subject for item in items),
        actions=actions,
        resources=resources,
        max_depth=max_depth,
    )


def can_execute(
    envelopes: Iterable[AuthorityEnvelope], *, action: str, resource: str, depth: int
) -> bool:
    effective = compose_authority(envelopes)
    return (
        action in effective.actions
        and resource in effective.resources
        and depth <= effective.max_depth
    )
