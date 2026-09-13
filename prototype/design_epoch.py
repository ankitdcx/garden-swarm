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
    required_dependencies: frozenset[str] | None = None


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
    stale_reasons: list[str] = []

    if binding.design_epoch != current_design_epoch:
        stale_reasons.append(
            f"DESIGN_EPOCH_CHANGED:{binding.design_epoch}->{current_design_epoch}"
        )

    # A binding cannot be called CURRENT unless it declares the dependency
    # closure it claims to cover. If it is already definitely stale, preserve
    # that stronger fact while still reporting the closure defect.
    if binding.required_dependencies is None:
        reason = "DEPENDENCY_CLOSURE_NOT_DECLARED"
        if stale_reasons:
            return ValidationResult(BindingStatus.STALE, tuple(stale_reasons + [reason]))
        return ValidationResult(BindingStatus.UNKNOWN, (reason,))

    omitted_required = sorted(binding.required_dependencies - set(binding.dependencies))
    if omitted_required:
        closure_reasons = [f"DEPENDENCY_CLOSURE_INCOMPLETE:{name}" for name in omitted_required]
        if stale_reasons:
            return ValidationResult(BindingStatus.STALE, tuple(stale_reasons + closure_reasons))
        return ValidationResult(BindingStatus.UNKNOWN, tuple(closure_reasons))

    missing = sorted(set(binding.dependencies) - set(current_dependencies))
    if missing:
        unknown_reasons = [f"DEPENDENCY_STATE_UNKNOWN:{name}" for name in missing]
        if stale_reasons:
            return ValidationResult(BindingStatus.STALE, tuple(stale_reasons + unknown_reasons))
        return ValidationResult(BindingStatus.UNKNOWN, tuple(unknown_reasons))

    for name, bound_version in binding.dependencies.items():
        current_version = current_dependencies[name]
        if current_version != bound_version:
            stale_reasons.append(
                f"DEPENDENCY_CHANGED:{name}:{bound_version}->{current_version}"
            )

    if stale_reasons:
        return ValidationResult(BindingStatus.STALE, tuple(stale_reasons))

    return ValidationResult(BindingStatus.CURRENT, ("BINDING_CURRENT",))
