#!/usr/bin/env python3
"""Convert AViD paper markdown sections to a single LaTeX file for arXiv."""

import re, os

BASE = "paper/draft_hermes"
SECTIONS = [
    "01_introduccion.md",
    "02_related_work.md",
    "03_pipeline.md",
    "04_validacion.md",
    "05_experimentos.md",
    "06_limitaciones.md",
    "07_conclusion.md",
]

def read_section(fname):
    with open(os.path.join(BASE, fname), encoding="utf-8") as f:
        return f.read()

def strip_comments(text):
    return re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)

def escape_latex(text):
    """Escape only truly dangerous LaTeX characters in non-math text. Leave LaTeX commands intact."""
    segments = re.split(
        r"(\$\$.*?\$\$|\$[^$]+\$|\\\[.*?\\\]|\\\(.*?\\\))", text, flags=re.DOTALL
    )
    result = []
    for i, seg in enumerate(segments):
        if i % 2 == 0:  # non-math
            seg = seg.replace("&", "\\&")
            seg = seg.replace("%", "\\%")
            seg = seg.replace("#", "\\#")
            # Don't touch backslash, braces, underscore, caret — they're part of LaTeX commands
        result.append(seg)
    return "".join(result)

def convert_table(md_table):
    """Convert a markdown table to a LaTeX table environment."""
    lines = md_table.strip().split("\n")
    rows = []
    for line in lines:
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        rows.append(cells)
    # Filter separator row
    data_rows = [r for r in rows if not all(re.match(r"^[-:]+$", c) for c in r)]
    if len(data_rows) < 2:
        return md_table
    ncols = max(len(r) for r in data_rows)
    colspec = "|" + "c|" * ncols
    latex = "\\begin{table}[htbp]\n\\centering\n"
    latex += f"\\begin{{tabular}}{{{colspec}}}\n\\hline\n"
    for i, row in enumerate(data_rows):
        while len(row) < ncols:
            row.append("")
        latex_row = " & ".join(
            cell.replace("&", "\\&").replace("%", "\\%").replace("#", "\\#")
            for cell in row
        )
        latex += latex_row + " \\\\\n"
        if i == 0:
            latex += "\\hline\n"
    latex += "\\hline\n\\end{tabular}\n"
    latex += "\\caption{}\n\\label{}\n\\end{table}"
    return latex

def md_to_latex(text):
    """Convert markdown body text to LaTeX."""
    text = strip_comments(text)

    # Extract and protect tables
    table_pattern = re.compile(
        r"(\|.+\|\n\|[-| :]+\|\n(?:\|.+\|\n?)+)", re.MULTILINE
    )
    tables = []
    def replace_table(m):
        tables.append(convert_table(m.group(1)))
        return f"<<<TABLE_{len(tables)-1}>>>"
    text = table_pattern.sub(replace_table, text)

    # Extract and protect code blocks
    code_blocks = []
    def replace_code(m):
        code_blocks.append(m.group(1))
        return f"<<<CODE_{len(code_blocks)-1}>>>"
    text = re.sub(r"```\n?(.*?)\n?```", replace_code, text, flags=re.DOTALL)

    # Headings (BEFORE escaping, while '#' is still '#')
    text = re.sub(r"^####\s+(.+)$", r"\\paragraph{\1}", text, flags=re.MULTILINE)
    text = re.sub(r"^###\s+(.+)$", r"\\subsubsection{\1}", text, flags=re.MULTILINE)
    text = re.sub(r"^##\s+(.+)$", r"\\subsection{\1}", text, flags=re.MULTILINE)
    text = re.sub(r"^#\s+(.+)$", r"\\section{\1}", text, flags=re.MULTILINE)

    # Bold (BEFORE escaping, while '**' is intact)
    text = re.sub(r"\*\*(.+?)\*\*", r"\\textbf{\1}", text)

    # Inline code (BEFORE escaping)
    text = re.sub(r"`([^`]+)`", r"\\texttt{\1}", text)

    # Italic (BEFORE escaping)
    text = re.sub(r"(?<!\*)\*([^*\n]+?)\*(?!\*)", r"\\textit{\1}", text)

    # Now escape LaTeX special chars in remaining plain text
    text = escape_latex(text)

    # Fix LaTeX commands inside \texttt{}: change \cmd to \textbackslash cmd
    text = re.sub(r'\\texttt\{(\\)([a-zA-Z]+)\}', r'\\texttt{\\textbackslash \2}', text)
    text = re.sub(r'\\texttt\{(\\)([a-zA-Z]+)\}', r'\\texttt{\\textbackslash \2}', text)  # second pass for \\\\ escaped

    # Lists
    lines = text.split("\n")
    in_enum = False
    in_itemize = False
    out = []
    for line in lines:
        enum_m = re.match(r"^(\d+)\.\s+(.+)", line)
        item_m = re.match(r"^-\s+(.+)", line)
        if enum_m:
            if not in_enum:
                if in_itemize:
                    out.append("\\end{itemize}")
                    in_itemize = False
                out.append("\\begin{enumerate}")
                in_enum = True
            out.append(f"\\item {enum_m.group(2)}")
        elif item_m:
            if not in_itemize:
                if in_enum:
                    out.append("\\end{enumerate}")
                    in_enum = False
                out.append("\\begin{itemize}")
                in_itemize = True
            out.append(f"\\item {item_m.group(1)}")
        else:
            if in_enum:
                out.append("\\end{enumerate}")
                in_enum = False
            if in_itemize:
                out.append("\\end{itemize}")
                in_itemize = False
            out.append(line)
    if in_enum:
        out.append("\\end{enumerate}")
    if in_itemize:
        out.append("\\end{itemize}")
    text = "\n".join(out)

    # Restore tables
    for i, t in enumerate(tables):
        text = text.replace(f"<<<TABLE_{i}>>>", t)

    # Restore code blocks as verbatim
    for i, c in enumerate(code_blocks):
        text = text.replace(f"<<<CODE_{i}>>>", f"\\begin{{verbatim}}{c}\\end{{verbatim}}")

    return text

