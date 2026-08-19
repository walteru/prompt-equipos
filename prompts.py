#!/usr/bin/env python3
"""Genera prompts de trabajo en _temps/ a partir de la plantilla maestra.

Uso:
    prompts                 # autodetecta el proyecto, abre $EDITOR para el requerimiento
    prompts --proyecto X    # fuerza el nombre del proyecto (en caso de ambigüedad)
    prompts --plantilla P   # usa otra plantilla en vez de inicial.txt

Requiere, en el directorio actual:
    - al menos un archivo context_inicial_<proyecto>.txt o .md
    - un directorio _temps/ (se crea si falta)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_TEMPLATE = SCRIPT_DIR / "inicial.txt"

CONTEXT_GLOBS = ("context_inicial_*.txt", "context_inicial_*.md")
CONTEXT_RE = re.compile(r"^context_inicial_(?P<name>.+)\.(?:txt|md)$")
SEPARATOR_RE = re.compile(r"^-{20,}\s*$", re.MULTILINE)
CORE_PROMPT_SECTIONS = (
    "TESTING",
    "DEV",
    "SINGLE_DEVELOPER",
    "ANALISIS",
)
OPTIONAL_PROMPT_SECTIONS = (
    "TEST_EN_BROWSER",
)
CONSENSUS_PROMPT_SECTIONS = (
    "ANALISIS_A",
    "ANALISIS_B",
)
PROMPT_SECTIONS = CORE_PROMPT_SECTIONS + OPTIONAL_PROMPT_SECTIONS + CONSENSUS_PROMPT_SECTIONS
DEV_PHASES = ("plan", "implement")
TESTING_PHASES = ("baseline", "review")
PROFILES = ("auto", "mixed", "php", "frontend", "javascript", "python", "mysql", "scripting")

EDITOR_HEADER = """# Escribí abajo SOLO el requerimiento del sprint/iteración.
# Las líneas que empiezan con '#' se ignoran.
# Guardá y cerrá el editor para generar los prompts.
# Dejá el archivo vacío (o cerrá sin guardar) para cancelar.
#
# Importante:
# - Este contenido será marcado como "REQUERIMIENTO DEL SPRINT ACTUAL".
# - Los archivos context_inicial_*.txt, context_inicial_*.md y proxima.md serán tratados solo como contexto.
# - No pegues contexto general acá salvo que quieras que sea parte accionable del sprint.
#
# Este archivo (_temps/REQUERIMIENTO.txt) se conserva entre corridas:
# la próxima vez que ejecutes 'prompts' se abrirá con este contenido
# pre-cargado para que puedas editarlo o agregar cosas olvidadas.

