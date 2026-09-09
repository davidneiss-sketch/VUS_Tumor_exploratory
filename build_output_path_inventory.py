#!/usr/bin/env python3
"""PART B -- static inventory of every output file path any script in
this repository writes, and whether that path is claimed by more than
one producer.

SIMULATED: read-only static analysis (Python `ast` module) over every
`.py` file in the repository (excluding `tests/fixtures/`, which holds
test data, not producer scripts). Does not modify any file it scans.

Method, disclosed (Standing Rule 4 -- what this DOES and does NOT catch):

1. AST-walks every `.py` file for:
   - `open(X, "w"|'w'|"a"...)` calls, tracing X back to its nearest
     preceding assignment in the same function if X is a bare Name (one
     level of tracing -- e.g. `out_path = REPO_ROOT / "foo.tsv"` then
     `open(out_path, "w")` resolves to `REPO_ROOT / "foo.tsv"`). An
     f-string or `.format()`-templated path is captured as a TEMPLATE
     (its constant pieces), not a single fully-resolved literal, and
     flagged `dynamic=TRUE` -- it may resolve to more than one path at
     runtime (e.g. per-arm output files); collision analysis below
     treats every dynamic template as a SEPARATE producer identity from
     every static path, since (per this project's own actual collision
     history) the dangerous case is always a STATIC, shared filename
     within a caller-supplied directory, not a per-arm-parameterized one.
   - Calls to `write_tsv(X, ...)` (this project's own `gates_common.py`
     helper) and `write_tsv`-style calls, resolved the same way.
   - Calls to `subprocess.run([...])` (or `subprocess.run(cmd, ...)`
     where `cmd` is a list built a few lines above) whose argument list
     contains a literal `"--outdir"` followed by a literal path
     argument, OR a literal `"--table"`/`"--truth"`/`"--recovered"`/
     `"--scope"`/`"--lr-table"` followed by a literal path -- these are
     the exact CLI flags `gates_common.py`-based gates
     (gate4/gate6/gate8/gate9) use, and this project's actual, real
     collisions were always at exactly this kind of call site (a caller
     script's own `--outdir` choice).

2. What this does NOT catch, disclosed rather than silently omitted:
   - A path built via more than one level of variable indirection
     (`a = "x"; b = a; open(b, "w")`) -- not traced past one hop.
   - A path assembled by string concatenation/`os.path.join` with
     non-literal pieces whose value cannot be determined statically.
   - Any output path chosen only in documentation (a `.md` file's own
     recorded terminal command, e.g. `DEPLOYMENT_LOG.md`'s own history)
     rather than hardcoded in a `.py` file -- those are call-site
     invocations, not producer-script properties, and are reviewed
     separately, by hand, against this inventory's own known gate
     scripts' fixed output filenames (see OUTPUT_PATH_INVENTORY.tsv's
     own trailing rows, added from that manual review, each tagged
     `source=manual_review_of_deployment_log` rather than
     `source=ast_scan`).

Run: python3 build_output_path_inventory.py
"""
from __future__ import annotations

import ast
import csv
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent

SCAN_DIRS = [REPO_ROOT, REPO_ROOT / "gates", REPO_ROOT / "scripts", REPO_ROOT / "production"]
EXCLUDE_NAMES = {"build_output_path_inventory.py"}  # this script itself writes only its own output, not a pipeline artifact

WRITE_MODES = {"w", "wb", "a", "ab"}

# Gate CLI flags known to name an output-relevant path -- these are
# exactly this project's own real collision surface (see module docstring).
OUTPUT_FLAGS = {"--outdir", "--table", "--truth", "--recovered", "--scope", "--lr-table"}


