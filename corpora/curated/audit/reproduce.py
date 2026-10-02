"""Focused source-level probes for the 2026-10-02 annotation audit.

Run: uv run python corpora/curated/audit/reproduce.py
Requires snapshot Git objects and Node.js. These are not upstream integration suites.
Source snippets are loaded from the case SHAs; no copied implementation is maintained.
"""

import __future__

import argparse
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


def write_enter_fixture(path: Path) -> None:
    """Build a browser fixture; real keyboard input must supply native activation."""
    # Model a routed link: the click listener cancels native navigation.
    # This preserves focus so both scripted and native Enter activation are observed.
    scripts = ["const SPACE = 32, ENTER = 13; window.clickCounts = {};"]
    links = []
    for side in ("base", "head"):
        src = source(66, "src/material/tabs/tab-nav-bar/tab-nav-bar.ts", side)
        method = src.split("  _handleKeydown(event: KeyboardEvent) {", 1)[1].split("\n  }", 1)[0]
        for mode in ("href", "no-href", "disabled"):
            key = f"{side}-{mode}"
            href = 'href="#target"' if mode != "no-href" else ""
            links.append(f'<a id="{key}" {href} role="tab" tabindex="0">{key}</a><br>')
            scripts.append(
                "{ const element = document.getElementById("
                + json.dumps(key)
                + ");"
                + "const self = {disabled: "
                + str(mode == "disabled").lower()
                + ", _tabNavBar: {tabPanel: true}, elementRef: {nativeElement: element}};"
                + "window.clickCounts[element.id] = 0;"
                + "element.addEventListener('click', event => {event.preventDefault();"
                + "window.clickCounts[element.id]++;"
                + "document.getElementById('counts').textContent = "
                + "JSON.stringify(window.clickCounts); });"
                + "element.addEventListener('keydown', function(event) {"
                + "(function(event) {"
                + method
                + "}).call(self, event); }); }"
            )
    path.write_text(
        '<!doctype html><meta charset="utf-8"><title>Case 066 native Enter probe</title>'
        + "<p>Focus each tab and press Enter once. Inspect clickCounts.</p>"
        + "".join(links)
        + '<pre id="counts"></pre><div id="target">Target</div>'
        + "<script>"
        + "\n".join(scripts)
        + "</script>"
    )
    print(f"Browser fixture written to {path}")


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
    strip_method = next(n for n in cls.body if n.name == "strip")
    raw_assignment = next(
        n
        for n in ast.walk(strip_method)
        if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Attribute) and t.attr == "raw_lines" for t in n.targets)
    )
    annotation = json.loads((ROOT / "corpora/curated/cases/case-064.json").read_text())
    issue = annotation["expected_issues"][0]
    assert issue["line_start"] == issue["line_end"] == raw_assignment.lineno
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser-fixture", type=Path, help="write the case-066 Enter HTML probe")
    args = parser.parse_args()
    if args.browser_fixture:
        write_enter_fixture(args.browser_fixture)
    else:
        main()