"""


def detect_project(cwd: Path, override: str | None) -> str:
    if override:
        expected = [
            cwd / f"context_inicial_{override}{suffix}"
            for suffix in (".txt", ".md")
        ]
        if not any(path.is_file() for path in expected):
            sys.exit(
                f"[prompts] No existe context_inicial_{override}.txt ni "
                f"context_inicial_{override}.md en {cwd}. "
                "Verificá el nombre del proyecto."
            )
        return override

    candidates = []
    selected_glob = ""
    for context_glob in CONTEXT_GLOBS:
        candidates = sorted(
            p for p in cwd.glob(context_glob) if CONTEXT_RE.match(p.name)
        )
        if candidates:
            selected_glob = context_glob
            break

    if not candidates:
        sys.exit(
            f"[prompts] No encontré ningún {CONTEXT_GLOBS[0]} ni "
            f"{CONTEXT_GLOBS[1]} en {cwd}. "
            "Ejecutá el comando dentro del directorio del proyecto."
        )
    if len(candidates) > 1:
        listado = "\n  - ".join(p.name for p in candidates)
        sys.exit(
            f"[prompts] Hay múltiples archivos {selected_glob}:\n  - {listado}\n"
            "Pasá --proyecto <nombre> para elegir uno."
        )
    return CONTEXT_RE.match(candidates[0].name)["name"]


def parse_template(template_path: Path) -> dict[str, str]:
    if not template_path.is_file():
        sys.exit(f"[prompts] No existe la plantilla: {template_path}")

    raw = template_path.read_text(encoding="utf-8")
    parts = [p.strip("\n") for p in SEPARATOR_RE.split(raw)]
    parts = [p for p in parts if p.strip()]

    sections: dict[str, str] = {}
    i = 0
    while i < len(parts) - 1:
        header = parts[i].strip()
        if header in PROMPT_SECTIONS:
            sections[header] = parts[i + 1].rstrip() + "\n"
            i += 2
        else:
            i += 1

    missing = set(CORE_PROMPT_SECTIONS) - sections.keys()
    if missing:
        sys.exit(
            f"[prompts] La plantilla no tiene la(s) sección(es): {', '.join(sorted(missing))}. "
            "Revisá los separadores en inicial.txt."
        )

    consensus_present = set(CONSENSUS_PROMPT_SECTIONS) & sections.keys()
    if consensus_present and consensus_present != set(CONSENSUS_PROMPT_SECTIONS):
        missing_consensus = set(CONSENSUS_PROMPT_SECTIONS) - consensus_present
        sys.exit(
            "[prompts] Las secciones de análisis consensuado deben aparecer juntas. "
            f"Falta: {', '.join(sorted(missing_consensus))}."
        )
    return sections


def useful_requirement(content: str) -> str:
    lines = [line for line in content.splitlines() if not line.lstrip().startswith("#")]
    return "\n".join(lines).strip()


def read_requirement(
    temps_dir: Path,
    requirement_path: Path | None,
    non_interactive: bool,
) -> str:
    if requirement_path:
        if str(requirement_path) == "-":
            requirement = useful_requirement(sys.stdin.read())
        else:
            if not requirement_path.is_file():
                sys.exit(f"[prompts] No existe el archivo de requerimiento: {requirement_path}")
            requirement = useful_requirement(requirement_path.read_text(encoding="utf-8"))
        if not requirement:
            sys.exit("[prompts] El requerimiento quedó vacío. Cancelado.")
        (temps_dir / "REQUERIMIENTO.txt").write_text(requirement + "\n", encoding="utf-8")
        return requirement

    editor = os.environ.get("EDITOR") or os.environ.get("VISUAL") or "vim"
    req_path = temps_dir / "REQUERIMIENTO.txt"

    if not req_path.exists() or not req_path.read_text(encoding="utf-8").strip():
        req_path.write_text(EDITOR_HEADER, encoding="utf-8")

    if not non_interactive:
        result = subprocess.run([editor, str(req_path)])
        if result.returncode != 0:
            sys.exit(f"[prompts] El editor terminó con código {result.returncode}. Cancelado.")

    requerimiento = useful_requirement(req_path.read_text(encoding="utf-8"))
    if not requerimiento:
        suffix = " Usa --requirement <archivo> o edita _temps/REQUERIMIENTO.txt." if non_interactive else ""
        sys.exit(f"[prompts] El requerimiento quedó vacío. Cancelado.{suffix}")
    return requerimiento


def detect_technologies(cwd: Path) -> list[str]:
    technologies: list[str] = []

    if (cwd / "composer.json").is_file():
        technologies.append("PHP")
    if any((cwd / name).is_file() for name in ("package.json", "vite.config.js", "vite.config.ts")):
        technologies.append("JavaScript/TypeScript")
    if any((cwd / name).is_file() for name in ("pyproject.toml", "requirements.txt", "Pipfile", "setup.py")):
        technologies.append("Python")
    data_markers = (
        any(cwd.glob("*.sql"))
        or (cwd / "migrations").exists()
        or (cwd / "docker-compose.yml").is_file()
        or (cwd / "compose.yml").is_file()
    )
    if data_markers:
        technologies.append("MySQL/datos (confirmar motor real)")
    if any((cwd / name).is_file() for name in ("Makefile", "justfile")) or any(cwd.glob("*.sh")):
        technologies.append("scripting/automatización")

    package_path = cwd / "package.json"
    if package_path.is_file():
        try:
            package = json.loads(package_path.read_text(encoding="utf-8"))
            dependencies = {**package.get("dependencies", {}), **package.get("devDependencies", {})}
            if dependencies.keys() & {"react", "vue", "@angular/core", "svelte", "next", "nuxt"}:
                technologies.append("frontend web")
        except (json.JSONDecodeError, OSError):
            pass

    return list(dict.fromkeys(technologies)) or ["stack no detectado; inspeccionar manifiestos y configuración"]


def technology_profile(cwd: Path, requested: str) -> str:
    if requested != "auto":
        return requested
    return "auto: " + ", ".join(detect_technologies(cwd))


def build_consensus_run_id(proyecto: str, requerimiento: str, generated_at: str) -> str:
    payload = "\0".join((proyecto, requerimiento, generated_at)).encode("utf-8")
    return f"consensus-{hashlib.sha256(payload).hexdigest()[:16]}"


def render(
    section: str,
    proyecto: str,
    requerimiento: str,
    dev_phase: str,
    testing_phase: str,
    profile: str,
    generated_at: str,
    consensus_run_id: str = "consensus-direct-render",
) -> str:
    salida = section.replace("context_inicial_AAAA", f"context_inicial_{proyecto}")
    replacements = {
        "<DEV_PHASE>": dev_phase.upper(),
        "<TESTING_PHASE>": testing_phase.upper(),
        "<TECH_PROFILE>": profile,
        "<CONSENSUS_RUN_ID>": consensus_run_id,
        "<GENERATED_METADATA>": (
            f"proyecto={proyecto}; generado={generated_at}; "
            f"dev_phase={dev_phase}; testing_phase={testing_phase}; perfil={profile}; "
            f"consensus_run_id={consensus_run_id}"
        ),
    }
    for placeholder, value in replacements.items():
        salida = salida.replace(placeholder, value)

    unresolved = sorted(
        placeholder
        for placeholder in set(re.findall(r"<[A-Z_]+>", salida))
        if placeholder != "<REQUERIMIENTO>"
    )
    if unresolved:
        sys.exit(f"[prompts] Quedaron placeholders sin reemplazar: {', '.join(unresolved)}")
    return salida.replace("<REQUERIMIENTO>", requerimiento)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Genera prompts DEV, TESTING, TEST_EN_BROWSER, SINGLE_DEVELOPER, ANALISIS y "
            "ANALISIS_A/B en _temps/."
        )
    )
    parser.add_argument("--proyecto", help="Forzar nombre del proyecto (override de autodetección).")
    parser.add_argument(
        "--plantilla",
        type=Path,
        default=DEFAULT_TEMPLATE,
        help=f"Plantilla a usar (default: {DEFAULT_TEMPLATE}).",
    )
    parser.add_argument(
        "-r",
        "--requirement",
        "--requerimiento",
        "--archivo",
        type=Path,
        dest="requirement",
        help="Leer requerimiento desde un archivo; usar '-' para stdin.",
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="No abrir editor; reutilizar _temps/REQUERIMIENTO.txt o --requirement.",
    )
    parser.add_argument("--dev-phase", choices=DEV_PHASES, default="plan")
    parser.add_argument("--testing-phase", choices=TESTING_PHASES, default="baseline")
    parser.add_argument("--profile", choices=PROFILES, default="auto")
    args = parser.parse_args()

    cwd = Path.cwd()
    proyecto = detect_project(cwd, args.proyecto)
    sections = parse_template(args.plantilla)

    temps_dir = cwd / "_temps"
    creado_temps = not temps_dir.exists()
    temps_dir.mkdir(exist_ok=True)
    if creado_temps:
        print(f"[prompts] _temps/ no existía en {cwd}, lo creé.")

    requerimiento = read_requirement(temps_dir, args.requirement, args.non_interactive)
    profile = technology_profile(cwd, args.profile)
    generated_at = datetime.now().astimezone().isoformat(timespec="microseconds")
    consensus_run_id = build_consensus_run_id(proyecto, requerimiento, generated_at)

    def render_role(role: str) -> str:
        return render(
            sections[role],
            proyecto,
            requerimiento,
            args.dev_phase,
            args.testing_phase,
            profile,
            generated_at,
            consensus_run_id,
        )

    salidas = {
        "TESTING.txt": render_role("TESTING"),
        "DEV.txt": render_role("DEV"),
        "SINGLE_DEVELOPER.txt": render_role("SINGLE_DEVELOPER"),
        "REQUIERE_ANALISIS.txt": render_role("ANALISIS"),
    }
    if "TEST_EN_BROWSER" in sections:
        salidas["TEST_EN_BROWSER.txt"] = render_role("TEST_EN_BROWSER")
    if all(role in sections for role in CONSENSUS_PROMPT_SECTIONS):
        salidas.update(
            {
                "ANALISIS_A.txt": render_role("ANALISIS_A"),
                "ANALISIS_B.txt": render_role("ANALISIS_B"),
            }
        )
    for nombre, contenido in salidas.items():
        (temps_dir / nombre).write_text(contenido, encoding="utf-8")

    print(f"[prompts] proyecto detectado: {proyecto}")
    print(f"[prompts] perfil tecnológico: {profile}")
    print(f"[prompts] fases: DEV={args.dev_phase}, TESTING={args.testing_phase}")
    print(f"[prompts] generados en {temps_dir}:")
    for nombre in salidas:
        print(f"  - {nombre}")
    print()
    print("debes leer _temps/DEV.txt")
    print("debes leer _temps/TESTING.txt")
    if "TEST_EN_BROWSER.txt" in salidas:
        print("debes leer _temps/TEST_EN_BROWSER.txt")
    print("debes leer _temps/SINGLE_DEVELOPER.txt")
    print("debes leer _temps/REQUIERE_ANALISIS.txt")
    if "ANALISIS_A.txt" in salidas:
        print("debes leer _temps/ANALISIS_A.txt")
        print("debes leer _temps/ANALISIS_B.txt")


if __name__ == "__main__":
    main()
