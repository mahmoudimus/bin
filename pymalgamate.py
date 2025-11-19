#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "libcst==1.8.2",
# ]
# ///
"""
A utility to amalgamate a Python package into a single file using LibCST.

This script will:
 1. Traverse all .py files under a given package directory.
 2. Remove any intra-package imports (imports of the package itself).
 3. Collect all external imports and uniqueify them.
 4. Concatenate the remaining code from each module into one output file.

Usage:
    python amalgamate_package.py /path/to/package mypkg output.py
"""
import argparse
import pkgutil
from pathlib import Path

import libcst as cst
from libcst import Assign, Name, SimpleStatementLine


class IntraPackageImportRemover(cst.CSTTransformer):
    """
    Transformer that removes any imports from the target package (and relative imports).
    """

    def __init__(self, pkg_name: str):
        self.pkg_name = pkg_name

    def _get_module_name(self, module_node: cst.BaseExpression) -> str:
        """Extract dotted module name from a CST module or alias node."""
        if isinstance(module_node, cst.Name):
            return module_node.value
        if isinstance(module_node, cst.Attribute):
            parts = []
            node = module_node
            while isinstance(node, cst.Attribute):
                parts.append(node.attr.value)
                node = node.value
            if isinstance(node, cst.Name):
                parts.append(node.value)
            return ".".join(reversed(parts))
        return ""

    def leave_Import(
        self, original_node: cst.Import, updated_node: cst.Import
    ) -> cst.CSTNode:
        # Filter out intra-package imports by full module name
        filtered_aliases = []
        for alias in updated_node.names:
            full_name = self._get_module_name(alias.name)
            # Remove imports of the package itself and its submodules
            if full_name == self.pkg_name or full_name.startswith(self.pkg_name + "."):
                continue
            filtered_aliases.append(alias)
        if not filtered_aliases:
            return cst.RemoveFromParent()  # type: ignore[return-value]
        return updated_node.with_changes(names=filtered_aliases)

    def leave_ImportFrom(
        self, original_node: cst.ImportFrom, updated_node: cst.ImportFrom
    ) -> cst.CSTNode:
        # Determine module string
        module_name = ""
        if updated_node.module:
            module_name = self._get_module_name(updated_node.module)
        # Skip any `from pkg...` or relative imports
        if module_name.startswith(self.pkg_name) or original_node.relative:
            return cst.RemoveFromParent()  # type: ignore[return-value]
        return updated_node


def topo_sort(deps: dict[str, set[str]]) -> list[str]:
    """
    Topologically sort based on prerequisites mapping (module->its dependencies).
    Returns a list where dependencies come before dependents.
    """
    # Make a mutable copy of dependencies
    deps_copy = {u: set(v) for u, v in deps.items()}
    order: list[str] = []
    # Start with modules that have no dependencies
    ready = [u for u, v in deps_copy.items() if not v]
    while ready:
        u = ready.pop(0)
        order.append(u)
        # Remove u as a dependency from all other modules
        for m in list(deps_copy.keys()):
            if u in deps_copy[m]:
                deps_copy[m].remove(u)
                if not deps_copy[m]:
                    ready.append(m)
    if len(order) != len(deps):
        raise RuntimeError("Cycle detected in dependency graph")
    return order


# New helper to scan modules using pkgutil
def scan_modules(package_dir: Path, prefix: str) -> dict[str, Path]:
    """
    Use pkgutil.walk_packages to discover all .py modules under package_dir,
    returning a mapping from module-relative name to its Path.
    """
    modules = {}
    for mod_info in pkgutil.walk_packages([str(package_dir)], prefix=prefix + "."):
        if mod_info.ispkg:
            continue
        spec = mod_info.module_finder.find_spec(mod_info.name, None)
        if spec and spec.origin and spec.origin.endswith(".py"):
            # derive name relative to prefix
            rel_name = mod_info.name[len(prefix) + 1 :]
            modules[rel_name] = Path(spec.origin)
    return modules


class DepCollector(cst.CSTVisitor):
    def __init__(self, remover: IntraPackageImportRemover, pkg_name: str):
        self.remover = remover
        self.pkg_name = pkg_name
        self.deps: set[str] = set()

    def visit_ImportFrom(self, node: cst.ImportFrom) -> None:
        if node.module:
            modname = self.remover._get_module_name(node.module)
            if modname.startswith(self.pkg_name + "."):
                self.deps.add(modname[len(self.pkg_name) + 1 :])

    def visit_Import(self, node: cst.Import) -> None:
        for alias in node.names:
            modname = self.remover._get_module_name(alias.name)
            if modname.startswith(self.pkg_name + "."):
                self.deps.add(modname[len(self.pkg_name) + 1 :])


