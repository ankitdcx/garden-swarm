"""Proposal-only cognition. This package cannot register assessments or execute tools."""
from .swarm import AgentRequest, build_bundle, ROLE_NAMES
from .backends import RuleBasedBackend, LlamaCppBackend, OllamaBackend, BackendError
__all__ = ["AgentRequest", "build_bundle", "ROLE_NAMES", "RuleBasedBackend", "LlamaCppBackend", "OllamaBackend", "BackendError"]
