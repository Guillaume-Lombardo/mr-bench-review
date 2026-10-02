"""Focused source-level probes for the 2026-10-02 annotation audit.

Run: uv run python corpora/curated/audit/reproduce.py
Requires snapshot Git objects and Node.js. These are not upstream integration suites.
Source snippets are loaded from the case SHAs; no copied implementation is maintained.
"""

import __future__

import ast
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def source(number: int, path: str, side: str = "head") -> str:
    case = json.loads((ROOT / f"corpora/curated/cases/case-{number:03}.json").read_text())
    return subprocess.check_output(
        ["git", "show", f"{case[side + '_sha']}:{path}"], cwd=ROOT, text=True
    )


def javascript(code: str) -> None:
    subprocess.run(["node", "--input-type=commonjs", "-e", code], check=True, cwd=ROOT)


def main() -> None:
    src = source(95, "packages/vite/src/node/utils.ts")
    regex = src.split("const imageCandidateRegex =", 1)[1].split("\nconst ", 1)[0]
    function = src.split("export function parseSrcset", 1)[1].split("\n}\n", 1)[0]
    function = (
        "function parseSrcset"
        + function.replace("(string: string): ImageCandidate[]", "(string)")
        + "\n}"
    )
    spaces = src.split("const escapedSpaceCharacters =", 1)[1].split("\n", 1)[0]
    javascript(
        "const assert = require('node:assert/strict');\n"
        + "const imageCandidateRegex = "
        + regex
        + ";\n"
        + "const escapedSpaceCharacters = "
        + spaces
        + ";\n"
        + function
        + "\nassert.deepEqual(parseSrcset('a'), []);"
        + "assert.equal(parseSrcset('ab')[0].url, 'ab');"
        + "console.log('095: single-character URL disappears; two-character control retained');"
    )
    src = source(30, "django/contrib/admin/static/admin/js/SelectBox.js")
    javascript(
        "const assert = require('node:assert/strict'); global.window = {};\n"
        + src
        + "\nwindow.SelectBox.cache.audit = ["
        + "{group:'A', text:'z'}, {group:'AB', text:'a'}, {group:'A', text:'a'}];"
        + "window.SelectBox.sort('audit');"
        + "assert.deepEqual(window.SelectBox.cache.audit.map(x=>x.group), ['A','AB','A']);"
        + "console.log('030: source comparator splits group A around group AB');"
    )
    for side in ("base", "head"):
        src = source(66, "src/material/tabs/tab-nav-bar/tab-nav-bar.ts", side)
        method = src.split("  _handleKeydown(event: KeyboardEvent) {", 1)[1].split("\n  }", 1)[0]
        javascript(
            "const assert = require('node:assert/strict'); const SPACE=32, ENTER=13;"
            + "let prevented=0, clicks=0; const self={disabled:false,_tabNavBar:{tabPanel:true},"
            + "elementRef:{nativeElement:{click(){clicks++}}}};"
            + "(function(event){"
            + method
            + "}).call(self, {keyCode:SPACE,"
            + "preventDefault(){prevented++}});"
            + "assert.equal(clicks,1); assert.equal(prevented,0);"
            + f"console.log('066 {side}: Space clicks without preventing default');"
        )
    src = source(64, "src/_pytest/_code/source.py")
    tree = ast.parse(src)
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Source")
    cls.body = [
        n
        for n in cls.body
        if isinstance(n, ast.FunctionDef) and n.name in {"__init__", "__len__", "strip"}
    ]
    namespace = {}
    exec(
        compile(
            ast.Module(body=[cls], type_ignores=[]),
            "snapshot-064",
            "exec",
            flags=__future__.annotations.compiler_flag,
        ),
        namespace,
    )
    obj = namespace["Source"]()
    obj.lines = ["", "    return 1 / 0", ""]
    obj.raw_lines = list(obj.lines)
    stripped = obj.strip()
    assert stripped.lines == ["    return 1 / 0"]
    assert stripped.raw_lines[0] == ""
    tree = ast.parse(source(64, "src/_pytest/_code/code.py"))
    formatter = next(
        n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "FormattedExcinfo"
    )
    formatter.decorator_list = []
    formatter.body = [
        n
        for n in formatter.body
        if isinstance(n, ast.FunctionDef) and n.name == "get_highlight_arrows_for_line"
    ]
    offset = next(
        n
        for n in tree.body
        if isinstance(n, ast.FunctionDef) and n.name == "_byte_offset_to_character_offset"
    )
    exec(
        compile(
            ast.Module(body=[formatter, offset], type_ignores=[]), "snapshot-064-highlight", "exec"
        ),
        namespace,
    )
    highlight = namespace["FormattedExcinfo"]().get_highlight_arrows_for_line
    arguments = dict(line=stripped.lines[0], lineno=0, end_lineno=0, colno=11, end_colno=16)
    assert "^" not in "".join(highlight(raw_line=stripped.raw_lines[0], **arguments))
    assert "^" in "".join(highlight(raw_line=obj.raw_lines[1], **arguments))
    print("064: strip() misaligns raw lines; snapshot highlighting loses the expression carets")


if __name__ == "__main__":
    main()
