#!/usr/bin/env python3
"""CLI interactiva para generar docs de Spec-Driven Development.

Uso rapido:
    sdd init
    sdd spec
    sdd plan
    sdd tasks
    sdd prompts
    sdd all
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

ROOT_MEMORY = Path(".specify") / "memory"
SPECS_DIR = Path("specs")
HARNESS_PROFILES = (
    "auto",
    "mixed",
    "php",
    "frontend",
    "javascript",
    "python",
    "mysql",
    "scripting",
)


@dataclass(frozen=True)
class Feature:
    number: int
    slug: str
    path: Path

    @property
    def name(self) -> str:
        return self.slug.replace("-", " ")


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "feature"


def heading(text: str) -> None:
    print(f"\n== {text} ==")


def prompt(label: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{label}{suffix}: ").strip()
    return value or default


def prompt_block(label: str, default: str = "") -> str:
    print(f"{label}")
    if default:
        print("(Enter para conservar valor actual, o escribi nuevo contenido. Termina con una linea con solo '.')")
        first = input("> ")
        if not first.strip():
            return default.strip()
        lines = [first]
    else:
        print("(Termina con una linea con solo '.')")
        lines = []

    while True:
        line = input("> ")
        if line.strip() == ".":
            break
        lines.append(line)
    return "\n".join(lines).strip()


def yes_no(label: str, default: bool = True) -> bool:
    marker = "S/n" if default else "s/N"
    value = input(f"{label} [{marker}]: ").strip().lower()
    if not value:
        return default
    return value in {"s", "si", "sí", "y", "yes"}


def bulletize(text: str) -> str:
    lines = [line.strip("-* \t") for line in text.splitlines() if line.strip()]
    if not lines:
        return "- Pendiente de definir."
    return "\n".join(f"- {line}" for line in lines)


def numbered_items(text: str) -> list[str]:
    items = [line.strip("-* \t") for line in text.splitlines() if line.strip()]
    return items or ["Pendiente de definir"]


def parse_task_dependencies(content: str, task_count: int) -> dict[int, list[int]]:
    dependencies = {index: [] for index in range(1, task_count + 1)}
    declared: set[int] = set()
    for raw_line in content.splitlines():
        line = raw_line.strip("-* \t")
        if not line:
            continue
        match = re.fullmatch(r"CA(?P<target>\d+)\s*:\s*(?P<blockers>.+)", line, re.IGNORECASE)
        if not match:
            sys.exit(
                "[sdd] Dependencia invalida. Usa el formato 'CA2: CA1' o deja el bloque vacio."
            )

        target = int(match["target"])
        if target not in dependencies:
            sys.exit(f"[sdd] La dependencia refiere a CA{target}, que no existe.")
        if target in declared:
            sys.exit(f"[sdd] CA{target} tiene mas de una linea de dependencias.")
        declared.add(target)

        blocker_ids = [int(value) for value in re.findall(r"\bCA(\d+)\b", match["blockers"], re.IGNORECASE)]
        if not blocker_ids and match["blockers"].strip().lower() not in {
            "ninguna",
            "ninguno",
            "none",
        }:
            sys.exit(f"[sdd] CA{target} no contiene bloqueantes CA validos.")
        if target in blocker_ids:
            sys.exit(f"[sdd] CA{target} no puede bloquearse a si misma.")
        unknown = [blocker for blocker in blocker_ids if blocker not in dependencies]
        if unknown:
            sys.exit(f"[sdd] La dependencia refiere a CA{unknown[0]}, que no existe.")
        dependencies[target] = list(dict.fromkeys(blocker_ids))

    visiting: set[int] = set()
    visited: set[int] = set()

    def visit(task: int) -> None:
        if task in visiting:
            sys.exit("[sdd] Las dependencias entre criterios contienen un ciclo.")
        if task in visited:
            return
        visiting.add(task)
        for blocker in dependencies[task]:
            visit(blocker)
        visiting.remove(task)
        visited.add(task)

    for task in dependencies:
        visit(task)
    return dependencies


def technology_profile(root: Path, requested: str) -> str:
    if requested != "auto":
        return requested

    detected: list[str] = []
    markers = (
        ("PHP", ("composer.json",)),
        ("JavaScript/TypeScript", ("package.json", "vite.config.js", "vite.config.ts")),
        ("Python", ("pyproject.toml", "requirements.txt", "Pipfile", "setup.py")),
        ("scripting/automatizacion", ("Makefile", "justfile")),
    )
    for technology, names in markers:
        if any((root / name).is_file() for name in names):
            detected.append(technology)
    if (
        any(root.glob("*.sql"))
        or (root / "migrations").exists()
        or (root / "docker-compose.yml").is_file()
        or (root / "compose.yml").is_file()
    ):
        detected.append("MySQL/datos (confirmar motor real)")
    if any(root.glob("*.sh")) and "scripting/automatizacion" not in detected:
        detected.append("scripting/automatizacion")

    summary = ", ".join(detected) if detected else "stack no detectado; inspeccionar proyecto"
    return f"auto: {summary}"


def ensure_dirs() -> None:
    ROOT_MEMORY.mkdir(parents=True, exist_ok=True)
    SPECS_DIR.mkdir(exist_ok=True)


def feature_dirs() -> list[Feature]:
    if not SPECS_DIR.exists():
        return []

    features: list[Feature] = []
    for path in SPECS_DIR.iterdir():
        if not path.is_dir():
            continue
        match = re.match(r"^(?P<num>\d{3})-(?P<slug>.+)$", path.name)
        if match:
            features.append(
                Feature(
                    number=int(match["num"]),
                    slug=match["slug"],
                    path=path,
                )
            )
    return sorted(features, key=lambda item: item.number)


def next_feature_number() -> int:
    features = feature_dirs()
    return features[-1].number + 1 if features else 1


def resolve_feature(value: str | None) -> Feature:
    features = feature_dirs()
    if not features:
        sys.exit("[sdd] No hay features en specs/. Ejecuta primero: sdd spec")

    if not value:
        return features[-1]

    lowered = value.lower()
    for feature in features:
        if (
            value == f"{feature.number:03d}"
            or lowered == feature.slug
            or lowered in feature.path.name.lower()
        ):
            return feature

    available = "\n  - ".join(feature.path.name for feature in features)
    sys.exit(f"[sdd] No encontre la feature '{value}'. Disponibles:\n  - {available}")


def read_section(path: Path, heading_name: str) -> str:
    if not path.is_file():
        return ""
    raw = path.read_text(encoding="utf-8")
    pattern = re.compile(
        rf"^## {re.escape(heading_name)}\s*$\n(?P<body>.*?)(?=^## |\Z)",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(raw)
    return match["body"].strip() if match else ""


def write_file(path: Path, content: str, force: bool) -> None:
    if path.exists() and not force:
        if not yes_no(f"[sdd] {path} ya existe. Sobrescribir?", False):
            print(f"[sdd] Conservado: {path}")
            return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")
    print(f"[sdd] generado: {path}")


def command_init(args: argparse.Namespace) -> None:
    ensure_dirs()
    target = ROOT_MEMORY / "constitution.md"

    heading("Constitucion del proyecto")
    project = prompt("Nombre del proyecto", Path.cwd().name)
    purpose = prompt_block("Proposito del producto/proyecto:")
    principles = prompt_block(
        "Principios no negociables del equipo, uno por linea:",
        "Alcance explicito antes de implementar\nTests proporcionales al riesgo\nCambios pequenos y revisables",
    )
    standards = prompt_block(
        "Estandares tecnicos esperados, uno por linea:",
        "Respetar patrones existentes\nNo agregar complejidad no pedida\nDocumentar decisiones no obvias",
    )
    workflow = prompt_block(
        "Flujo de trabajo esperado, uno por linea:",
        "Spec antes de plan\nPlan antes de tasks\nTasks antes de implementacion",
    )

    content = f"""# Constitucion: {project}

