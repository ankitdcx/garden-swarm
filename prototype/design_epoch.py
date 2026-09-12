from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping


class BindingStatus(str, Enum):
    CURRENT = "CURRENT"
    STALE = "STALE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class ArtifactBinding:
    artifact_id: str
    design_epoch: str
    dependencies: Mapping[str, str]


@dataclass(frozen=True)
class ValidationResult:
    status: BindingStatus
    reasons: tuple[str, ...]


def validate_binding(
    binding: ArtifactBinding,
    *,
    current_design_epoch: str,
    current_dependencies: Mapping[str, str],
) -> ValidationResult:
    reasons: list[str] = []

    if binding.design_epoch != current_design_epoch:
        reasons.append(
            f"DESIGN_EPOCH_CHANGED:{binding.design_epoch}->{current_design_epoch}"
        )

    missing = sorted(set(binding.dependencies) - set(current_dependencies))
    if missing:
        return ValidationResult(
            BindingStatus.UNKNOWN,
            tuple(f"DEPENDENCY_STATE_UNKNOWN:{name}" for name in missing),
        )

    for name, bound_version in binding.dependencies.items():
        current_version = current_dependencies[name]
        if current_version != bound_version:
            reasons.append(
                f"DEPENDENCY_CHANGED:{name}:{bound_version}->{current_version}"
            )

    if reasons:
        return ValidationResult(BindingStatus.STALE, tuple(reasons))

    return ValidationResult(BindingStatus.CURRENT, ("BINDING_CURRENT",))
