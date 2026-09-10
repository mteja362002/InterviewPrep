"""Minimal pytest shim — lets the provenance regression file execute in an
environment where pytest cannot be installed (no network egress).

Supports only what these tests use: `pytest.mark.parametrize`, plain asserts,
and class-based grouping with no fixtures. NOT a pytest replacement.
"""
import importlib
import inspect
import sys
import traceback
import types

sys.path.insert(0, ".")
sys.path.insert(0, "./tests")


def _make_pytest_stub():
    mod = types.ModuleType("pytest")

    class _Mark:
        @staticmethod
        def parametrize(argnames, argvalues):
            names = ([a.strip() for a in argnames.split(",")]
                     if isinstance(argnames, str) else list(argnames))

            def deco(fn):
                cases = []
                for vals in argvalues:
                    vals = vals if isinstance(vals, (tuple, list)) else (vals,)
                    cases.append(dict(zip(names, vals)))
                existing = getattr(fn, "_params", None)
                if existing:                      # stacked parametrize
                    fn._params = [{**a, **b} for a in existing for b in cases]
                else:
                    fn._params = cases
                return fn
            return deco

        @staticmethod
        def __getattr__(name):
            def deco(fn=None, **kw):
                return fn if fn is not None else (lambda f: f)
            return deco

    mod.mark = _Mark()
    mod.raises = None
    return mod


sys.modules.setdefault("pytest", _make_pytest_stub())


def run(module_name):
    mod = importlib.import_module(module_name)
    passed = failed = 0
    failures = []

    def invoke(label, fn, inst=None):
        nonlocal passed, failed
        params = getattr(fn, "_params", [{}])
        for kw in params:
            tag = f"{label}[{','.join(f'{k}={v!r}' for k, v in kw.items())}]" if kw else label
            try:
                fn(inst, **kw) if inst is not None else fn(**kw)
                passed += 1
                print(f"  PASS  {tag}")
            except Exception:
                failed += 1
                failures.append((tag, traceback.format_exc()))
                print(f"  FAIL  {tag}")

    for name, obj in vars(mod).items():
        if name.startswith("Test") and inspect.isclass(obj):
            print(f"\n{obj.__name__}")
            inst = obj()
            for mname, meth in sorted(vars(obj).items()):
                if mname.startswith("test_"):
                    invoke(mname, meth, inst)
        elif name.startswith("test_") and inspect.isfunction(obj):
            invoke(name, obj)

    print("\n" + "=" * 70)
    print(f"{module_name}: {passed} passed, {failed} failed")
    print("=" * 70)
    for tag, tb in failures:
        print(f"\n--- {tag} ---\n{tb}")
    return failed


if __name__ == "__main__":
    total = 0
    for m in sys.argv[1:] or ["test_provenance_status_regression"]:
        total += run(m)
    sys.exit(1 if total else 0)