Fecha: {date.today().isoformat()}

## Proposito

{purpose or "Pendiente de definir."}

## Principios

{bulletize(principles)}

## Estandares Tecnicos

{bulletize(standards)}

## Flujo De Trabajo

{bulletize(workflow)}

## Criterio De Cierre

- La implementacion cumple la especificacion vigente.
- Los criterios de aceptacion tienen validacion suficiente.
- Los riesgos residuales quedan explicitados.
- El trabajo fuera de alcance queda separado como seguimiento opcional.
"""
    write_file(target, content, args.force)


def command_spec(args: argparse.Namespace) -> None:
    ensure_dirs()

    heading("Nueva especificacion")
    title = prompt("Nombre corto de la feature")
    if not title:
        sys.exit("[sdd] El nombre de la feature es obligatorio.")

    number = args.number or next_feature_number()
    slug = slugify(title)
    feature = Feature(number=number, slug=slug, path=SPECS_DIR / f"{number:03d}-{slug}")

    problem = prompt_block("Problema u oportunidad que resuelve:")
    users = prompt_block("Usuarios, roles o sistemas afectados, uno por linea:")
    goals = prompt_block("Objetivos de negocio/producto, uno por linea:")
    scope_in = prompt_block("Alcance incluido, uno por linea:")
    scope_out = prompt_block("Fuera de alcance, uno por linea:")
    main_flow = prompt_block("Flujo principal esperado:")
    rules = prompt_block("Reglas de negocio, restricciones o invariantes, uno por linea:")
    edge_cases = prompt_block("Casos borde relevantes, uno por linea:")
    acceptance = prompt_block("Criterios de aceptacion verificables, uno por linea:")
    questions = prompt_block("Dudas abiertas o supuestos, uno por linea:")

    content = f"""# Spec: {title}

