import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("updater", Path(__file__).parents[1] / "scripts/update-proxy-packages.py")
updater = importlib.util.module_from_spec(spec)
spec.loader.exec_module(updater)


class GoDependencyTests(unittest.TestCase):
    def test_toolchain_directive_can_raise_the_minimum(self):
        self.assertEqual(updater.required_go("go 1.25.5\ntoolchain go1.26.2\n"), "1.26.2")
        self.assertEqual(updater.required_go("go 1.25.5\ntoolchain go1.25.1\n"), "1.25.5")

    def choose(self, recipes, minimum, staging):
        def fake_git(*args):
            if args[0] == "ls-remote":
                return "\n".join("sha\trefs/heads/" + name for name in recipes)
            self.assertEqual(args[0], "clone")
            branch = args[args.index("--branch") + 1]
            folder = args[-1] / "golang"
            folder.mkdir(parents=True)
            folder.joinpath("Makefile").write_text(recipes[branch])
            return ""
        with patch.object(updater, "git", side_effect=fake_git):
            return updater.choose_go_recipe("test-repository", staging, minimum)

    def test_insufficient_patch_level_advances_to_newer_branch(self):
        recipes = {
            "25.x": "GO_VERSION_MAJOR_MINOR:=1.25\nGO_VERSION_PATCH:=4\n",
            "26.x": "GO_VERSION_MAJOR_MINOR:=1.26\nGO_VERSION_PATCH:=2\n",
        }
        with tempfile.TemporaryDirectory() as folder:
            staging = Path(folder)
            _, selected, branch = self.choose(recipes, "1.25.5", staging)
            self.assertEqual((selected, branch), ("1.26.2", "26.x"))
            self.assertFalse((staging / "golang-25").exists())

    def test_numeric_patch_comparison_accepts_fourteen_after_five(self):
        recipes = {"25.x": "GO_VERSION_MAJOR_MINOR:=1.25\nGO_VERSION_PATCH:=14\n"}
        with tempfile.TemporaryDirectory() as folder:
            _, selected, branch = self.choose(recipes, "1.25.5", Path(folder))
            self.assertEqual((selected, branch), ("1.25.14", "25.x"))

    def test_unsatisfied_requirement_fails_instead_of_using_old_go(self):
        recipes = {"25.x": "GO_VERSION_MAJOR_MINOR:=1.25\nGO_VERSION_PATCH:=4\n"}
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError, "No maintained Go recipe"):
                self.choose(recipes, "1.25.5", Path(folder))

    def test_recipe_format_change_is_not_silently_ignored(self):
        with self.assertRaisesRegex(ValueError, "Expected one PKG_HASH"):
            updater.set_make_value("PKG_VERSION:=1.14.0\n", "PKG_HASH", "new-release-hash")


if __name__ == "__main__":
    unittest.main()
