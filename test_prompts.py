#!/usr/bin/env python3
"""Tests para el script prompts.py."""

import unittest
from unittest.mock import patch, MagicMock
import tempfile
import shutil
from pathlib import Path
import sys

# Importamos las funciones de prompts.py
# Para poder importar prompts, añadimos su directorio a sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import prompts


class TestPrompts(unittest.TestCase):

    def setUp(self):
        # Creamos un directorio temporal para cada test
        self.test_dir = tempfile.TemporaryDirectory()
        self.cwd = Path(self.test_dir.name)

        # Plantilla básica para pruebas
        self.template_content = (
            "--------------------------------------------------\n"
            "TESTING\n"
            "--------------------------------------------------\n"
            "testing template for context_inicial_AAAA.txt: <REQUERIMIENTO>\n"
            "--------------------------------------------------\n"
            "DEV\n"
            "--------------------------------------------------\n"
            "dev template for context_inicial_AAAA.txt: <REQUERIMIENTO>\n"
        )
        self.template_path = self.cwd / "inicial.txt"
        self.template_path.write_text(self.template_content, encoding="utf-8")

    def tearDown(self):
        self.test_dir.cleanup()

    def test_clean_requirement(self):
        # Caso multilínea con comentarios y espacios
        content = (
            "# Este es un comentario\n"
            "Requerimiento linea 1\n"
            "  # Comentario indentado\n"
            "Requerimiento linea 2\n"
            "\n"
            "Requerimiento linea 3 con UTF-8: Áéíóú ñ"
        )
        cleaned = prompts.clean_requirement(content)
        expected = (
            "Requerimiento linea 1\n"
            "Requerimiento linea 2\n"
            "\n"
            "Requerimiento linea 3 con UTF-8: Áéíóú ñ"
        )
        self.assertEqual(cleaned, expected)

    def test_clean_requirement_empty(self):
        content = "# Solo comentarios\n# de varias lineas\n"
        self.assertEqual(prompts.clean_requirement(content), "")

    def test_detect_project_success_single(self):
        # Crea un único archivo de contexto
        (self.cwd / "context_inicial_mi-proyecto.txt").touch()
        name = prompts.detect_project(self.cwd, None)
        self.assertEqual(name, "mi-proyecto")

    def test_detect_project_success_override(self):
        # Múltiples archivos de contexto, pero forzamos uno por override
        (self.cwd / "context_inicial_proyecto-a.txt").touch()
        (self.cwd / "context_inicial_proyecto-b.txt").touch()
        name = prompts.detect_project(self.cwd, "proyecto-a")
        self.assertEqual(name, "proyecto-a")

    def test_detect_project_failure_no_files(self):
        with self.assertRaises(SystemExit):
            prompts.detect_project(self.cwd, None)

    def test_detect_project_failure_multiple_no_override(self):
        (self.cwd / "context_inicial_proyecto-a.txt").touch()
        (self.cwd / "context_inicial_proyecto-b.txt").touch()
        with self.assertRaises(SystemExit):
            prompts.detect_project(self.cwd, None)

    def test_detect_project_failure_override_not_found(self):
        with self.assertRaises(SystemExit):
            prompts.detect_project(self.cwd, "proyecto-inexistente")

    def test_parse_template_success(self):
        sections = prompts.parse_template(self.template_path)
        self.assertIn("TESTING", sections)
        self.assertIn("DEV", sections)
        self.assertEqual(
            sections["TESTING"],
            "testing template for context_inicial_AAAA.txt: <REQUERIMIENTO>\n"
        )
        self.assertEqual(
            sections["DEV"],
            "dev template for context_inicial_AAAA.txt: <REQUERIMIENTO>\n"
        )

    def test_parse_template_invalid_missing_section(self):
        bad_template = (
            "--------------------------------------------------\n"
            "TESTING\n"
            "--------------------------------------------------\n"
            "testing template for context_inicial_AAAA.txt: <REQUERIMIENTO>\n"
        )
        bad_path = self.cwd / "bad_template.txt"
        bad_path.write_text(bad_template, encoding="utf-8")
        with self.assertRaises(SystemExit):
            prompts.parse_template(bad_path)

    def test_default_template_includes_team_guidelines(self):
        sections = prompts.parse_template(prompts.DEFAULT_TEMPLATE)

        self.assertIn("PRINCIPIOS DE REVISION INSPIRADOS EN KARPATHY", sections["TESTING"])
        self.assertIn("Supuestos explícitos", sections["TESTING"])
        self.assertIn("Cambios quirúrgicos", sections["TESTING"])
        self.assertIn("guías de Andrej Karpathy", sections["DEV"])
        self.assertIn("Pensar antes de modificar", sections["DEV"])
        self.assertIn("Ejecución orientada a objetivos", sections["DEV"])

    def test_render(self):
        section = "Contexto: context_inicial_AAAA.txt\nReq: <REQUERIMIENTO>"
        rendered = prompts.render(section, "mi-proyecto", "Hacer tests")
        expected = "Contexto: context_inicial_mi-proyecto.txt\nReq: Hacer tests"
        self.assertEqual(rendered, expected)

    @patch("prompts.read_requirement_via_editor")
    def test_main_non_interactive_success(self, mock_editor):
        # Configurar archivos de contexto
        (self.cwd / "context_inicial_mi-proyecto.txt").touch()

        # Crear archivo de requerimiento para pruebas
        req_file = self.cwd / "input_req.txt"
        req_content = "# Comentario de entrada\nReq de prueba\nLínea 2"
        req_file.write_text(req_content, encoding="utf-8")

        # Mockear argumentos
        test_args = [
            "prompts.py",
            "--proyecto", "mi-proyecto",
            "--plantilla", str(self.template_path),
            "--requerimiento", str(req_file)
        ]

        with patch.object(sys, "argv", test_args), patch("pathlib.Path.cwd", return_value=self.cwd):
            prompts.main()

        # Verificar salidas
        temps_dir = self.cwd / "_temps"
        self.assertTrue(temps_dir.exists())
        self.assertTrue((temps_dir / "DEV.txt").exists())
        self.assertTrue((temps_dir / "TESTING.txt").exists())
        self.assertTrue((temps_dir / "REQUERIMIENTO.txt").exists())

        # Verificar contenido
        dev_out = (temps_dir / "DEV.txt").read_text(encoding="utf-8")
        self.assertIn("dev template for context_inicial_mi-proyecto.txt: Req de prueba\nLínea 2", dev_out)

        testing_out = (temps_dir / "TESTING.txt").read_text(encoding="utf-8")
        self.assertIn("testing template for context_inicial_mi-proyecto.txt: Req de prueba\nLínea 2", testing_out)

        cache_out = (temps_dir / "REQUERIMIENTO.txt").read_text(encoding="utf-8")
        self.assertEqual(cache_out, req_content)

        # Asegurar que no se llamó al editor interactivo
        mock_editor.assert_not_called()

    def test_main_non_interactive_file_not_found(self):
        (self.cwd / "context_inicial_mi-proyecto.txt").touch()

        test_args = [
            "prompts.py",
            "--requerimiento", str(self.cwd / "inexistente.txt")
        ]

        temps_dir = self.cwd / "_temps"
        # No deberían existir salidas antes del error
        self.assertFalse((temps_dir / "DEV.txt").exists())

        with patch.object(sys, "argv", test_args), patch("pathlib.Path.cwd", return_value=self.cwd):
            with self.assertRaises(SystemExit):
                prompts.main()

        # Las salidas no deben haberse creado/modificado
        self.assertFalse((temps_dir / "DEV.txt").exists())

    def test_main_non_interactive_empty_requirement(self):
        (self.cwd / "context_inicial_mi-proyecto.txt").touch()

        req_file = self.cwd / "empty_req.txt"
        req_file.write_text("# Solo comentarios\n", encoding="utf-8")

        test_args = [
            "prompts.py",
            "--requerimiento", str(req_file)
        ]

        temps_dir = self.cwd / "_temps"

        with patch.object(sys, "argv", test_args), patch("pathlib.Path.cwd", return_value=self.cwd):
            with self.assertRaises(SystemExit):
                prompts.main()

        self.assertFalse((temps_dir / "DEV.txt").exists())

    @patch("subprocess.run")
    @patch.dict("os.environ", {"EDITOR": "dummy-editor"})
    def test_read_requirement_via_editor_success(self, mock_run):
        # Para que el editor mockeado escriba en el archivo y simule edición exitosa
        temps_dir = self.cwd / "_temps"
        temps_dir.mkdir(exist_ok=True)
        req_path = temps_dir / "REQUERIMIENTO.txt"

        def write_req(args):
            req_path.write_text("# Header\nRequerimiento desde editor", encoding="utf-8")
            return MagicMock(returncode=0)

        mock_run.side_effect = write_req

        req = prompts.read_requirement_via_editor(temps_dir)
        self.assertEqual(req, "Requerimiento desde editor")
        mock_run.assert_called_once_with(["dummy-editor", str(req_path)])

    @patch("subprocess.run")
    @patch.dict("os.environ", {"EDITOR": "dummy-editor"})
    def test_read_requirement_via_editor_failure(self, mock_run):
        temps_dir = self.cwd / "_temps"
        temps_dir.mkdir(exist_ok=True)

        # El editor retorna código de error
        mock_run.return_value = MagicMock(returncode=1)

        with self.assertRaises(SystemExit):
            prompts.read_requirement_via_editor(temps_dir)


if __name__ == "__main__":
    unittest.main()