Feature: {feature.path.name}
Fecha: {date.today().isoformat()}
Estado: Draft

## Problema

{problem or "Pendiente de definir."}

## Usuarios Y Actores

{bulletize(users)}

## Objetivos

{bulletize(goals)}

## Alcance Incluido

{bulletize(scope_in)}

## Fuera De Alcance

{bulletize(scope_out)}

## Flujo Principal

{main_flow or "Pendiente de definir."}

## Reglas De Negocio

{bulletize(rules)}

## Casos Borde

{bulletize(edge_cases)}

## Criterios De Aceptacion

{bulletize(acceptance)}

## Dudas Y Supuestos

{bulletize(questions)}
"""
    write_file(feature.path / "spec.md", content, args.force)


def command_plan(args: argparse.Namespace) -> None:
    feature = resolve_feature(args.feature)
    spec_path = feature.path / "spec.md"

    heading(f"Plan tecnico para {feature.path.name}")
    context = prompt_block("Contexto tecnico relevante:")
    architecture = prompt_block("Diseño propuesto o zonas probables de cambio:")
    data = prompt_block("Datos, migraciones, contratos o integraciones afectadas:")
    validation = prompt_block("Estrategia de validacion y TDD:")
    risks = prompt_block("Riesgos tecnicos, uno por linea:")
    rollout = prompt_block("Despliegue, rollback o compatibilidad:")

    content = f"""# Plan: {feature.name}

Feature: {feature.path.name}
Fecha: {date.today().isoformat()}
Spec: ./spec.md

## Resumen De La Spec

{read_section(spec_path, "Problema") or "Ver spec.md."}

## Contexto Tecnico

{context or "Pendiente de definir."}

## Diseno Propuesto

{architecture or "Pendiente de definir."}

## Datos E Integraciones

{data or "Sin impacto identificado."}

## Estrategia De Validacion

{validation or "Pendiente de definir."}

## Riesgos

{bulletize(risks)}

## Despliegue Y Compatibilidad

