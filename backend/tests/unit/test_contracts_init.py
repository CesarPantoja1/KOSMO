from __future__ import annotations

import pytest

import kosmo.contracts as contracts


@pytest.mark.unit
def test_contracts_init_exports_all_declared_symbols() -> None:
    # Arrange & Act
    exported_names = contracts.__all__

    # Assert: Each symbol in __all__ must exist as an attribute on the module
    for name in exported_names:
        assert hasattr(contracts, name), f"Symbol '{name}' listed in __all__ is missing on kosmo.contracts"
        attr = getattr(contracts, name)
        assert attr is not None or name in ("get_telemetry_provider",), f"Symbol '{name}' resolved to None"


@pytest.mark.unit
def test_contracts_init_includes_core_bounded_contexts() -> None:
    # Auth
    from kosmo.contracts import (
        AccountLockedError,
        AuthError,
        EncryptedSecret,
        Principal,
        SecretCipher,
        TokenClaims,
        User,
        UserRepository,
        current_user_id,
    )

    assert Principal is not None
    assert User is not None
    assert UserRepository is not None
    assert AccountLockedError is not None
    assert AuthError is not None
    assert EncryptedSecret is not None
    assert SecretCipher is not None
    assert TokenClaims is not None
    assert current_user_id is not None

    # Audit
    from kosmo.contracts import AuditEvent, AuditEventSink, AuditOutcome

    assert AuditEvent is not None
    assert AuditEventSink is not None
    assert AuditOutcome is not None

    # Integrations
    from kosmo.contracts import (
        DeploymentProviderPort,
        DeploymentStatus,
        GitHubClientPort,
        GitWorkspacePort,
        ProjectDeployment,
        ProjectGitHubIntegration,
    )

    assert DeploymentProviderPort is not None
    assert DeploymentStatus is not None
    assert GitHubClientPort is not None
    assert GitWorkspacePort is not None
    assert ProjectDeployment is not None
    assert ProjectGitHubIntegration is not None

    # LLM
    from kosmo.contracts import LLMClient, LLMResponse, PromptTemplate

    assert LLMClient is not None
    assert LLMResponse is not None
    assert PromptTemplate is not None

    # Memory
    from kosmo.contracts import UserPreference

    assert UserPreference is not None

    # Persistence
    from kosmo.contracts import OutboxPort, UnitOfWork

    assert OutboxPort is not None
    assert UnitOfWork is not None

    # Pipeline
    from kosmo.contracts import (
        AgentPort,
        DiscoveryPhaseContext,
        FeaturesPhaseOutput,
        PhaseMode,
        ValidationResult,
    )

    assert AgentPort is not None
    assert DiscoveryPhaseContext is not None
    assert FeaturesPhaseOutput is not None
    assert PhaseMode is not None
    assert ValidationResult is not None

    # SDD
    from kosmo.contracts import (
        ActivityDiagramRepository,
        DocumentRepository,
        Feature,
        FeatureRepository,
        Project,
        ProjectId,
        ProjectRepository,
        RequirementRepository,
        SpecPhase,
        UXContext,
    )

    assert ActivityDiagramRepository is not None
    assert DocumentRepository is not None
    assert Feature is not None
    assert FeatureRepository is not None
    assert Project is not None
    assert ProjectId is not None
    assert ProjectRepository is not None
    assert RequirementRepository is not None
    assert SpecPhase is not None
    assert UXContext is not None

    # Telemetry
    from kosmo.contracts import TelemetryPort, record_auth_event, traced

    assert TelemetryPort is not None
    assert record_auth_event is not None
    assert traced is not None
