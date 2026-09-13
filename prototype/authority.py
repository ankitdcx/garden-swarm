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


@dataclass(frozen=True)
class AuthorityScope:
    subject: str
    actions: frozenset[str]
    resources: frozenset[str]
    source_ref: str


@dataclass(frozen=True)
class AuthorityProvenanceChain:
    chain_id: str
    controlling_scopes: tuple[AuthorityScope, ...]
    provenance_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.chain_id or not self.controlling_scopes or not self.provenance_refs:
            raise ValueError("authority provenance chain requires id, controlling scopes, and provenance")


@dataclass(frozen=True)
class ActionEligibleArtifact:
    artifact_id: str
    target_action: str
    target_resource: str
    authority_chain: AuthorityProvenanceChain

    def __post_init__(self) -> None:
        if not self.artifact_id or not self.target_action or not self.target_resource:
            raise ValueError("action-eligible artifact requires id/action/resource")


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
    """Total deterministic predicate over already-resolved authority inputs."""
    effective = compose_authority(envelopes)
    return (
        action in effective.actions
        and resource in effective.resources
        and depth <= effective.max_depth
    )


def intersect_authority_scopes(scopes: Iterable[AuthorityScope]) -> AuthorityScope:
    """Intersect direct and shared-state controlling authority without amplification."""
    items = tuple(scopes)
    if not items:
        raise ValueError("authority intersection requires at least one scope")
    return AuthorityScope(
        subject="intersection:" + "->".join(item.subject for item in items),
        actions=reduce(frozenset.intersection, (item.actions for item in items)),
        resources=reduce(frozenset.intersection, (item.resources for item in items)),
        source_ref="intersection:" + "->".join(item.source_ref for item in items),
    )


def effective_authority_for_artifact_trigger(
    *, acting_scope: AuthorityScope, artifact: ActionEligibleArtifact
) -> AuthorityScope:
    """Preserve authority provenance when shared state triggers downstream action."""
    return intersect_authority_scopes(
        (acting_scope, *artifact.authority_chain.controlling_scopes)
    )


def authorize_artifact_trigger(
    *, acting_scope: AuthorityScope, artifact: ActionEligibleArtifact
) -> bool:
    """Total predicate over the composed shared-state authority path."""
    effective = effective_authority_for_artifact_trigger(
        acting_scope=acting_scope,
        artifact=artifact,
    )
    return (
        artifact.target_action in effective.actions
        and artifact.target_resource in effective.resources
    )