{rollout or "Pendiente de definir."}
"""
    write_file(feature.path / "plan.md", content, args.force)


def command_tasks(args: argparse.Namespace) -> None:
    feature = resolve_feature(args.feature)
    spec_path = feature.path / "spec.md"
    acceptance = numbered_items(read_section(spec_path, "Criterios De Aceptacion"))

    heading(f"Tareas para {feature.path.name}")
    extra = prompt_block("Tareas adicionales necesarias, una por linea:")
    extra_items = numbered_items(extra) if extra else []
    dependency_text = prompt_block(
        "Dependencias reales entre criterios, una por linea (ejemplo: CA2: CA1). "
        "Deja vacio si pueden comenzar de forma independiente:"
    )
    dependencies = parse_task_dependencies(dependency_text, len(acceptance))

    lines = [
        f"# Tasks: {feature.name}",
        "",
        f"Feature: {feature.path.name}",
        f"Fecha: {date.today().isoformat()}",
        "Spec: ./spec.md",
        "Plan: ./plan.md",
        "",
        "## Checklist",
        "",
        "- [ ] Confirmar que la spec no tiene ambiguedades bloqueantes.",
        "- [ ] Revisar el plan tecnico contra la arquitectura existente.",
        "- [ ] Definir validacion minima antes de implementar.",
    ]

    lines.extend(
        [
            "",
            "## Slices Verticales Por Criterio De Aceptacion",
            "",
            "Cada slice debe entregar un camino angosto pero completo y verificable. No la dividas por capas.",
        ]
    )
    for index, item in enumerate(acceptance, 1):
        blockers = dependencies[index]
        blocked_by = ", ".join(f"CA{blocker}" for blocker in blockers) or "Ninguna"
        lines.extend(
            [
                "",
                f"### CA{index}",
                "",
                f"**Que entrega:** {item}",
                "",
                f"**Bloqueada por:** {blocked_by}",
                "",
                "- [ ] Implementar el comportamiento end-to-end minimo para este criterio.",
                "- [ ] Validar el criterio a traves de la interfaz publica o seam mas alto viable.",
            ]
        )

    if extra_items:
        lines.extend(["", "## Tareas Tecnicas Adicionales", ""])
        for item in extra_items:
            lines.append(f"- [ ] {item}")

    lines.extend(
        [
            "",
            "## Cierre",
            "",
            "- [ ] Tests o validaciones ejecutadas y documentadas.",
            "- [ ] Riesgos residuales explicitados.",
            "- [ ] Seguimiento opcional separado del alcance actual.",
        ]
    )

    write_file(feature.path / "tasks.md", "\n".join(lines), args.force)


def build_consensus_run_id(feature: Feature, generated_at: str) -> str:
    source_paths = (
        ROOT_MEMORY / "constitution.md",
        feature.path / "spec.md",
        feature.path / "plan.md",
        feature.path / "tasks.md",
    )
    parts = [feature.path.name, generated_at]
    for path in source_paths:
        parts.append(path.as_posix())
        if path.is_file():
            parts.append(path.read_text(encoding="utf-8"))
    payload = "\0".join(parts).encode("utf-8")
    return f"consensus-{hashlib.sha256(payload).hexdigest()[:16]}"


def render_prompt(
    role: str,
    feature: Feature,
    dev_phase: str = "plan",
    testing_phase: str = "baseline",
    profile: str = "auto",
    consensus_run_id: str | None = None,
) -> str:
    role_upper = role.upper()
    if consensus_run_id is None:
        consensus_run_id = build_consensus_run_id(feature, "direct-render")
    consensus_dir = f"./specs/{feature.path.name}/prompts"
    consensus_protocol = ""
    if role == "SINGLE_DEVELOPER":
        mission = (
            "Modalidad autonoma: analiza, implementa, valida y auto-revisa el alcance de punta a punta. "
            "Cambios autorizados dentro de la spec. No te detengas despues de presentar un plan ni "
            "esperes handoffs de DEV o TESTING: completa la implementacion segura y razonable salvo "
            "bloqueo real."
        )
        phase_state = "Fases coordinadas DEV/TESTING: NO APLICAN para este rol."
    elif role == "DEV":
        mission = {
            "plan": "Fase PLAN: analiza y propone sin modificar archivos.",
            "implement": "Fase IMPLEMENT: implementa y valida el cambio minimo dentro de la spec.",
        }[dev_phase]
        phase_state = f"Fase DEV: {dev_phase.upper()}"
    elif role == "TESTING":
        mission = {
            "baseline": "Fase BASELINE: crea una linea base independiente sin modificar archivos.",
            "review": (
                "Fase REVIEW: revisa la entrega real de DEV, el diff, los tests y sus resultados "
                "sin modificar archivos."
            ),
        }[testing_phase]
        phase_state = f"Fase TESTING: {testing_phase.upper()}"
    elif role == "TEST_EN_BROWSER":
        mission = (
            "Modalidad TEST EN BROWSER: valida la spec como una persona usuaria en una instancia "
            "real de Chrome/Chromium mediante Chrome DevTools, Playwright u otra herramienta de "
            "browser disponible. Debes abrir y usar un navegador real; inspeccion estatica, tests "
            "unitarios, requests HTTP, curl o una simulacion DOM no sustituyen esta validacion. "
            "No modifiques ni corrijas el producto."
        )
        phase_state = "Fases coordinadas DEV/TESTING: NO APLICAN para este rol."
    elif role == "ANALISIS_A":
        mission = (
            "Modalidad ANALISIS CONSENSUADO A: crea una linea base independiente y, "
            "cuando el coordinador habilite el contraste, compara el resultado de B y "
            "consolida ANALISIS_UNIFICADO.md. No implementes ni fabriques consenso."
        )
        phase_state = "Fases coordinadas DEV/TESTING: NO APLICAN para este rol."
        consensus_protocol = f"""
Protocolo de consenso:

