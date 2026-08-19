import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("sdd_module", ROOT / "sdd" / "sdd.py")
assert SPEC and SPEC.loader
sdd = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = sdd
SPEC.loader.exec_module(sdd)


class SddHarnessTest(unittest.TestCase):
    def setUp(self) -> None:
        self.feature = sdd.Feature(1, "login", Path("specs/001-login"))

    def test_render_supports_all_roles_and_explicit_phases(self) -> None:
        expectations = {
            "DEV": "Fase IMPLEMENT",
            "TESTING": "Fase REVIEW",
            "TEST_EN_BROWSER": "Modalidad TEST EN BROWSER",
            "SINGLE_DEVELOPER": "Modalidad autonoma",
            "ANALISIS": "Modalidad ANALISIS",
            "ANALISIS_A": "ANALISIS CONSENSUADO A",
            "ANALISIS_B": "ANALISIS CONSENSUADO B",
        }
        for role, expected in expectations.items():
            with self.subTest(role=role):
                content = sdd.render_prompt(role, self.feature, "implement", "review", "mixed")
                self.assertIn(expected, content)
                self.assertIn("Perfil tecnologico: mixed", content)
                self.assertIn("Trabaja y valida solamente en local", content)
                self.assertIn("prefiere la rama local `dev`", content)
                self.assertIn("No crees commits", content)
                self.assertIn("incluye solo archivos del alcance vigente", content)

    def test_render_includes_debugging_testing_and_review_discipline(self) -> None:
        dev = sdd.render_prompt("DEV", self.feature, "implement", "baseline", "mixed")
        single = sdd.render_prompt(
            "SINGLE_DEVELOPER", self.feature, "plan", "baseline", "mixed"
        )
        testing = sdd.render_prompt("TESTING", self.feature, "implement", "review", "mixed")

        for content in (dev, single):
            self.assertIn("interfaces publicas o del seam mas alto viable", content)
            self.assertIn("resultados esperados independientes", content)
            self.assertIn("slices verticales pequenos", content)
            self.assertIn("loop que detecte el sintoma exacto", content)
            self.assertIn("de 3 a 5 hipotesis falsables", content)
            self.assertIn("elimina la instrumentacion antes de cerrar", content)

        self.assertIn("CUMPLIMIENTO DE LA SPEC", testing)
        self.assertIn("ESTANDARES Y DISENO", testing)
        self.assertIn("Ningun eje compensa fallos del otro", testing)
        self.assertIn("punto base del diff", testing)

    def test_autonomous_roles_do_not_inherit_coordinated_phases(self) -> None:
        single = sdd.render_prompt(
            "SINGLE_DEVELOPER", self.feature, "plan", "baseline", "mixed"
        )
        analysis = sdd.render_prompt("ANALISIS", self.feature, "plan", "baseline", "mixed")
        browser = sdd.render_prompt(
            "TEST_EN_BROWSER", self.feature, "plan", "baseline", "mixed"
        )

        for content in (single, analysis, browser):
            self.assertIn("Fases coordinadas DEV/TESTING: NO APLICAN", content)
            self.assertNotIn("Fase DEV: PLAN", content)
            self.assertNotIn("Fase TESTING: BASELINE", content)

        self.assertIn("No te detengas despues de presentar un plan", single)
        self.assertIn("esperes handoffs de DEV o TESTING", single)
        self.assertIn("No requiere fases, handoffs ni autorizaciones posteriores", analysis)
        self.assertIn("concluye igualmente", analysis)
        self.assertIn("navegador real", browser)
        self.assertIn("no sustituyen esta validacion", browser)
        self.assertIn("HEADED/visible", browser)
        self.assertIn("No declares COMPLETE sin una sesion real de browser", browser)
        self.assertIn("antes de emitir la salida final cierra por completo", browser)
        self.assertIn("incluido el acceso mediante MCP", browser)
        self.assertIn("`about:blank` o `blank` no cuenta como cierre", browser)
        self.assertIn("No cierres instancias preexistentes", browser)

    def test_consensus_roles_define_handoffs_and_separate_responsibilities(self) -> None:
        coordinator = sdd.render_prompt(
            "ANALISIS_A",
            self.feature,
            "plan",
            "baseline",
            "mixed",
            "consensus-test123",
        )
        reviewer = sdd.render_prompt(
            "ANALISIS_B",
            self.feature,
            "plan",
            "baseline",
            "mixed",
            "consensus-test123",
        )

        for content in (coordinator, reviewer):
            self.assertIn("primera ronda es independiente", content)
            self.assertIn("no implementes ni modifiques codigo", content)
            self.assertIn("EXTERNAL_CLARIFICATION_REQUIRED", content)
            self.assertIn("CONSENSUS_RUN_ID: consensus-test123", content)
            self.assertIn("COINCIDENTE, SUPUESTO, PENDIENTE o DESACUERDO", content)
            self.assertIn("matriz de trazabilidad", content)

        self.assertIn("consolida ANALISIS_UNIFICADO.md", coordinator)
        self.assertIn("CONSENSUS_REVIEW_READY", coordinator)
        self.assertIn("cambiar COINCIDENTE a ACORDADO", coordinator)
        self.assertIn("valida ANALISIS_UNIFICADO.md", reviewer)
        self.assertIn("CONSENSUS_CHANGES_REQUESTED", reviewer)

    def test_auto_profile_detects_project_markers(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "composer.json").write_text("{}", encoding="utf-8")
            (root / "requirements.txt").write_text("pytest", encoding="utf-8")
            profile = sdd.technology_profile(root, "auto")
        self.assertIn("PHP", profile)
        self.assertIn("Python", profile)

    def test_task_dependencies_are_validated_and_cycles_are_rejected(self) -> None:
        self.assertEqual(
            {1: [], 2: [1], 3: [1, 2]},
            sdd.parse_task_dependencies("CA2: CA1\nCA3: CA1, CA2", 3),
        )

        with self.assertRaisesRegex(SystemExit, "contienen un ciclo"):
            sdd.parse_task_dependencies("CA1: CA2\nCA2: CA1", 2)
        with self.assertRaisesRegex(SystemExit, "CA3, que no existe"):
            sdd.parse_task_dependencies("CA2: CA3", 2)
        with self.assertRaisesRegex(SystemExit, "no puede bloquearse a si misma"):
            sdd.parse_task_dependencies("CA1: CA1", 1)

    def test_command_tasks_writes_vertical_slices_and_blocking_edges(self) -> None:
        class Args:
            feature = None
            force = True

        with tempfile.TemporaryDirectory() as directory:
            previous_specs = sdd.SPECS_DIR
            try:
                sdd.SPECS_DIR = Path(directory) / "specs"
                feature_dir = sdd.SPECS_DIR / "001-login"
                feature_dir.mkdir(parents=True)
                (feature_dir / "spec.md").write_text(
                    "# Spec\n\n## Criterios De Aceptacion\n\n- Crear cuenta\n- Iniciar sesion\n",
                    encoding="utf-8",
                )
                with patch.object(
                    sdd,
                    "prompt_block",
                    side_effect=["Preparar fixture", "CA2: CA1"],
                ):
                    sdd.command_tasks(Args())
                tasks = (feature_dir / "tasks.md").read_text(encoding="utf-8")
            finally:
                sdd.SPECS_DIR = previous_specs

        self.assertIn("## Slices Verticales Por Criterio De Aceptacion", tasks)
        self.assertIn("**Que entrega:** Crear cuenta", tasks)
        self.assertIn("**Bloqueada por:** Ninguna", tasks)
        self.assertIn("**Que entrega:** Iniciar sesion", tasks)
        self.assertIn("**Bloqueada por:** CA1", tasks)
        self.assertIn("comportamiento end-to-end minimo", tasks)
        self.assertIn("interfaz publica o seam mas alto viable", tasks)

    def test_command_prompts_writes_all_harnesses(self) -> None:
        class Args:
            feature = None
            force = True
            dev_phase = "plan"
            testing_phase = "baseline"
            profile = "auto"

        with tempfile.TemporaryDirectory() as directory:
            previous_specs = sdd.SPECS_DIR
            try:
                sdd.SPECS_DIR = Path(directory) / "specs"
                feature_dir = sdd.SPECS_DIR / "001-login"
                feature_dir.mkdir(parents=True)
                sdd.command_prompts(Args())
                generated = {path.name for path in (feature_dir / "prompts").iterdir()}
                analysis_a = (feature_dir / "prompts/ANALISIS_A.txt").read_text()
                analysis_b = (feature_dir / "prompts/ANALISIS_B.txt").read_text()
            finally:
                sdd.SPECS_DIR = previous_specs

        self.assertEqual(
            {
                "DEV.txt",
                "TESTING.txt",
                "TEST_EN_BROWSER.txt",
                "SINGLE_DEVELOPER.txt",
                "ANALISIS.txt",
                "ANALISIS_A.txt",
                "ANALISIS_B.txt",
            },
            generated,
        )
        run_id_a = next(
            line for line in analysis_a.splitlines() if line.startswith("CONSENSUS_RUN_ID:")
        )
        run_id_b = next(
            line for line in analysis_b.splitlines() if line.startswith("CONSENSUS_RUN_ID:")
        )
        self.assertEqual(run_id_a, run_id_b)
        self.assertRegex(run_id_a, r"^CONSENSUS_RUN_ID: consensus-[0-9a-f]{16}$")


if __name__ == "__main__":
    unittest.main()
