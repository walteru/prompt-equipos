import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("prompts_module", ROOT / "prompts.py")
assert SPEC and SPEC.loader
prompts = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(prompts)


class PromptGeneratorTest(unittest.TestCase):
    def test_master_template_has_all_roles(self) -> None:
        sections = prompts.parse_template(ROOT / "inicial.txt")
        self.assertEqual(set(prompts.PROMPT_SECTIONS), set(sections))

    def test_all_roles_are_local_first_and_forbid_implicit_deploys(self) -> None:
        sections = prompts.parse_template(ROOT / "inicial.txt")

        for role, section in sections.items():
            with self.subTest(role=role):
                self.assertIn("todo requerimiento se trabaja y valida solamente en el entorno local", section)
                self.assertIn("usa preferentemente la rama local `dev`", section)
                self.assertIn("Nunca ejecutes un deploy", section)
                self.assertIn("sin una peticion explicita y directa del usuario", section)
                self.assertIn("scripts de deploy", section)
                self.assertIn("sin realizarlo", section)
                self.assertIn("No crees commits", section)
                self.assertIn("sin una instruccion explicita del usuario", section)
                self.assertIn("incluye solo archivos del alcance vigente", section)
                self.assertIn("reporta el hash resultante", section)

    def test_all_roles_treat_context_formats_without_priority(self) -> None:
        sections = prompts.parse_template(ROOT / "inicial.txt")

        for role, section in sections.items():
            with self.subTest(role=role):
                self.assertIn(
                    "sea .txt, .md o ambos, sin prioridad por extension",
                    section,
                )
                self.assertNotIn("complemento o fallback", section)
                self.assertNotIn("contexto principal", section)

    def test_coordinated_roles_define_conversational_phase_handoffs(self) -> None:
        sections = prompts.parse_template(ROOT / "inicial.txt")

        self.assertIn("instantanea generada, no un archivo de estado vivo", sections["DEV"])
        self.assertIn("no solicites una actualizacion de `_temps/DEV.txt`", sections["DEV"])
        self.assertIn("DEV_IMPLEMENT_READY", sections["DEV"])
        self.assertIn("TESTING_REVIEW_READY", sections["DEV"])

        self.assertIn("instantanea generada, no un archivo de estado vivo", sections["TESTING"])
        self.assertIn("no pidas que lo editen o regeneren", sections["TESTING"])
        self.assertIn("DEV_IMPLEMENT_READY", sections["TESTING"])
        self.assertIn("TESTING_REVIEW_READY", sections["TESTING"])

    def test_single_developer_is_authorized_to_complete_without_handoffs(self) -> None:
        section = prompts.parse_template(ROOT / "inicial.txt")["SINGLE_DEVELOPER"]

        self.assertIn("ejecucion autonoma de punta a punta", section)
        self.assertIn("Cambios autorizados: SI", section)
        self.assertIn("No te detengas despues de presentar un plan", section)
        self.assertIn("no requiere handoffs ni autorizaciones de DEV o TESTING", section)
        self.assertIn("Declara supuestos tecnicos razonables y reversibles y avanza", section)

    def test_implementation_roles_use_behavioral_tests_and_disciplined_debugging(self) -> None:
        sections = prompts.parse_template(ROOT / "inicial.txt")

        for role in ("DEV", "SINGLE_DEVELOPER"):
            with self.subTest(role=role):
                section = sections[role]
                self.assertIn("interfaces publicas o del seam mas alto viable", section)
                self.assertIn("resultados esperados independientes", section)
                self.assertIn("mocks solo en limites externos", section)
                self.assertIn("slices verticales pequenos", section)
                self.assertIn("loop que detecte el sintoma exacto", section)
                self.assertIn("de 3 a 5 hipotesis falsables", section)
                self.assertIn("elimina la instrumentacion antes de cerrar", section)
                self.assertIn("artefacto redactado", section)

    def test_testing_review_keeps_spec_and_design_axes_separate(self) -> None:
        section = prompts.parse_template(ROOT / "inicial.txt")["TESTING"]

        self.assertIn("dos ejes que no se compensan entre si", section)
        self.assertIn("CUMPLIMIENTO DEL REQUERIMIENTO", section)
        self.assertIn("ESTANDARES Y DISENO", section)
        self.assertIn("punto base del diff", section)
        self.assertIn("loop reproducible que detecte el sintoma exacto", section)

    def test_analysis_completes_without_phases_or_nonblocking_questions(self) -> None:
        section = prompts.parse_template(ROOT / "inicial.txt")["ANALISIS"]

        self.assertIn("no requiere fases, handoffs ni autorizaciones posteriores", section)
        self.assertIn("concluye igualmente", section)
        self.assertIn("pregunta solo cuando", section)
        self.assertNotIn("DEV_IMPLEMENT_READY", section)
        self.assertNotIn("TESTING_REVIEW_READY", section)

    def test_browser_mode_requires_a_real_browser_and_evidence(self) -> None:
        section = prompts.parse_template(ROOT / "inicial.txt")["TEST_EN_BROWSER"]

        self.assertIn("navegador real", section)
        self.assertIn("no reemplazan esta validacion", section)
        self.assertIn("HEADED, HEADLESS o REMOTO", section)
        self.assertIn("consola", section)
        self.assertIn("requests fallidos", section)
        self.assertIn("screenshots, trace o video", section)
        self.assertIn("termina BLOCKED", section)
        self.assertIn("No declares COMPLETE si no hubo una sesion de navegador real", section)
        self.assertIn("Antes de emitir la salida final", section)
        self.assertIn("cierra por completo todas las instancias", section)
        self.assertIn("mediante MCP, Chrome DevTools o Playwright", section)
        self.assertIn("`about:blank` o `blank` no cuenta como cierre", section)

    def test_browser_capable_roles_close_test_instances_completely(self) -> None:
        sections = prompts.parse_template(ROOT / "inicial.txt")

        for role in ("TESTING", "SINGLE_DEVELOPER", "DEV"):
            with self.subTest(role=role):
                section = sections[role]
                self.assertIn("antes de emitir la salida final cierra por completo", section)
                self.assertIn("incluido el acceso mediante MCP", section)
                self.assertIn("`about:blank` o `blank` no cuenta como cierre", section)
                self.assertIn("No cierres instancias preexistentes", section)

    def test_consensus_analysis_has_independent_and_review_roles(self) -> None:
        sections = prompts.parse_template(ROOT / "inicial.txt")

        coordinator = sections["ANALISIS_A"]
        reviewer = sections["ANALISIS_B"]
        for section in (coordinator, reviewer):
            self.assertIn("No implementes", section)
            self.assertIn("ANALISIS_UNIFICADO.md", section)
            self.assertIn("CONSENSUS_READY", section)
            self.assertIn("EXTERNAL_CLARIFICATION_REQUIRED", section)
            self.assertIn("<CONSENSUS_RUN_ID>", section)

        self.assertIn("analisis inicial independiente", coordinator)
        self.assertIn("responsable de consolidar", coordinator)
        self.assertIn("cambia COINCIDENTE a ACORDADO", coordinator)
        self.assertIn("analisis inicial independiente", reviewer)
        self.assertIn("CONSENSUS_CHANGES_REQUESTED", reviewer)

    def test_render_replaces_harness_state_and_requirement(self) -> None:
        section = (
            "context_inicial_AAAA.txt <REQUERIMIENTO> <DEV_PHASE> "
            "<TESTING_PHASE> <TECH_PROFILE> <GENERATED_METADATA>"
        )
        rendered = prompts.render(
            section,
            "demo",
            "hacer algo con <API_KEY>",
            "implement",
            "review",
            "mixed",
            "2026-07-11T12:00:00-03:00",
            "consensus-test123",
        )
        self.assertIn("context_inicial_demo.txt", rendered)
        self.assertIn("hacer algo", rendered)
        self.assertIn("<API_KEY>", rendered)
        self.assertIn("IMPLEMENT", rendered)
        self.assertIn("REVIEW", rendered)
        self.assertNotIn("<DEV_PHASE>", rendered)

    def test_consensus_run_id_identifies_project_requirement_and_generation(self) -> None:
        first = prompts.build_consensus_run_id(
            "demo", "analizar login", "2026-07-11T12:00:00-03:00"
        )
        same = prompts.build_consensus_run_id(
            "demo", "analizar login", "2026-07-11T12:00:00-03:00"
        )
        changed = prompts.build_consensus_run_id(
            "demo", "analizar logout", "2026-07-11T12:00:00-03:00"
        )

        self.assertEqual(first, same)
        self.assertNotEqual(first, changed)
        self.assertRegex(first, r"^consensus-[0-9a-f]{16}$")

    def test_legacy_template_without_consensus_pair_remains_valid(self) -> None:
        separator = "-" * 40
        template = "\n".join(
            f"{separator}\n{role}\n{separator}\ncontenido {role} <REQUERIMIENTO>"
            for role in prompts.CORE_PROMPT_SECTIONS
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "legacy.txt"
            path.write_text(template, encoding="utf-8")
            sections = prompts.parse_template(path)

        self.assertEqual(set(prompts.CORE_PROMPT_SECTIONS), set(sections))

    def test_template_rejects_incomplete_consensus_pair(self) -> None:
        separator = "-" * 40
        roles = (*prompts.CORE_PROMPT_SECTIONS, "ANALISIS_A")
        template = "\n".join(
            f"{separator}\n{role}\n{separator}\ncontenido {role} <REQUERIMIENTO>"
            for role in roles
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "incomplete.txt"
            path.write_text(template, encoding="utf-8")
            with self.assertRaisesRegex(SystemExit, "deben aparecer juntas"):
                prompts.parse_template(path)

    def test_cli_with_legacy_template_generates_only_original_roles(self) -> None:
        separator = "-" * 40
        template = "\n".join(
            f"{separator}\n{role}\n{separator}\ncontenido {role} <REQUERIMIENTO>"
            for role in prompts.CORE_PROMPT_SECTIONS
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "context_inicial_demo.md").write_text("contexto", encoding="utf-8")
            requirement = root / "pedido.md"
            requirement.write_text("Analizar endpoint", encoding="utf-8")
            template_path = root / "legacy.txt"
            template_path.write_text(template, encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "prompts.py"),
                    "--plantilla",
                    str(template_path),
                    "--requirement",
                    str(requirement),
                    "--non-interactive",
                ],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(0, result.returncode, result.stderr)
            generated = {path.name for path in (root / "_temps").iterdir()}

        self.assertEqual(
            {
                "DEV.txt",
                "TESTING.txt",
                "SINGLE_DEVELOPER.txt",
                "REQUIERE_ANALISIS.txt",
                "REQUERIMIENTO.txt",
            },
            generated,
        )
        self.assertNotIn("ANALISIS_A.txt", result.stdout)

    def test_auto_profile_detects_mixed_project(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "composer.json").write_text("{}", encoding="utf-8")
            (root / "package.json").write_text(
                '{"dependencies":{"react":"1"}}', encoding="utf-8"
            )
            (root / "pyproject.toml").write_text("[project]", encoding="utf-8")
            (root / "migrations").mkdir()
            profile = prompts.technology_profile(root, "auto")
        self.assertIn("PHP", profile)
        self.assertIn("JavaScript/TypeScript", profile)
        self.assertIn("Python", profile)
        self.assertIn("frontend web", profile)
        self.assertIn("MySQL/datos", profile)

    def test_cli_generates_all_prompts_non_interactively(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "context_inicial_demo.md").write_text("contexto", encoding="utf-8")
            requirement = root / "pedido.md"
            requirement.write_text("Implementar endpoint", encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "prompts.py"),
                    "--requirement",
                    str(requirement),
                    "--non-interactive",
                    "--dev-phase",
                    "implement",
                    "--testing-phase",
                    "review",
                    "--profile",
                    "mixed",
                ],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(0, result.returncode, result.stderr)
            expected = {
                "DEV.txt",
                "TESTING.txt",
                "SINGLE_DEVELOPER.txt",
                "REQUIERE_ANALISIS.txt",
                "TEST_EN_BROWSER.txt",
                "ANALISIS_A.txt",
                "ANALISIS_B.txt",
                "REQUERIMIENTO.txt",
            }
            self.assertEqual(expected, {path.name for path in (root / "_temps").iterdir()})
            self.assertIn(
                "Fase inicial al cargar este prompt: IMPLEMENT",
                (root / "_temps/DEV.txt").read_text(),
            )
            self.assertIn(
                "Fase inicial al cargar este prompt: REVIEW",
                (root / "_temps/TESTING.txt").read_text(),
            )
            analysis_a = (root / "_temps/ANALISIS_A.txt").read_text()
            analysis_b = (root / "_temps/ANALISIS_B.txt").read_text()
            run_id_a = next(
                line for line in analysis_a.splitlines() if "CONSENSUS_RUN_ID:" in line
            )
            run_id_b = next(
                line for line in analysis_b.splitlines() if "CONSENSUS_RUN_ID:" in line
            )
            self.assertEqual(run_id_a, run_id_b)
            self.assertNotIn("<CONSENSUS_RUN_ID>", analysis_a + analysis_b)

    def test_cli_keeps_historical_requirement_aliases(self) -> None:
        for alias in ("-r", "--requerimiento", "--archivo"):
            with self.subTest(alias=alias), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / "context_inicial_demo.txt").write_text("contexto\n", encoding="utf-8")
                requirement = root / "sprint.txt"
                requirement.write_text("Compatibilidad CLI\n", encoding="utf-8")

                result = subprocess.run(
                    [sys.executable, str(ROOT / "prompts.py"), alias, str(requirement)],
                    cwd=root,
                    text=True,
                    capture_output=True,
                    check=False,
                )

                self.assertEqual(0, result.returncode, result.stderr)
                generated = (root / "_temps" / "DEV.txt").read_text(encoding="utf-8")
                self.assertIn("Compatibilidad CLI", generated)


if __name__ == "__main__":
    unittest.main()