1. INDEPENDIENTE: no leas `{consensus_dir}/ANALISIS_B_RESULTADO.md` ni el documento unificado. Entrega tu interpretacion y emite BASELINE_A_READY con el CONSENSUS_RUN_ID.
2. CONTRASTE: solo con autorizacion del coordinador, compara el resultado B que tenga el mismo identificador. Si retomaste en una conversacion nueva, recupera tambien tu propio resultado A de esta ronda.
3. CONSOLIDACION: crea o actualiza `{consensus_dir}/ANALISIS_UNIFICADO.md` solo con autorizacion expresa. Inclui interpretacion, objetivos, fuera de alcance, criterios y ejemplos, supuestos, dependencias, restricciones, riesgos, evidencia, matriz de trazabilidad, validaciones A/B y conclusion READY_FOR_PLANNING o NEEDS_CLARIFICATION. Emite CONSENSUS_REVIEW_READY.
4. AJUSTE: ante CONSENSUS_CHANGES_REQUESTED de la misma ronda, evalua cada observacion, actualiza el documento y repite CONSENSUS_REVIEW_READY.
5. CIERRE: solo CONSENSUS_READY de B para esta ronda permite finalizar el documento, registrar las validaciones A/B, cambiar COINCIDENTE a ACORDADO donde corresponda y marcar COMPLETE. Usa EXTERNAL_CLARIFICATION_REQUIRED si una decision imprescindible no puede resolverse mediante inspeccion.
"""
    elif role == "ANALISIS_B":
        mission = (
            "Modalidad ANALISIS CONSENSUADO B: crea una linea base independiente y, "
            "cuando el coordinador habilite el contraste, actua como contraparte y valida "
            "ANALISIS_UNIFICADO.md. No implementes ni aceptes por preferencia."
        )
        phase_state = "Fases coordinadas DEV/TESTING: NO APLICAN para este rol."
        consensus_protocol = f"""
Protocolo de consenso:

1. INDEPENDIENTE: no leas `{consensus_dir}/ANALISIS_A_RESULTADO.md` ni el documento unificado. Entrega tu interpretacion y emite BASELINE_B_READY con el CONSENSUS_RUN_ID.
2. CONTRASTE: solo con autorizacion del coordinador, compara el resultado A que tenga el mismo identificador. Si retomaste en una conversacion nueva, recupera tambien tu propio resultado B de esta ronda.
3. VALIDACION: ante CONSENSUS_REVIEW_READY de la misma ronda, revisa `{consensus_dir}/ANALISIS_UNIFICADO.md` completo, incluida su matriz de trazabilidad, las validaciones A/B y la conclusion. Emite CONSENSUS_READY si representa fielmente coincidencias, supuestos, pendientes y desacuerdos. De lo contrario emite CONSENSUS_CHANGES_REQUESTED con afirmacion afectada, evidencia, impacto y cambio concreto.
4. CIERRE: no bloquees por redaccion sin impacto. Usa EXTERNAL_CLARIFICATION_REQUIRED solo si una decision imprescindible no puede resolverse mediante inspeccion.
"""
    else:
        mission = (
            "Modalidad ANALISIS: investiga y recomienda sin modificar archivos, dependencias ni datos. "
            "No requiere fases, handoffs ni autorizaciones posteriores. Si falta informacion no "
            "bloqueante, declara el limite de la evidencia y concluye igualmente."
        )
        phase_state = "Fases coordinadas DEV/TESTING: NO APLICAN para este rol."

    output_formats = {
        "DEV": """FASE: PLAN | IMPLEMENT
CRITERIOS DE ACEPTACION: ...
PLAN / IMPLEMENTACION: ...
TESTS Y COMANDOS: ...
RIESGOS Y SUPUESTOS: ...
SEGUIMIENTO OPCIONAL / FUERA DE ALCANCE: ...
ESTADO: PLAN_COMPLETE | COMPLETE | PARTIAL_AUTHORIZED | BLOCKED""",
        "TESTING": """FASE: BASELINE | REVIEW
CRITERIOS DE ACEPTACION: ...
CUMPLIMIENTO DE LA SPEC: ...
ESTANDARES Y DISENO: ...
HALLAZGOS: severidad; evidencia; impacto; accion necesaria
EVIDENCIA Y VALIDACION: ...
RIESGOS Y CASOS BORDE: ...
SEGUIMIENTO OPCIONAL / FUERA DE ALCANCE: ...
ESTADO: BASELINE_COMPLETE | COMPLETE | BLOCKED""",
        "TEST_EN_BROWSER": """RESUMEN: ...
