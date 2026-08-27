from datetime import datetime

from kosmo.contracts.integrations.github import (
    CodeSyncLog,
    CodeSyncStatus,
    ProjectGitHubIntegration,
    UserGitHubIntegration,
)
from kosmo.contracts.sdd.ids import ProjectId, UserId


def test_user_github_integration_defaults():
    integration = UserGitHubIntegration(
        user_id=UserId("user-1"), github_username="testuser", encrypted_token="encrypted-pat"
    )
    assert integration.user_id == "user-1"
    assert integration.github_username == "testuser"
    assert integration.encrypted_token == "encrypted-pat"
    assert isinstance(integration.updated_at, datetime)
    assert integration.updated_at.tzinfo is not None


def test_project_github_integration_defaults():
    integration = ProjectGitHubIntegration(
        project_id=ProjectId("proj-1"), repo_url="https://github.com/testuser/testrepo"
    )
    assert integration.project_id == "proj-1"
    assert integration.repo_url == "https://github.com/testuser/testrepo"
    assert integration.default_branch == "main"
    assert integration.last_synced_at is None


def test_code_sync_log_defaults():
    log = CodeSyncLog()
    assert log.id is not None
    assert log.project_id == ""
    assert log.commit_sha is None
    assert log.status == CodeSyncStatus.FAILED
    assert log.message is None
    assert isinstance(log.synced_at, datetime)