def main():
    parser = argparse.ArgumentParser(
        description="Amalgamate a Python package into a single file."
    )
    parser.add_argument("src_dir", help="Path to the root of the package")
    parser.add_argument("pkg_name", help="Top-level package name")
    parser.add_argument("out_file", help="Path to the output .py file")
    args = parser.parse_args()

    # Discover modules via pkgutil under the package directory
    package_dir = Path(args.src_dir)
    module_map = scan_modules(package_dir, args.pkg_name)
    # Prepare for dependency analysis
    deps = {name: set() for name in module_map}
    remover = IntraPackageImportRemover(args.pkg_name)

    # Build dependency graph using LibCST traversal
    for mod_name, path in module_map.items():
        src = path.read_text(encoding="utf-8")
        mod = cst.parse_module(src)

        collector = DepCollector(remover, args.pkg_name)
        mod.visit(collector)
        for dep in collector.deps:
            if dep in module_map:
                deps[mod_name].add(dep)
    # Order modules so dependencies come first
    sorted_names = topo_sort(deps)

    external_imports = set()
    global_stmts: list[cst.CSTNode] = []
    collected_stmts: list[cst.CSTNode] = []
    seen_defs: set[str] = set()

    # Gather statements, deduplicate definitions, and collect imports
    for mod_name in sorted_names:
        path = module_map[mod_name]
        src = path.read_text(encoding="utf-8")
        module = cst.parse_module(src)
        modified = module.visit(remover)

        for stmt in modified.body:
            # Collect and hoist all top-level import statements so they appear
            # at the beginning of the amalgamated file.  LibCST represents a
            # bare ``import x`` statement as a ``SimpleStatementLine`` which
            # *contains* an ``Import`` node in its ``body``.  A ``from x import``
            # statement is represented similarly.  We therefore need to handle
            # both the raw ``Import`` / ``ImportFrom`` nodes *and* the single-
            # line wrapper that may contain them.

            # Bare ``import ...`` or ``from ... import ...``
            if isinstance(stmt, (cst.Import, cst.ImportFrom)):
                external_imports.add(cst.Module([]).code_for_node(stmt).strip())
                continue

            # One-liner wrapper around an import (the usual case)
            if (
                isinstance(stmt, SimpleStatementLine)
                and len(stmt.body) == 1
                and isinstance(stmt.body[0], (cst.Import, cst.ImportFrom))
            ):
                external_imports.add(
                    cst.Module([]).code_for_node(stmt.body[0]).strip()
                )
                continue

            # Detect definitions to avoid duplicates
            def_name = None
            if isinstance(stmt, cst.FunctionDef):
                def_name = stmt.name.value
            elif isinstance(stmt, cst.ClassDef):
                def_name = stmt.name.value
            elif isinstance(stmt, SimpleStatementLine):
                # Top-level assignment to a name
                if len(stmt.body) == 1 and isinstance(stmt.body[0], Assign):
                    target = stmt.body[0].targets[0].target
                    if isinstance(target, Name):
                        def_name = target.value

            if def_name:
                if def_name in seen_defs:
                    continue
                seen_defs.add(def_name)

            # Hoist global assignments (after imports) if this is a simple
            # top-level assignment or annotated assignment.
            if isinstance(stmt, SimpleStatementLine):
                # already checked for Assign case above; include AnnAssign too
                if len(stmt.body) == 1 and isinstance(
                    stmt.body[0], (Assign, cst.AnnAssign)
                ):
                    global_stmts.append(stmt)
                    continue

            collected_stmts.append(stmt)

    # Write output
    with open(args.out_file, "w", encoding="utf-8") as out:
        # Write a header
        out.write("# Auto-amalgamated by amalgamate_package.py\n")
        out.write(f"# Contains all code from package: {args.pkg_name}\n\n")

        # Write external imports
        for imp in sorted(external_imports):
            out.write(imp + "\n")
        out.write("\n")

        # Write hoisted globals (in deterministic order of appearance)
        for stmt in global_stmts:
            out.write(cst.Module([]).code_for_node(stmt) + "\n")
        if global_stmts:
            out.write("\n")

        # Write the deduplicated statements as a module body
        final_module = cst.Module(body=collected_stmts)  # type: ignore[arg-type]
        out.write(final_module.code)


if __name__ == "__main__":
    main()