BROWSER: herramienta; version; HEADED | HEADLESS | REMOTO; URL; viewport
ESCENARIOS: pasos de usuario; esperado; observado; PASS | FAIL | BLOCKED
EVIDENCIA: screenshots/traces/videos; consola; red; otros datos verificables
HALLAZGOS: severidad; reproduccion; evidencia; impacto; accion sugerida
LIMITES DE LA VALIDACION: ...
SEGUIMIENTO OPCIONAL / FUERA DE ALCANCE: ...
ESTADO: COMPLETE | FAILED | BLOCKED""",
        "SINGLE_DEVELOPER": """CRITERIOS DE ACEPTACION: ...
IMPLEMENTACION: ...
TESTS Y VALIDACION: ...
AUTO-REVISION: ...
RIESGOS Y LIMITACIONES: ...
SEGUIMIENTO OPCIONAL / FUERA DE ALCANCE: ...
ESTADO: COMPLETE | PARTIAL_AUTHORIZED | BLOCKED""",
        "ANALISIS": """RESUMEN: ...
EVIDENCIA REVISADA: ...
DIAGNOSTICO: hechos; hipotesis; informacion faltante
IMPACTO, RIESGOS Y ALTERNATIVAS: ...
RECOMENDACION Y PROXIMOS PASOS: ...
SEGUIMIENTO OPCIONAL / FUERA DE ALCANCE: ...
ESTADO: ANALYSIS_COMPLETE | BLOCKED""",
        "ANALISIS_A": f"""CONSENSUS_RUN_ID: {consensus_run_id}
RONDA: INDEPENDIENTE | CONTRASTE | CONSOLIDACION | AJUSTE | CIERRE
HANDOFF: BASELINE_A_READY | CONSENSUS_REVIEW_READY | EXTERNAL_CLARIFICATION_REQUIRED | NONE
INTERPRETACION, ALCANCE Y CRITERIOS: ...
EVIDENCIA, SUPUESTOS Y DIFERENCIAS: ...
DOCUMENTO UNIFICADO: no realizado | propuesto | actualizado | validado
ESTADO: BASELINE_COMPLETE | CONSOLIDATING | COMPLETE | BLOCKED""",
        "ANALISIS_B": f"""CONSENSUS_RUN_ID: {consensus_run_id}
RONDA: INDEPENDIENTE | CONTRASTE | VALIDACION | CIERRE
HANDOFF: BASELINE_B_READY | CONSENSUS_READY | CONSENSUS_CHANGES_REQUESTED | EXTERNAL_CLARIFICATION_REQUIRED | NONE
INTERPRETACION, ALCANCE Y CRITERIOS: ...
EVIDENCIA, SUPUESTOS Y DIFERENCIAS: ...
REVISION DEL DOCUMENTO UNIFICADO: no realizada | aprobada | cambios solicitados
ESTADO: BASELINE_COMPLETE | REVIEW_COMPLETE | COMPLETE | BLOCKED""",
    }
    consensus_state = (
        f"CONSENSUS_RUN_ID: {consensus_run_id}"
        if role in ("ANALISIS_A", "ANALISIS_B")
        else ""
    )

    return f"""# Prompt {role_upper}: {feature.name}

Debes leer estas fuentes desde la raiz del proyecto:

1. ./.specify/memory/constitution.md
2. ./specs/{feature.path.name}/spec.md
3. ./specs/{feature.path.name}/plan.md
4. ./specs/{feature.path.name}/tasks.md

Rol: {role_upper}
Perfil tecnologico: {profile}
{phase_state}
{consensus_state}

{mission}
{consensus_protocol}

Reglas:

