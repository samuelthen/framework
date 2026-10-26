"""A limited sentence-length check, not an ASD-STE100 compliance checker.

Checks prose in the abstract and numbered main sections. Excludes revision
notes, tables, captions, equations, references, and appendices. Pandoc expands
LaTeX macros before the check. Sentence and word counts are heuristic.
"""
from pathlib import Path
import json
import re
import subprocess

HERE = Path(__file__).resolve().parent
source = (HERE / "main.tex").read_text()
source = re.sub(r"\\rev\{\d+\}\{[^{}]*\}", "", source)
source = source.split(r"\begin{thebibliography}")[0] + r"\end{document}"
doc = json.loads(subprocess.run(
    ["pandoc", "--from=latex", "--to=json"], input=source,
    capture_output=True, text=True, check=True).stdout)


def inline(x):
    if isinstance(x, list):
        return "".join(inline(y) for y in x)
    if not isinstance(x, dict):
        return ""
    typ, value = x.get("t"), x.get("c")
    if typ in {"Space", "SoftBreak", "LineBreak"}:
        return " "
    if typ == "Str":
        return value
    if typ == "Code":
        return value[1]
    if typ in {"Emph", "Strong", "SmallCaps", "Strikeout"}:
        return inline(value)
    if typ in {"Span", "Link"}:
        return inline(value[1])
    if typ == "Quoted":
        return inline(value[1])
    # Citations, maths, and LaTeX references are technical tokens.
    if typ in {"Cite", "Math", "RawInline"}:
        return " X "
    return ""


paragraphs = []


def blocks(items):
    for item in items:
        typ, val = item.get("t"), item.get("c")
        if typ in {"Para", "Plain"}:
            paragraphs.append(inline(val))
        elif typ == "BulletList":
            for entry in val:
                blocks(entry)
        elif typ == "Div":
            blocks(val[1])


if "abstract" in doc["meta"]:
    blocks(doc["meta"]["abstract"].get("c", []))
blocks(doc["blocks"])
sentences = []
for paragraph in paragraphs:
    # Do not split at decimal points or abbreviations ending in lowercase.
    for sentence in re.split(r"(?<=[.!?])\s+(?=[A-Z])", paragraph):
        sentence = sentence.strip()
        if not sentence or not re.search(r"[.!?]", sentence):
            continue
        words = re.findall(r"[A-Za-z0-9]+(?:[.'_-][A-Za-z0-9]+)*", sentence)
        sentences.append({"words": len(words), "sentence": sentence})
assert sentences
short = sum(s["words"] <= 25 for s in sentences)
report = {"scope": "Abstract and main prose; heuristic sentence counts only",
          "sentences": len(sentences), "at_most_25_words": short,
          "percent_at_most_25_words": round(100*short/len(sentences), 1),
          "mean_words": round(sum(s["words"] for s in sentences)/len(sentences), 1),
          "above_25_words": [s for s in sentences if s["words"] > 25],
          "limits": "No approved-word dictionary, grammar certification, or percent-compliance claim."}
(HERE / "writing_check.json").write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
