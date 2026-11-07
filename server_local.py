import os
from pathlib import Path
from fastmcp import FastMCP

VAULT = Path(os.environ.get("VAULT_DIR", "./vault")).resolve()
mcp = FastMCP("vault")


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
    return sorted(str(p.relative_to(VAULT)) for p in _notas())


@mcp.tool
def leer_nota(path: str) -> str:
    """Devuelve el contenido completo de una nota por su ruta relativa."""
    p = _safe(path)
    if p.suffix != ".md" or not p.is_file():
        raise ValueError("Nota no encontrada")
    return p.read_text(encoding="utf-8")


@mcp.tool
def buscar_notas(query: str, max_resultados: int = 20) -> list[dict]:
    """Busca texto (sin distinguir mayúsculas) en todas las notas."""
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
    mcp.run(transport="http", host="127.0.0.1", port=8000)
