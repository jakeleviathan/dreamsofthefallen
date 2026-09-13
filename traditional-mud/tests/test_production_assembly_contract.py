from __future__ import annotations

import ast
import os
import subprocess
import sys
import unittest
from collections import defaultdict, deque
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MUD = ROOT / "mud"


class _AssemblyGraph:
    """Static view of explicit install_* wiring in the production entrypoints.

    Content modules in Dreams of the Fallen intentionally compose through small
    installer functions. A feature can be perfectly unit tested yet absent from
    the live game if its installer is never reachable from server.py. This graph
    makes that failure mode a regression instead of a manual code-review task.
    """

    def __init__(self) -> None:
        self.trees: dict[str, ast.Module] = {}
        self.defs: dict[tuple[str, str], ast.AST] = {}
        self.imported_symbols: dict[str, dict[str, tuple[str, str]]] = defaultdict(dict)
        self.imported_modules: dict[str, dict[str, str]] = defaultdict(dict)
        self.edges: dict[tuple[str, str], set[tuple[str, str]]] = defaultdict(set)
        self._load_sources()
        self._index_installers_and_imports()
        self._build_edges()

    @staticmethod
    def _module_for(path: Path) -> str:
        if path == ROOT / "server.py":
            return "ROOT"
        return f"mud.{path.stem}"

    def _load_sources(self) -> None:
        paths = [ROOT / "server.py", *sorted(MUD.glob("*.py"))]
        for path in paths:
            self.trees[self._module_for(path)] = ast.parse(path.read_text(encoding="utf-8"))

    def _index_installers_and_imports(self) -> None:
        for module, tree in self.trees.items():
            for node in tree.body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("install_"):
                    self.defs[(module, node.name)] = node
                elif isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("mud."):
                    for alias in node.names:
                        self.imported_symbols[module][alias.asname or alias.name] = (node.module, alias.name)
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.startswith("mud."):
                            local = alias.asname or alias.name.rsplit(".", 1)[-1]
                            self.imported_modules[module][local] = alias.name

    def _resolve(self, module: str, func: ast.expr) -> tuple[str, str] | None:
        if isinstance(func, ast.Name):
            if func.id in self.imported_symbols[module]:
                return self.imported_symbols[module][func.id]
            local = (module, func.id)
            if local in self.defs:
                return local
        if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
            imported_module = self.imported_modules[module].get(func.value.id)
            if imported_module:
                return imported_module, func.attr
        return None

    def _record_calls(self, source: tuple[str, str], module: str, node: ast.AST) -> None:
        for child in ast.walk(node):
            if not isinstance(child, ast.Call):
                continue
            target = self._resolve(module, child.func)
            if target in self.defs:
                self.edges[source].add(target)

    def _build_edges(self) -> None:
        for module, tree in self.trees.items():
            for node in tree.body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("install_"):
                    self._record_calls((module, node.name), module, node)
                elif not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    self._record_calls(("TOP", module), module, node)

    def reachable_installers(self) -> set[tuple[str, str]]:
        # Importing root server.py imports mud.server, so both modules' top-level
        # assembly statements execute in production.
        starts = (("TOP", "ROOT"), ("TOP", "mud.server"))
        seen = set(starts)
        queue = deque(starts)
        while queue:
            source = queue.popleft()
            for target in self.edges.get(source, ()):
                if target not in seen:
                    seen.add(target)
                    queue.append(target)
        return set(self.defs).intersection(seen)


class ProductionAssemblyContractTests(unittest.TestCase):
    def test_every_explicit_installer_is_reachable_from_production(self):
        graph = _AssemblyGraph()
        reachable = graph.reachable_installers()
        missing = sorted(set(graph.defs) - reachable)
        self.assertEqual(
            missing,
            [],
            "Installer functions exist but are not reachable from production assembly: "
            + ", ".join(f"{module}.{name}" for module, name in missing),
        )

    def test_real_production_import_has_critical_runtime_markers(self):
        # The static graph catches forgotten installer calls. This subprocess also
        # proves the assembled class itself carries critical live wrappers after
        # the real production entrypoint has executed.
        code = r'''
import server
markers = (
    "_starter_class_moment_runtime_installed",
    "_party_runtime_installed",
    "_death_recovery_runtime_installed",
    "_class_progression_runtime_installed",
    "_living_world_runtime_installed",
    "_planar_realms_runtime_installed",
    "_alpha_ux_runtime_installed",
    "_modern_client_runtime_installed",
)
missing = [name for name in markers if not getattr(server.PlayerSession, name, False)]
assert not missing, missing
print("PRODUCTION_ASSEMBLY_MARKERS_OK")
'''
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=ROOT,
            text=True,
            capture_output=True,
            env={**os.environ, "PYTHONPATH": str(ROOT)},
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertIn("PRODUCTION_ASSEMBLY_MARKERS_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
