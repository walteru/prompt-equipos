#!/usr/bin/env python3
"""Genera _temps/DEV.txt y _temps/TESTING.txt a partir de la plantilla maestra.

Uso:
    prompts                 # autodetecta el proyecto, abre $EDITOR para el requerimiento
    prompts --proyecto X    # fuerza el nombre del proyecto (en caso de ambigüedad)
    prompts --plantilla P   # usa otra plantilla en vez de inicial.txt

Requiere, en el directorio actual:
    - un archivo context_inicial_<proyecto>.txt
    - un directorio _temps/ (se crea si falta)
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_TEMPLATE = SCRIPT_DIR / "inicial.txt"

CONTEXT_GLOB = "context_inicial_*.txt"
CONTEXT_RE = re.compile(r"^context_inicial_(?P<name>.+)\.txt$")
SEPARATOR_RE = re.compile(r"^-{20,}\s*$", re.MULTILINE)

EDITOR_HEADER = """# Escribí abajo el requerimiento del sprint/iteración.
# Las líneas que empiezan con '#' se ignoran.
# Guardá y cerrá el editor para generar los prompts.
# Dejá el archivo vacío (o cerrá sin guardar) para cancelar.
#
# Este archivo (_temps/REQUERIMIENTO.txt) se conserva entre corridas:
# la próxima vez que ejecutes 'prompts' se abrirá con este contenido
# pre-cargado para que puedas editarlo o agregar cosas olvidadas.

"""


def detect_project(cwd: Path, override: str | None) -> str:
    if override:
        expected = cwd / f"context_inicial_{override}.txt"
        if not expected.is_file():
            sys.exit(
                f"[prompts] No existe {expected.name} en {cwd}. "
                "Verificá el nombre del proyecto."
            )
        return override

    candidates = sorted(
        p for p in cwd.glob(CONTEXT_GLOB) if CONTEXT_RE.match(p.name)
    )
    if not candidates:
        sys.exit(
            f"[prompts] No encontré ningún {CONTEXT_GLOB} en {cwd}. "
            "Ejecutá el comando dentro del directorio del proyecto."
        )
    if len(candidates) > 1:
        listado = "\n  - ".join(p.name for p in candidates)
        sys.exit(
            f"[prompts] Hay múltiples archivos context_inicial_*.txt:\n  - {listado}\n"
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
        if header in ("TESTING", "DEV"):
            sections[header] = parts[i + 1].rstrip() + "\n"
            i += 2
        else:
            i += 1

    missing = {"TESTING", "DEV"} - sections.keys()
    if missing:
        sys.exit(
            f"[prompts] La plantilla no tiene la(s) sección(es): {', '.join(sorted(missing))}. "
            "Revisá los separadores en inicial.txt."
        )
    return sections


def clean_requirement(contenido: str) -> str:
    lineas_utiles = [ln for ln in contenido.splitlines() if not ln.lstrip().startswith("#")]
    return "\n".join(lineas_utiles).strip()


def read_requirement_via_editor(temps_dir: Path) -> str:
    editor = os.environ.get("EDITOR") or os.environ.get("VISUAL") or "vim"
    req_path = temps_dir / "REQUERIMIENTO.txt"

    if not req_path.exists() or not req_path.read_text(encoding="utf-8").strip():
        req_path.write_text(EDITOR_HEADER, encoding="utf-8")

    result = subprocess.run([editor, str(req_path)])
    if result.returncode != 0:
        sys.exit(f"[prompts] El editor terminó con código {result.returncode}. Cancelado.")

    contenido = req_path.read_text(encoding="utf-8")
    requerimiento = clean_requirement(contenido)
    if not requerimiento:
        sys.exit("[prompts] El requerimiento quedó vacío. Cancelado.")
    return requerimiento


def render(section: str, proyecto: str, requerimiento: str) -> str:
    salida = section.replace("context_inicial_AAAA.txt", f"context_inicial_{proyecto}.txt")
    salida = salida.replace("<REQUERIMIENTO>", requerimiento)
    return salida


def main() -> None:
    parser = argparse.ArgumentParser(description="Genera prompts DEV y TESTING en _temps/.")
    parser.add_argument("--proyecto", help="Forzar nombre del proyecto (override de autodetección).")
    parser.add_argument(
        "--plantilla",
        type=Path,
        default=DEFAULT_TEMPLATE,
        help=f"Plantilla a usar (default: {DEFAULT_TEMPLATE}).",
    )
    parser.add_argument(
        "-r", "--requerimiento", "--archivo",
        type=Path,
        dest="requerimiento",
        help="Archivo desde el cual leer el requerimiento (modo no interactivo).",
    )
    args = parser.parse_args()

    cwd = Path.cwd()
    proyecto = detect_project(cwd, args.proyecto)
    sections = parse_template(args.plantilla)

    temps_dir = cwd / "_temps"
    creado_temps = not temps_dir.exists()
    temps_dir.mkdir(exist_ok=True)
    if creado_temps:
        print(f"[prompts] _temps/ no existía en {cwd}, lo creé.")

    if args.requerimiento:
        req_file = Path(args.requerimiento)
        if not req_file.is_file():
            sys.exit(f"[prompts] El archivo de requerimiento {req_file} no existe o no es un archivo.")
        try:
            contenido = req_file.read_text(encoding="utf-8")
        except Exception as e:
            sys.exit(f"[prompts] Error al leer el archivo {req_file}: {e}")

        requerimiento = clean_requirement(contenido)
        if not requerimiento:
            sys.exit("[prompts] El requerimiento está vacío o contiene solo comentarios. Cancelado.")

        try:
            (temps_dir / "REQUERIMIENTO.txt").write_text(contenido, encoding="utf-8")
        except Exception as e:
            print(f"[prompts] Advertencia: No se pudo guardar la caché del requerimiento: {e}")
    else:
        requerimiento = read_requirement_via_editor(temps_dir)

    salidas = {
        "TESTING.txt": render(sections["TESTING"], proyecto, requerimiento),
        "DEV.txt": render(sections["DEV"], proyecto, requerimiento),
    }
    for nombre, contenido in salidas.items():
        (temps_dir / nombre).write_text(contenido, encoding="utf-8")

    print(f"[prompts] proyecto detectado: {proyecto}")
    print(f"[prompts] generados en {temps_dir}:")
    for nombre in salidas:
        print(f"  - {nombre}")
    print()
    print("debes leer _temps/DEV.txt")
    print("debes leer _temps/TESTING.txt")


if __name__ == "__main__":
    main()
