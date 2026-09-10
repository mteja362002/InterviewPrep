"""Execute the canonical-authority tests without importing the full module.

`knowledge_generation` transitively imports pydantic, which cannot be installed
in this sandbox (no network egress). To still test the REAL code rather than a
copy, this parses `knowledge_generation.py` and exec's only the two pure
helpers, then installs them as a stand-in module so the test file's
`from knowledge_generation import ...` resolves to genuine source text.
"""
import ast
import sys
import types

sys.path.insert(0, ".")

TARGETS = {"_deterministic_related", "_merge_relationships"}
SRC = "knowledge_generation.py"

tree = ast.parse(open(SRC, encoding="utf-8").read(), filename=SRC)
picked = [n for n in tree.body
          if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name in TARGETS]

missing = TARGETS - {n.name for n in picked}
if missing:
    raise SystemExit(f"Could not locate in {SRC}: {sorted(missing)}")

module = types.ModuleType("knowledge_generation")
module.__dict__["__builtins__"] = __builtins__
code = compile(ast.Module(body=picked, type_ignores=[]), SRC, "exec")
exec(code, module.__dict__)
sys.modules["knowledge_generation"] = module

print(f"Extracted from real source: {sorted(TARGETS)}")
print(f"  source file: {SRC}")
print()

import scratch_minipytest  # noqa: E402  (installs the pytest shim)

sys.exit(1 if scratch_minipytest.run("test_canonical_relationship_authority") else 0)