def literal_repr(node: ast.AST) -> tuple[str, bool]:
    """Best-effort static rendering of a path expression. Returns
    (rendered_string, is_dynamic). is_dynamic=True means the expression
    contains a non-literal piece (a variable, a loop index, an f-string
    substitution) -- the rendered string keeps that piece as `{expr}` so
    the TEMPLATE is still informative, per the module docstring."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value, False
    if isinstance(node, ast.JoinedStr):  # f-string
        parts = []
        dynamic = False
        for value in node.values:
            if isinstance(value, ast.Constant):
                parts.append(str(value.value))
            else:
                dynamic = True
                try:
                    parts.append("{" + ast.unparse(value) + "}")
                except Exception:
                    parts.append("{?}")
        return "".join(parts), dynamic
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        left, left_dyn = literal_repr(node.left)
        right, right_dyn = literal_repr(node.right)
        sep = "" if left.endswith("/") or not left else "/"
        return f"{left}{sep}{right}", left_dyn or right_dyn
    if isinstance(node, ast.Call):
        # Path("literal") / Path('literal') -- a common, fully-static
        # wrapper this project's own scripts and this file's own test
        # fixtures both use; unwrap it to its literal argument rather
        # than treating the whole call as dynamic.
        func = node.func
        func_name = func.id if isinstance(func, ast.Name) else (func.attr if isinstance(func, ast.Attribute) else None)
        if func_name == "Path" and len(node.args) == 1:
            return literal_repr(node.args[0])
        try:
            return ast.unparse(node), True
        except Exception:
            return "<call>", True
    if isinstance(node, ast.Name):
        return node.id, True
    if isinstance(node, ast.Attribute):
        try:
            return ast.unparse(node), True
        except Exception:
            return "<attr>", True
    try:
        return ast.unparse(node), True
    except Exception:
        return "<unresolved>", True


class FileScanner(ast.NodeVisitor):
    def __init__(self, filename: str):
        self.filename = filename
        self.rows: list[dict] = []
        self.assignments: dict[str, ast.AST] = {}  # last-seen simple Name -> value expr, per file (single-hop trace)

    def visit_Assign(self, node: ast.Assign) -> None:
        for target in node.targets:
            if isinstance(target, ast.Name):
                self.assignments[target.id] = node.value
        self.generic_visit(node)

    def _resolve(self, node: ast.AST) -> tuple[str, bool]:
        if isinstance(node, ast.Name) and node.id in self.assignments:
            return literal_repr(self.assignments[node.id])
        return literal_repr(node)

    def visit_Call(self, node: ast.Call) -> None:
        func_name = None
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            func_name = node.func.attr

        if func_name == "open" and node.args:
            mode = None
            if len(node.args) >= 2 and isinstance(node.args[1], ast.Constant):
                mode = node.args[1].value
            for kw in node.keywords:
                if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
                    mode = kw.value.value
            if mode is None and len(node.args) < 2:
                mode = "r"  # default open() mode -- not a write, skip
            if mode in WRITE_MODES:
                path_str, dynamic = self._resolve(node.args[0])
                self.rows.append({"producer": self.filename, "output_path": path_str,
                                   "dynamic": dynamic, "call_kind": "open()", "line": node.lineno})

        if func_name == "write_tsv" and node.args:
            path_str, dynamic = self._resolve(node.args[0])
            self.rows.append({"producer": self.filename, "output_path": path_str,
                               "dynamic": dynamic, "call_kind": "write_tsv()", "line": node.lineno})

        if func_name == "run" and node.args:
            # subprocess.run([...]) or subprocess.run(cmd_var, ...)
            arg0 = node.args[0]
            elts = None
            if isinstance(arg0, ast.List):
                elts = arg0.elts
            elif isinstance(arg0, ast.Name) and arg0.id in self.assignments:
                maybe_list = self.assignments[arg0.id]
                if isinstance(maybe_list, ast.List):
                    elts = maybe_list.elts
            if elts:
                str_elts = []
                for e in elts:
                    s, dyn = literal_repr(e)
                    str_elts.append((s, dyn))
                for i, (s, dyn) in enumerate(str_elts):
                    if s in OUTPUT_FLAGS and i + 1 < len(str_elts):
                        val, val_dyn = str_elts[i + 1]
                        self.rows.append({"producer": self.filename, "output_path": f"{s}={val}",
                                           "dynamic": dyn or val_dyn, "call_kind": "subprocess.run() CLI flag",
                                           "line": node.lineno})

        self.generic_visit(node)


def _producer_name(path: Path) -> str:
    """Repo-relative name when the file is under REPO_ROOT (the normal
    case); falls back to the bare filename for a file scanned from
    outside the repo (a test fixture in an isolated temp directory)."""
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return path.name


def scan_file(path: Path) -> list[dict]:
    try:
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text, filename=str(path))
    except (SyntaxError, UnicodeDecodeError) as e:
        return [{"producer": _producer_name(path), "output_path": f"PARSE_ERROR: {e}",
                 "dynamic": True, "call_kind": "PARSE_ERROR", "line": 0}]
    scanner = FileScanner(_producer_name(path))
    scanner.visit(tree)
    return scanner.rows


def build_inventory_rows(scan_dirs: list[Path] | None = None, include_manual_rows: bool = True) -> list[dict]:
    """Runs the full static scan + manual-review rows + collision
    detection, and returns the resulting rows -- callable directly (not
    only via a subprocess reading a possibly-stale committed TSV) by
    scripts/preflight_collision_check.py, so the preflight check always
    reflects the CURRENT source tree, not whatever was last committed.

    `scan_dirs` defaults to this repository's real SCAN_DIRS; a test can
    pass an isolated temp directory instead, to scan a small, deliberately
    -constructed fixture rather than this repo's own real (and, by
    design, currently collision-free) source tree.
    `include_manual_rows=False` skips this repo's own historical-
    invocation rows, which name real files by their real repo-relative
    paths and would not resolve meaningfully against an isolated test
    fixture."""
    all_rows = []
    seen_files = set()
    for d in (scan_dirs if scan_dirs is not None else SCAN_DIRS):
        if not d.exists():
            continue
        for py_file in sorted(d.glob("*.py")):
            if py_file.name in EXCLUDE_NAMES or py_file in seen_files:
                continue
            seen_files.add(py_file)
            all_rows.extend(scan_file(py_file))

    if not include_manual_rows:
        expanded_rows = list(all_rows)
        return _finish_inventory(expanded_rows)

    # Manual-review rows: known historical CLI invocations recorded in
    # DEPLOYMENT_LOG.md that are NOT hardcoded in any .py source (the
    # --outdir value was typed at the terminal) -- per this project's own
    # documented collision history. Added here, explicitly tagged, not
    # silently omitted (Standing Rule 4).
    # Each row here encodes the FULL RESOLVED FILE PATH (--outdir + the
    # gate's own known fixed output filename), not just the --outdir
    # value alone -- comparing bare directories would falsely flag two
    # gates that share a --outdir but write DIFFERENT filenames there
    # (e.g. gate5's own metrics file vs. gate6's SIMULATED_RECOVERY_TABLE.tsv
    # both under production/) as a collision, which they are not. An
    # earlier draft of this script made exactly that mistake -- caught
    # and fixed here before this file was ever committed, not silently
    # left in.
    manual_rows = [
        {"producer": "DEPLOYMENT_LOG.md Invocation 2 (gate6, historical)",
         "output_path": "production/SIMULATED_RECOVERY_TABLE.tsv",
         "dynamic": False, "call_kind": "manual_review_of_deployment_log", "line": 0},
        {"producer": "DEPLOYMENT_LOG.md Invocation 3 (gate8, historical)",
         "output_path": "SIMULATED_GATE8_INTERVAL_REPORT.tsv (repo root)",
         "dynamic": False, "call_kind": "manual_review_of_deployment_log", "line": 0},
        {"producer": "DEPLOYMENT_LOG.md Invocation 4, gate6 (this session)",
         "output_path": "production_v2/SIMULATED_RECOVERY_TABLE.tsv",
         "dynamic": False, "call_kind": "manual_review_of_deployment_log", "line": 0},
        {"producer": "DEPLOYMENT_LOG.md Invocation 4, gate8 (this session)",
         "output_path": "production_v2/gate8_out/SIMULATED_GATE8_INTERVAL_REPORT.tsv",
         "dynamic": False, "call_kind": "manual_review_of_deployment_log", "line": 0},
        {"producer": "DEPLOYMENT_LOG.md Invocation 4, gate9 (this session)",
         "output_path": "production_v2/gate9_out/SIMULATED_GATE9_IMBALANCE_REPORT.tsv",
         "dynamic": False, "call_kind": "manual_review_of_deployment_log", "line": 0},
        {"producer": "loh_caller.py's own gate6 invocation (P06R3 REVERSION_DIAGNOSIS.md) -- DELIBERATE shared writer, gate6's merge-aware logic exists precisely for this",
         "output_path": "SIMULATED_RECOVERY_TABLE.tsv (repo root)",
         "dynamic": False, "call_kind": "manual_review_of_reversion_diagnosis", "line": 0},
        {"producer": "check_loh_caller_acceptance.py / check_gate_housekeeping_acceptance.py (this session, live gate6 re-run) -- DELIBERATE shared writer, same merge-aware target as above",
         "output_path": "SIMULATED_RECOVERY_TABLE.tsv (repo root)",
         "dynamic": False, "call_kind": "manual_review_of_this_session_collision", "line": 0},
    ]
    # NOTE on scope: subtype_gate8_check.py's EARLY, never-committed draft
    # (which used --outdir=repo-root and would have collided with the
    # STAKE task's own gate8 report there) is NOT listed as a row here --
    # it never existed in any committed revision of this repository, so
    # listing it as a "producer" in a live inventory would misrepresent
    # the current codebase (Standing Rule 3). The committed
    # subtype_gate8_check.py (scanned by the AST pass above, from its
    # actual current source) already uses its own dedicated
    # SIMULATED_subtype_gate8_out/ directory and does not collide with
    # anything -- see this file's own row from the AST scan, and
    # TRUTH_DELTA.md's subtype-fix addendum Section 7 for the historical
    # near-miss narrative.

    expanded_rows = list(all_rows) + manual_rows
    return _finish_inventory(expanded_rows)


def _finish_inventory(expanded_rows: list[dict]) -> list[dict]:
    """Normalizes paths and runs collision detection over a fully-
    assembled row list (static-scan rows, plus manual rows if any)."""
    # Resolve each row's output_path to a normalized, comparable key
    # (repo-relative, best-effort) for collision detection.
    def normalize(path_str: str) -> str:
        s = path_str.strip()
        for prefix in ("REPO_ROOT / ", "REPO_ROOT/"):
            if s.startswith(prefix):
                s = s[len(prefix):].strip('"\'')
        s = s.replace('"', "").replace("'", "")
        return s

    for r in expanded_rows:
        r["normalized_path"] = normalize(r["output_path"])

    # Collision detection: group STATIC (non-dynamic) rows by normalized
    # path; any group with more than one DISTINCT producer is a collision.
    static_rows = [r for r in expanded_rows if not r["dynamic"]]
    by_path: dict[str, set[str]] = {}
    for r in static_rows:
        by_path.setdefault(r["normalized_path"], set()).add(r["producer"])

    # SANCTIONED EXCEPTION: gate6_recovery.py itself is merge-aware BY
    # DESIGN (this task's own DO-NOT clause: "change gate6's existing
    # merge-aware logic, which works" -- explicitly preserved, not
    # eliminated). A path whose ONLY sharers are gate6_recovery.py
    # invocations (identifiable here by "SIMULATED_RECOVERY_TABLE.tsv" in
    # the path) is flagged shared_with_other_producer=TRUE (it IS a
    # shared path, factually) but ALSO known_sanctioned_exception=TRUE,
    # so the preflight check below can tell "the one deliberate,
    # protected case" apart from "every other collision, which is a bug."
    for r in expanded_rows:
        producers_at_path = by_path.get(r["normalized_path"], set())
        r["shared_with_other_producer"] = (not r["dynamic"]) and len(producers_at_path) > 1
        r["other_producers"] = "; ".join(sorted(p for p in producers_at_path if p != r["producer"])) if r["shared_with_other_producer"] else ""
        r["known_sanctioned_exception"] = (r["shared_with_other_producer"]
                                            and "SIMULATED_RECOVERY_TABLE.tsv" in r["normalized_path"])

    return expanded_rows


INVENTORY_COLUMNS = ["producer", "call_kind", "line", "output_path", "normalized_path", "dynamic",
                      "shared_with_other_producer", "known_sanctioned_exception", "other_producers"]


def main() -> None:
    expanded_rows = build_inventory_rows()

    out_path = REPO_ROOT / "OUTPUT_PATH_INVENTORY.tsv"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=INVENTORY_COLUMNS, delimiter="\t")
        w.writeheader()
        for r in expanded_rows:
            w.writerow({c: r.get(c, "") for c in INVENTORY_COLUMNS})

    n_shared = sum(1 for r in expanded_rows if r["shared_with_other_producer"])
    n_unsanctioned = sum(1 for r in expanded_rows if r["shared_with_other_producer"] and not r["known_sanctioned_exception"])
    print(f"Wrote {out_path} ({len(expanded_rows)} rows, {n_shared} flagged shared_with_other_producer=TRUE, "
          f"{n_unsanctioned} UNSANCTIONED)")
    if n_shared:
        print("SHARED PATHS FOUND:")
        for r in expanded_rows:
            if r["shared_with_other_producer"]:
                tag = "SANCTIONED EXCEPTION" if r["known_sanctioned_exception"] else "UNSANCTIONED -- COLLISION"
                print(f"  [{tag}] {r['producer']} -> {r['normalized_path']}  (also: {r['other_producers']})")


if __name__ == "__main__":
    main()
