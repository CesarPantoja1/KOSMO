from typing import Protocol, runtime_checkable


@runtime_checkable
class GitWorkspacePort(Protocol):
    """Puerto para interactuar con repositorios Git locales del workspace."""

    def remote_add_or_update(self, workspace_path: str, name: str, url: str) -> None:
        """Añade un remoto al repositorio local o actualiza su URL si ya existe."""
        ...

    def build_authenticated_url(self, repo_url: str, token: str) -> str:
        """Construye una URL HTTPS autenticada utilizando el token provisto."""
        ...

    def push(
        self,
        workspace_path: str,
        remote: str = "origin",
        branch: str | None = None,
        *,
        token: str | None = None,
    ) -> str:
        """
        Ejecuta git push hacia el repositorio remoto, validando commits.
        Retorna el hash del commit en HEAD que fue enviado. Si se proporciona
        ``token``, se usa únicamente para este push y no se persiste en la URL
        configurada del remoto.
        """
        ...
