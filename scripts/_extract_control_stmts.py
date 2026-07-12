"""Extract theorem statements for control papers from ctrl caches."""
import hashlib, re, json
from pathlib import Path

CACHE_DIR = Path("cache/retracted_dataset")

THEOREM_ENVS = r"(?:theorem|lemma|proposition|corollary|claim|conjecture|thm|lem|prop|cor|fact)"
STMT_RE = re.compile(rf"\\begin\{{{THEOREM_ENVS}\}}(.*?)\\end\{{{THEOREM_ENVS}\}}", re.DOTALL)

def to_v1(aid):
    return re.sub(r"v\d+$", "", aid) + "v1"

def get_stmt(arxiv_id):
    v1 = to_v1(arxiv_id)
    h = hashlib.sha256(v1.encode()).hexdigest()[:16]
    src = CACHE_DIR / f"ctrl_src_{h}"
    tex_files = list(src.rglob("*.tex")) if src.exists() else []
    if not tex_files:
        return None
    tex_files.sort(key=lambda p: p.stat().st_size, reverse=True)
    content = tex_files[0].read_text(encoding="utf-8", errors="replace")
    matches = list(STMT_RE.finditer(content))
    if not matches:
        return None
    for m in matches:
        env = m.group(0).split("{")[1].split("}")[0]
        if env.lower() in ("theorem", "thm", "proposition", "prop", "claim"):
            return m.group(1).strip()[:1000]
    env = matches[0].group(0).split("{")[1].split("}")[0]
    return matches[0].group(1).strip()[:1000]

ctrls = ["1501.01654v1", "1101.3431v2", "1101.3720v1", "0904.1783v3", "math/0504586v2"]
for c in ctrls:
    s = get_stmt(c)
    if s:
        print(f"{c}: {s[:200]}...")
    else:
        print(f"{c}: NO STATEMENT")
