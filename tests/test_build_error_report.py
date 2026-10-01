import contextlib
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('reporter', Path(__file__).parents[1] / 'scripts/report-build-errors.py')
reporter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reporter)


class CompilerDiagnosticsTests(unittest.TestCase):
    def test_leaf_failure_exposes_compiler_error_and_writes_summary(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            log = root / 'logs/package/mtk/drivers/mt_wifi/compile.txt'
            log.parent.mkdir(parents=True)
            log.write_text('CC wifi.o\nwifi.c:10: fatal error: missing%header.h: No such file\n')
            console = root / 'compile.log'
            console.write_text('ERROR: package/mtk/drivers/mt_wifi failed to build.\n')
            summary = root / 'summary.md'
            output = io.StringIO()
            with patch.dict('os.environ', {'GITHUB_STEP_SUMMARY': str(summary)}), contextlib.redirect_stdout(output):
                reporter.report(root, console)
            self.assertIn('::error title=package/mtk/drivers/mt_wifi::', output.getvalue())
            self.assertIn('missing%25header.h', output.getvalue())
            self.assertIn('wifi.c:10: fatal error', summary.read_text())

    def test_missing_package_logs_preserves_console_error(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            console = root / 'compile.log'
            console.write_text('fatal error: compiler missing\n')
            output = io.StringIO()
            with patch.dict('os.environ', {'GITHUB_STEP_SUMMARY': ''}), contextlib.redirect_stdout(output):
                reporter.report(root, console)
            self.assertIn('fatal error: compiler missing', output.getvalue())


if __name__ == '__main__':
    unittest.main()