def build_latex():
    parts = []

    # Preamble
    preamble = r"""\documentclass[12pt,a4paper]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage[spanish,es-noshorthands]{babel}
\usepackage{amsmath,amssymb,amsthm}
\usepackage{mathtools}
\usepackage{graphicx}
\usepackage{xcolor}
\usepackage{hyperref}
\usepackage{array,booktabs,multirow}
\usepackage[margin=2.5cm]{geometry}
\usepackage{setspace}
\onehalfspacing
\usepackage{verbatim}
\usepackage{listings}
\usepackage{caption}
\usepackage[numbers,sort&compress]{natbib}

\newtheorem{theorem}{Teorema}[section]
\newtheorem{lemma}[theorem]{Lema}
\newtheorem{proposition}[theorem]{Proposicion}
\newtheorem{corollary}[theorem]{Corolario}
\newtheorem{definition}[theorem]{Definicion}
\theoremstyle{remark}
\newtheorem{remark}{Observacion}[section]

\title{AViD Journal: Verificacion Automatizada de Novedad \\ de Teoremas con Grounding Formal}
\author{Ayrton Porto\textsuperscript{1}}
\date{Julio 2026}

\begin{document}
\maketitle

\begin{abstract}
Los sistemas de inteligencia artificial aplicados a la matematica verifican correccion pero no novedad. Un teorema generado automaticamente puede compilar en Lean sin errores y, sin embargo, ser un resultado ya conocido en Mathlib o en la literatura informal. Este articulo presenta AViD Journal, un pipeline que recibe un articulo en LaTeX, formaliza sus teoremas en Lean 4, y emite un veredicto de novedad con grounding formal mediante un arbol de decision en tres dimensiones: D1 (no-existencia previa en corpus formal e informal), D2 (no-trivialidad via tacticas automaticas), y D3 (distancia de Jaccard sobre premisas estructurales). El sistema se evalua de forma preliminar contra tres fuentes de ground truth: un eval set de 24 teoremas hand-curated, un experimento con 10 papers retirados de arXiv por duplicacion, y un estudio ancho sobre 52 papers (26 retirados + 26 controles). D2 alcanza 91.7\% de precision sobre el eval set, D1 C\_F cubre el 100\% de los teoremas no triviales, y D3 produce una escalera de distancias consistente con el juicio humano. El estudio ancho arroja un resultado negativo (Mann-Whitney $p = 0.854$): la similitud semantica de enunciados no basta para separar papers retirados de controles. El articulo documenta 17 limitaciones del framework, la implementacion y el diseno experimental, y propone vias concretas de mejora.
\end{abstract}
"""
    parts.append(preamble)

    # Process sections
    for fname in SECTIONS:
        text = read_section(fname)
        processed = md_to_latex(text)
        parts.append(processed)
        parts.append("\n")

    # Bibliography
    bib = r"""
\begin{thebibliography}{99}

\bibitem{abouzaid2026}
M.~Abouzaid \emph{et al.}, ``First Proof: A mathematics challenge for AI,''
arXiv:2602.05192, 2026.

\bibitem{tao2025}
T.~Tao, ``Machine-Assisted Proof,''
\emph{Notices of the AMS}, 2025.

\bibitem{kasaura2025}
K.~Kasaura \emph{et al.}, ``Discovering New Theorems via LLMs with In-Context Proof Learning in Lean,''
arXiv:2509.14274, 2025.

\bibitem{theoremsearch2026}
A.~Ilin, T.~Alper, and L.~Inchiostro, ``TheoremSearch: Semantic Search over Theorems,''
arXiv:2602.05216, 2026.

\bibitem{theoremgraph2026}
TheoremGraph + LeanGraph, arXiv:2606.25363, 2026. {[}VERIFICAR{]}

\bibitem{compose2026}
COMPOSE, arXiv:2605.30333, 2026. {[}VERIFICAR{]}

\bibitem{leanconjecturer2025}
N.~Onda \emph{et al.}, ``LeanConjecturer: Filtering Novelty in LLM-Generated Conjectures,''
arXiv:2506.22005, 2025.

\bibitem{matlas2026}
Matlas: 8.07M theorem statements from 435K peer-reviewed articles (1826--2025),
arXiv:2604.17484, 2026.

\bibitem{yoo2025}
S.~Yoo, ``The Axiom-Based Atlas of Mathematical Theorems,''
arXiv:2504.00063, 2025.

\bibitem{kaliszyk2013}
C.~Kaliszyk and J.~Urban, ``MaSh: Machine Learning for Sledgehammer,''
\emph{Interactive Theorem Proving (ITP)}, 2013. {[}VERIFICAR{]}

\bibitem{magnushammer2024}
M.~Mikula, A.~Jiang, W.~Li \emph{et al.}, ``Magnushammer: A Transformer-Based Approach to Premise Selection,''
\emph{ICLR}, 2024.

\bibitem{piotrowski2023}
B.~Piotrowski \emph{et al.}, ``Machine-Learned Premise Selection for Lean,''
arXiv:2304.00994, 2023.

\bibitem{network2026}
``The Network Structure of Mathlib,''
arXiv:2604.24797, 2026. {[}VERIFICAR{]}

\bibitem{huch2022}
F.~Huch, ``Structure in Theorem Proving: Analyzing the Archive of Formal Proofs,''
arXiv:2209.13305, 2022.

\bibitem{mining2024}
``Mining Math Conjectures from LLMs: A Pruning Approach,''
arXiv:2412.16177, 2024.

\bibitem{synthetic2024}
``Synthetic Theorem Generation in Lean,''
OpenReview EeDSMy5Ruj, 2024.

\bibitem{withdrarxiv2024}
R.~Rao \emph{et al.}, ``WithdrarXiv: A Large-Scale Dataset of Retracted Papers,''
arXiv:2412.03775, 2024.

\bibitem{pseudo2026}
Pseudo-Formalization / ArxivMathGradingBench, 2026. {[}VERIFICAR{]}

\bibitem{merlean2026}
MerLean, 2026. {[}VERIFICAR{]}

\bibitem{survey2026}
``AI for Mathematics: Progress, Challenges, and Prospects,''
arXiv:2601.13209, 2026.

\bibitem{lakatos1976}
I.~Lakatos, \emph{Proofs and Refutations}, Cambridge University Press, 1976.

\bibitem{dosen2003}
K.~Dosen, ``Identity of Proofs,''
\emph{Bulletin of Symbolic Logic}, vol.~9, no.~4, 2003.

\end{thebibliography}
"""
    parts.append(bib)
    parts.append("\n\\end{document}\n")

    output = "".join(parts)
    # Replace Unicode emoji with LaTeX equivalents
    emoji_map = {
        '\u2705': r'\checkmark',           # ✅
        '\u274c': r'$\times$',             # ❌
        '\u26a0\ufe0f': r'$\triangle$',    # ⚠️
        '\u26a0': r'$\triangle$',          # ⚠️ (sin variante)
        '\u23f3': r'timeout',              # ⏳
    }
    for emoji, latex in emoji_map.items():
        output = output.replace(emoji, latex)
    # Fix double-escaped backslashes inside texttt (e.g., \texttt{\\foo} -> \texttt{\textbackslash foo})
    output = re.sub(r'\\texttt\{\\\\([a-zA-Z]+)\}', r'\\texttt{\\textbackslash \1}', output)
    output = re.sub(r'\\texttt\{\\\\([a-zA-Z]+)\}', r'\\texttt{\\textbackslash \1}', output)  # second pass for chained
    # Clean up excess blank lines
    output = re.sub(r"\n{4,}", "\n\n\n", output)
    # Clean up double backslash issues from tables
    output = output.replace("\\\\ \\\\", "\\\\")
    # Escape underscores in plain text (not inside LaTeX commands already escaped)
    output = re.sub(r'(?<!\\)_(?![\s\\}])', r'\\_', output)
    # Escape carets in plain text
    output = re.sub(r'(?<!\\)\^(?![\s\\}])', r'\\textasciicircum{}', output)
    # Escape tildes in plain text
    output = re.sub(r'(?<!\\)~', r'\\textasciitilde{}', output)

    with open("paper/avid_journal.tex", "w", encoding="utf-8") as f:
        f.write(output)

    print(f"Generated: paper/avid_journal.tex")
    print(f"Lines: {output.count(chr(10))}")
    print(f"Bytes: {len(output)}")
    # Report some stats
    for tag in ["\\section{", "\\subsection{", "\\subsubsection{", "\\begin{table}",
                "\\begin{verbatim}", "\\begin{enumerate}", "\\begin{itemize}",
                "\\bibitem{", "\\textbf{", "\\texttt{", "\\textit{"]:
        print(f"  {tag}: {output.count(tag)}")
    em = output.count("\u2014")
    print(f"  em-dashes: {em}")

if __name__ == "__main__":
    build_latex()