- Trabaja y valida solamente en local. No hagas push, merge remoto, tags, releases, publicaciones, promociones de entorno, migraciones en produccion ni deploy sin una peticion explicita y directa del usuario para el entorno indicado.
- Cuando el rol y la fase autoricen cambios, prefiere la rama local `dev` despues de inspeccionar rama y estado. Si cambiarla o crearla puede afectar trabajo preexistente, conserva una rama local segura y reporta la excepcion.
- No crees commits, no hagas amend, rebase ni modifiques el historial sin una instruccion explicita del usuario. Si autoriza un commit, inspecciona estado y diff, incluye solo archivos del alcance vigente y reporta el hash resultante.
- La spec define el comportamiento esperado.
- El plan explica la estrategia tecnica, pero no puede ampliar alcance por si mismo.
- Las tasks ordenan el trabajo; si contradicen la spec, reporta la contradiccion.
- No conviertas dudas, riesgos o seguimiento opcional en alcance automatico.
- Si falta una decision de negocio bloqueante, pregunta antes de implementar.
- Si existe un supuesto tecnico razonable y reversible, declaralo y avanza segun tu rol.
- Mantene separado: cumplimiento del requerimiento, riesgos, mejoras opcionales y fuera de alcance.
- Inspecciona manifiestos, lockfiles, configuracion y scripts antes de asumir stack, versiones o comandos.
- Adapta la validacion al proyecto real: PHP; JavaScript/TypeScript y frontend; Python; MySQL/datos; scripting; integraciones.
- Preserva cambios preexistentes. No reviertas, reformatees ni sobrescribas trabajo ajeno.
- No operes sobre datos o servicios no confirmados como aislados y seguros.
- Reporta solo comandos realmente ejecutados y sus resultados; no ocultes fallos.
- En ANALISIS, TESTING o DEV/PLAN, evita comandos que puedan escribir caches, artefactos o datos.
- En DEV/IMPLEMENT y SINGLE_DEVELOPER, prueba comportamiento a traves de interfaces publicas o del seam mas alto viable. Usa resultados esperados independientes de la implementacion y mocks solo en limites externos cuando sea posible. Para funcionalidad nueva, avanza en slices verticales pequenos: un comportamiento verificable, implementacion minima y validacion antes del siguiente.
- En DEV/IMPLEMENT y SINGLE_DEVELOPER, ante un bug dificil o intermitente, antes de formular una solucion construye y ejecuta un loop que detecte el sintoma exacto; minimiza el caso; plantea de 3 a 5 hipotesis falsables y prueba una variable por vez. Etiqueta la instrumentacion temporal con un prefijo unico, convierte la reproduccion en regresion en un seam adecuado cuando exista, verifica el escenario original y elimina la instrumentacion antes de cerrar. Si no puedes construir el loop, reporta que acceso o artefacto redactado falta en vez de adivinar.
- En REVIEW, usa la entrega de DEV, el diff, los tests y los comandos como evidencia; declara lo que falte. Separa CUMPLIMIENTO DE LA SPEC (criterios omitidos, parciales, incorrectos o alcance agregado) de ESTANDARES Y DISENO (convenciones documentadas, mantenibilidad y smells relevantes como juicio). Ningun eje compensa fallos del otro. Identifica el punto base del diff si puede resolverse; si no, declara exactamente que comparaste.
- En REVIEW, verifica tests proporcionales al riesgo a traves de interfaces publicas o del seam mas alto viable, valores esperados independientes y mocks limitados a limites externos cuando sea posible. Para bugs dificiles, exige evidencia del loop previo al fix, regresion cuando exista un seam adecuado, verificacion del escenario original y ausencia de instrumentacion temporal.
- En TEST_EN_BROWSER, inspecciona scripts y documentacion para descubrir como iniciar la aplicacion, URL, credenciales de prueba y tooling existente; no inventes comandos ni secretos.
- En TEST_EN_BROWSER, prioriza browser HEADED/visible si el entorno ofrece escritorio o browser conectado. Si solo hay HEADLESS o REMOTO, puedes usarlo salvo que la spec exija observar una ventana; declara el modo exacto.
- En TEST_EN_BROWSER, recorre por UI los pasos funcionales y verifica resultado visible, navegacion, consola y red. No saltees por API pasos que sean parte del criterio.
- En TEST_EN_BROWSER, usa solo entorno, cuentas y datos confirmados como seguros. No ejecutes pagos, mensajes, publicaciones, emails ni acciones destructivas o persistentes sin esa confirmacion.
- En TEST_EN_BROWSER, reporta herramienta/version, modo, URL, escenarios y evidencia. No declares COMPLETE sin una sesion real de browser ni sustituyas silenciosamente el browser por otro test. Si falta browser, URL o autenticacion imprescindible, usa BLOCKED con el impedimento exacto.
- En TEST_EN_BROWSER, puedes iniciar procesos locales y generar evidencia temporal, pero no modificar codigo, configuracion, dependencias ni datos reales. No llames manual a una prueba automatizada ni visible a una sesion headless/remota.
- Siempre que uses Chrome DevTools, Playwright u otra automatizacion de navegador, incluido el acceso mediante MCP, antes de emitir la salida final cierra por completo todas las instancias que hayas abierto o controlado para las pruebas, incluso ante fallos o bloqueos. Cerrar pestañas o dejar una ventana abierta en `about:blank` o `blank` no cuenta como cierre: usa el cierre total de la herramienta y verifica que no queden ventanas ni procesos de prueba abiertos. No cierres instancias preexistentes ajenas a la prueba.
- En ANALISIS_A/B, la primera ronda es independiente: no leas el resultado del otro equipo hasta que el coordinador habilite el contraste.
- En ANALISIS_A/B, no implementes ni modifiques codigo, configuracion, dependencias o datos. A solo puede escribir el documento unificado cuando el coordinador lo autorice expresamente.
- En ANALISIS_A/B, rechaza artefactos y handoffs cuyo CONSENSUS_RUN_ID no coincida o no sea verificable; nunca mezcles rondas.
- En ANALISIS_A/B, clasifica el borrador como COINCIDENTE, SUPUESTO, PENDIENTE o DESACUERDO. Usa ACORDADO solo despues de CONSENSUS_READY. A consolida y B valida con CONSENSUS_READY o CONSENSUS_CHANGES_REQUESTED.
- En ANALISIS_A/B, usa EXTERNAL_CLARIFICATION_REQUIRED solo para una decision imprescindible que la inspeccion no pueda resolver.

