import os
import subprocess
import threading
import time
from pathlib import Path

from fastmcp import FastMCP
from fastmcp.server.auth.providers.github import GitHubProvider
from fastmcp.server.dependencies import get_access_token

# Fallan si falta alguna: el servidor no arranca sin autenticación
OWNER = os.environ["OWNER_LOGIN"]
VAULT_REPO = os.environ["VAULT_REPO"]
VAULT_TOKEN = os.environ["VAULT_TOKEN"]

VAULT = Path(os.environ.get("VAULT_DIR", "/tmp/vault")).resolve()
REMOTE = f"https://x-access-token:{VAULT_TOKEN}@github.com/{VAULT_REPO}.git"


def _sync():
    try:
        if (VAULT / ".git").exists():
            cmd = ["git", "-C", str(VAULT), "pull", "--ff-only"]
        else:
            cmd = ["git", "clone", "--depth", "1", REMOTE, str(VAULT)]
        subprocess.run(cmd, check=True, capture_output=True, timeout=120)
    except Exception as e:
        print("sync falló:", type(e).__name__, flush=True)


def _loop():
    while True:
        time.sleep(300)
        _sync()


auth = GitHubProvider(
    client_id=os.environ["GITHUB_CLIENT_ID"],
    client_secret=os.environ["GITHUB_CLIENT_SECRET"],
    base_url=os.environ["BASE_URL"],
    jwt_signing_key=os.environ["JWT_SIGNING_KEY"],
)
mcp = FastMCP("vault", auth=auth)


def _check():
    t = get_access_token()
    if t is None or t.claims.get("login") != OWNER:
        raise PermissionError("No autorizado")


def _safe(path: str) -> Path:
    p = (VAULT / path).resolve()
    if not p.is_relative_to(VAULT) or ".git" in p.relative_to(VAULT).parts:
        raise ValueError("Ruta no permitida")
    return p


def _notas():
    return [p for p in VAULT.rglob("*.md") if ".git" not in p.parts]


@mcp.tool
def listar_notas() -> list[str]:
    """Lista todas las notas .md del vault (rutas relativas)."""
    _check()
    return sorted(str(p.relative_to(VAULT)) for p in _notas())


@mcp.tool
def leer_nota(path: str) -> str:
    """Devuelve el contenido completo de una nota por su ruta relativa."""
    _check()
    p = _safe(path)
    if p.suffix != ".md" or not p.is_file():
        raise ValueError("Nota no encontrada")
    return p.read_text(encoding="utf-8")


@mcp.tool
def buscar_notas(query: str, max_resultados: int = 20) -> list[dict]:
    """Busca texto (sin distinguir mayúsculas) en todas las notas."""
    _check()
    q = query.lower()
    out = []
    for p in sorted(_notas()):
        for i, linea in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if q in linea.lower():
                out.append({"path": str(p.relative_to(VAULT)), "linea": i, "texto": linea.strip()[:200]})
                if len(out) >= max_resultados:
                    return out
    return out


if __name__ == "__main__":
    _sync()
    threading.Thread(target=_loop, daemon=True).start()
    mcp.run(transport="http", host="0.0.0.0", port=int(os.environ.get("PORT", "10000")))