Formato esperado:

{role.lower()}:

{output_formats[role]}
"""


def command_prompts(args: argparse.Namespace) -> None:
    feature = resolve_feature(args.feature)
    prompts_dir = feature.path / "prompts"
    profile = technology_profile(Path.cwd(), args.profile)
    generated_at = datetime.now().astimezone().isoformat(timespec="microseconds")
    consensus_run_id = build_consensus_run_id(feature, generated_at)
    for role in (
        "DEV",
        "TESTING",
        "TEST_EN_BROWSER",
        "SINGLE_DEVELOPER",
        "ANALISIS",
        "ANALISIS_A",
        "ANALISIS_B",
    ):
        content = render_prompt(
            role,
            feature,
            dev_phase=args.dev_phase,
            testing_phase=args.testing_phase,
            profile=profile,
            consensus_run_id=consensus_run_id,
        )
        write_file(prompts_dir / f"{role}.txt", content, args.force)


def command_all(args: argparse.Namespace) -> None:
    if not (ROOT_MEMORY / "constitution.md").exists():
        command_init(args)
    command_spec(args)
    feature = resolve_feature(None)
    args.feature = feature.path.name
    command_plan(args)
    command_tasks(args)
    command_prompts(args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sdd",
        description="Genera documentos y prompts de Spec-Driven Development.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_common(subparser: argparse.ArgumentParser) -> None:
        subparser.add_argument("--force", action="store_true", help="Sobrescribir archivos existentes.")

    init_parser = subparsers.add_parser("init", help="Crear .specify/memory/constitution.md")
    add_common(init_parser)
    init_parser.set_defaults(func=command_init)

    spec_parser = subparsers.add_parser("spec", help="Crear specs/NNN-feature/spec.md")
    add_common(spec_parser)
    spec_parser.add_argument("--number", type=int, help="Numero de feature a usar.")
    spec_parser.set_defaults(func=command_spec)

    plan_parser = subparsers.add_parser("plan", help="Crear plan.md para una feature.")
    add_common(plan_parser)
    plan_parser.add_argument("--feature", help="Numero, slug o nombre de directorio de feature.")
    plan_parser.set_defaults(func=command_plan)

    tasks_parser = subparsers.add_parser("tasks", help="Crear tasks.md para una feature.")
    add_common(tasks_parser)
    tasks_parser.add_argument("--feature", help="Numero, slug o nombre de directorio de feature.")
    tasks_parser.set_defaults(func=command_tasks)

    def add_harness_options(subparser: argparse.ArgumentParser) -> None:
        subparser.add_argument("--dev-phase", choices=("plan", "implement"), default="plan")
        subparser.add_argument("--testing-phase", choices=("baseline", "review"), default="baseline")
        subparser.add_argument(
            "--profile",
            choices=HARNESS_PROFILES,
            default="auto",
        )

    prompts_parser = subparsers.add_parser(
        "prompts",
        help="Crear prompts DEV/TESTING/TEST_EN_BROWSER/SINGLE_DEVELOPER/ANALISIS/ANALISIS_A/B.",
    )
    add_common(prompts_parser)
    add_harness_options(prompts_parser)
    prompts_parser.add_argument("--feature", help="Numero, slug o nombre de directorio de feature.")
    prompts_parser.set_defaults(func=command_prompts)

    all_parser = subparsers.add_parser("all", help="Ejecutar init si hace falta, spec, plan, tasks y prompts.")
    add_common(all_parser)
    add_harness_options(all_parser)
    all_parser.add_argument("--number", type=int, help="Numero de feature a usar.")
    all_parser.set_defaults(func=command_all)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
