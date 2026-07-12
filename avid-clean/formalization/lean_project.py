"""
AViD Journal - Lean Project Manager
=====================================
Crea y gestiona un proyecto Lean 4 por paper.
Cada paper tiene su propio proyecto aislado con:
  - Estructura de directorios Lean
  - Paper.lean acumulativo
  - PAPER_INDEX.md como base de datos local
"""

import os
import re
import json
import shutil
import subprocess
from pathlib import Path
from typing import List, Dict, Optional


# ─────────────────────────────────────────────
# Rutas estandar del repo AViD
# ─────────────────────────────────────────────

# Este archivo vive en <repo>/src/formalization/lean_project.py, asi que la
# raiz del repo es tres niveles arriba.
AVID_REPO_ROOT = Path(__file__).resolve().parents[2]

# Fuente de los docs de agentes (avid_common.md, avid_sketch_agent.md, ...)
AVID_AGENT_DOCS_SRC = AVID_REPO_ROOT / "prompts" / "docs" / "prompts"

# Proyecto Lean por defecto (con Mathlib pre-compilado, compartido por todos
# los papers). Cada paper se crea como un sub-modulo dentro de Papers/.
DEFAULT_PARENT_PROJECT = AVID_REPO_ROOT / "lean_project"

# Subdirectorio donde viven los papers dentro del proyecto compartido.
PAPERS_SUBDIR = "Papers"


def ensure_papers_lib_in_lakefile(parent_project: Path) -> bool:
    """Asegura que el lakefile.toml del proyecto padre declara el lib `Papers`.

    Idempotente: si la entrada ya existe, no hace nada. Si no existe, anade
    al final del archivo:

        [[lean_lib]]
        name = "Papers"

    Returns:
        True si modifico el archivo, False si ya estaba listo.
    """
    lakefile = parent_project / "lakefile.toml"
    if not lakefile.exists():
        raise FileNotFoundError(f"No se encontro {lakefile}")

    content = lakefile.read_text(encoding="utf-8")

    # Detecta si ya hay un [[lean_lib]] con name = "Papers"
    pattern = re.compile(
        r'\[\[lean_lib\]\][^[]*?name\s*=\s*"Papers"',
        re.DOTALL,
    )
    if pattern.search(content):
        return False

    if not content.endswith("\n"):
        content += "\n"
    content += '\n[[lean_lib]]\nname = "Papers"\n'
    lakefile.write_text(content, encoding="utf-8")
    print(f"[avid] Anadido lean_lib 'Papers' a {lakefile}")
    return True


# ─────────────────────────────────────────────
# Utilidades
# ─────────────────────────────────────────────

def slugify(text: str) -> str:
    """Convierte un título de paper a nombre de directorio válido.
    
    Ejemplo: "On Boolean Algebras and Duality" → "on_boolean_algebras_and_duality"
    """
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)       # quita caracteres especiales
    text = re.sub(r'[\s-]+', '_', text)         # espacios/guiones → underscore
    text = re.sub(r'_+', '_', text)             # colapsa underscores múltiples
    text = text.strip('_')
    return text[:60]                            # máximo 60 caracteres


# ─────────────────────────────────────────────
# Plantillas de archivos Lean
# ─────────────────────────────────────────────

LAKEFILE_TOML = """\
name = "{project_name}"
version = "0.1.0"
keywords = ["math"]
defaultTargets = ["{module_name}"]

[leanOptions]
pp.unicode.fun = true
relaxedAutoImplicit = false

[[require]]
name = "mathlib"
scope = "leanprover-community"
rev = "v4.26.0"

[[lean_lib]]
name = "{module_name}"
"""

LEAN_TOOLCHAIN = "leanprover/lean4:v4.29.0"

PAPER_LEAN_HEADER = """\
-- ============================================================
-- AViD Journal — Paper: {paper_title}
-- Formalización automática generada por AViD
-- ============================================================

import Mathlib

"""

PAPER_INDEX_HEADER = """\
# PAPER_INDEX — {paper_title}

Base de datos local de bloques formalizados de este paper.
El Sketch Agent debe consultar este archivo ANTES de buscar en Mathlib.

---

"""

REVIEW_MD_HEADER = """\
# REVIEW — {paper_title}

Documento de seguimiento humano. El orchestrator anota aqui los bloques que
necesitan revisar manualmente: axiomas declarados (resultados externos sin
prueba en el paper) y bloques que no se pudieron formalizar (failed).

Los bloques `verified` NO aparecen aqui; vive el log limpio en `PAPER_INDEX.md`.

---

## Axiomas declarados

(ninguno todavia)

---

## Bloques fallidos

(ninguno todavia)

---

## Notas adicionales

"""


# ─────────────────────────────────────────────
# Clase principal
# ─────────────────────────────────────────────

class LeanProjectManager:
    """Gestiona el proyecto Lean de un paper.

    Dos modos:

    1. **Standalone** (parent_project=None): crea un proyecto Lean completo
       con su propio lakefile, toolchain y Mathlib. Para experimentos aislados.

    2. **Sub-proyecto compartido** (parent_project=<ruta>): crea el paper
       como sub-modulo Lean dentro de un proyecto existente que ya tiene
       Mathlib pre-compilado. Es la opcion recomendada para produccion: todos
       los papers comparten el mismo `.lake/` y el mismo Mathlib.

    En modo sub-proyecto, la estructura es:

        <parent_project>/
          lakefile.toml          (compartido, debe declarar lean_lib "Papers")
          lean-toolchain         (compartido)
          .lake/                 (compartido, Mathlib aqui)
          Papers/
            <ModuleName>/
              Paper.lean         (modulo: Papers.<ModuleName>.Paper)
              PAPER_INDEX.md
              REVIEW.md
              TASK.md            (escrito por el orchestrator por bloque)
              Blocks/
              docs/prompts/
    """

    def __init__(
        self,
        paper_title: str,
        base_dir: str = "lean_papers",
        parent_project: Optional[Path | str] = None,
    ):
        """
        Args:
            paper_title:    Titulo del paper (se usa para nombrar el proyecto)
            base_dir:       Directorio raiz donde se crean proyectos standalone.
                            Ignorado si parent_project esta dado.
            parent_project: Si se da, el paper se crea como sub-modulo
                            dentro de <parent_project>/Papers/<ModuleName>/.
                            Comparte Mathlib y .lake con otros papers.
        """
        self.paper_title = paper_title
        self.project_name = slugify(paper_title)
        self.module_name = "".join(
            word.capitalize() for word in self.project_name.split("_")
        )

        self.parent_project = Path(parent_project) if parent_project else None

        if self.parent_project is not None:
            # Modo sub-proyecto compartido
            self.base_dir = self.parent_project / PAPERS_SUBDIR
            self.project_dir = self.base_dir / self.module_name
            # Paper.lean vive directamente en el project_dir; el modulo Lean
            # asociado es Papers.<ModuleName>.Paper
            self.src_dir = self.project_dir
            self.lean_module = f"{PAPERS_SUBDIR}.{self.module_name}.Paper"
        else:
            # Modo standalone (legacy)
            self.base_dir = Path(base_dir)
            self.project_dir = self.base_dir / self.project_name
            self.src_dir = self.project_dir / self.module_name
            self.lean_module = f"{self.module_name}.Paper"

        self.paper_lean = self.src_dir / "Paper.lean"
        self.paper_index = self.project_dir / "PAPER_INDEX.md"
        self.review_md = self.project_dir / "REVIEW.md"

    # ── Creacion del proyecto ──────────────────

    def create(self) -> Path:
        """Crea (o reusa) la estructura del proyecto Lean.

        Si el paper ya existe en disco (Paper.lean presente), NO sobreescribe
        nada: solo refresca los docs/prompts (por si los prompts cambiaron) y
        garantiza que Blocks/ exista. Esto permite reanudar trabajo previo.

        Returns:
            Path al directorio del paper.
        """
        already_existed = self.project_dir.exists() and self.paper_lean.exists()

        if already_existed:
            print(f"[avid] [RESUME] Paper ya existe, no se sobreescribe: {self.project_dir}")
            (self.project_dir / "Blocks").mkdir(parents=True, exist_ok=True)
            self._copy_agent_docs()
            if self.parent_project is not None:
                ensure_papers_lib_in_lakefile(self.parent_project)
            print(f"[avid]      modulo Lean: {self.lean_module}")
            return self.project_dir

        print(f"[avid] Creando paper: {self.project_name}")

        if self.parent_project is None:
            self._create_standalone_project()
        else:
            self._create_sub_project()

        self.paper_lean.write_text(
            PAPER_LEAN_HEADER.format(paper_title=self.paper_title),
            encoding="utf-8",
        )
        self.paper_index.write_text(
            PAPER_INDEX_HEADER.format(paper_title=self.paper_title),
            encoding="utf-8",
        )
        self.review_md.write_text(
            REVIEW_MD_HEADER.format(paper_title=self.paper_title),
            encoding="utf-8",
        )

        (self.project_dir / "Blocks").mkdir(parents=True, exist_ok=True)
        self._copy_agent_docs()

        print(f"[avid] [OK] Paper creado en: {self.project_dir}")
        print(f"[avid]      modulo Lean: {self.lean_module}")
        return self.project_dir

    def _create_standalone_project(self) -> None:
        """Crea proyecto Lean completo (lakefile + toolchain + .lake propios)."""
        self.src_dir.mkdir(parents=True, exist_ok=True)

        lakefile = self.project_dir / "lakefile.toml"
        lakefile.write_text(
            LAKEFILE_TOML.format(
                project_name=self.project_name,
                module_name=self.module_name,
            ),
            encoding="utf-8",
        )

        toolchain = self.project_dir / "lean-toolchain"
        toolchain.write_text(LEAN_TOOLCHAIN, encoding="utf-8")

        root_lean = self.project_dir / f"{self.module_name}.lean"
        root_lean.write_text(
            f"import {self.module_name}.Paper\n",
            encoding="utf-8",
        )

    def _create_sub_project(self) -> None:
        """Crea el paper como sub-modulo de un proyecto Lean existente."""
        assert self.parent_project is not None

        if not self.parent_project.exists():
            raise FileNotFoundError(
                f"parent_project no existe: {self.parent_project}"
            )

        if not (self.parent_project / "lean-toolchain").exists():
            raise RuntimeError(
                f"{self.parent_project} no parece un proyecto Lean "
                f"(falta lean-toolchain)"
            )

        # Asegura que el lakefile padre exporta el lib "Papers".
        ensure_papers_lib_in_lakefile(self.parent_project)

        # Crea el directorio del paper. NO hay lakefile/toolchain aqui;
        # se heredan del proyecto padre.
        self.project_dir.mkdir(parents=True, exist_ok=True)

    def _copy_agent_docs(self, source_dir: Optional[Path] = None) -> None:
        """Copia prompts/docs/prompts/avid_*.md a <project>/docs/prompts/.

        Claude Code, ejecutandose con cwd=<project_dir>, encontrara los docs
        en `docs/prompts/avid_common.md`, etc.
        """
        src = Path(source_dir) if source_dir else AVID_AGENT_DOCS_SRC
        if not src.exists():
            print(f"[avid] [WARN] No se encontro {src} (copia de docs omitida)")
            return

        dst = self.project_dir / "docs" / "prompts"
        dst.mkdir(parents=True, exist_ok=True)

        copied = 0
        for md_file in src.glob("avid_*.md"):
            shutil.copy2(md_file, dst / md_file.name)
            copied += 1

        if copied:
            print(f"[avid] Copiados {copied} docs de agentes -> {dst}")

    def setup_mathlib(self) -> bool:
        """Ejecuta lake update y lake exe cache get para preparar Mathlib.
        
        Returns:
            True si fue exitoso
        """
        print("[avid] Configurando Mathlib (puede tardar varios minutos)...")

        try:
            # lake update: descarga dependencias
            subprocess.run(
                ["lake", "update"],
                cwd=self.project_dir,
                check=True,
            )

            # lake exe cache get: descarga binarios precompilados
            subprocess.run(
                ["lake", "exe", "cache", "get"],
                cwd=self.project_dir,
                check=True,
            )

            print("[avid] [OK] Mathlib lista")
            return True

        except subprocess.CalledProcessError as e:
            print(f"[avid] [FAIL] Error configurando Mathlib: {e}")
            return False

    # ── Gestión de Paper.lean ──────────────────

    def append_block(self, lean_code: str) -> int:
        """Agrega un bloque Lean verificado a Paper.lean.
        
        Args:
            lean_code: Código Lean ya verificado (sin errores)
            
        Returns:
            Número de línea donde fue insertado
        """
        current = self.paper_lean.read_text(encoding="utf-8")
        line_number = len(current.splitlines()) + 1
        updated = current + lean_code.rstrip() + "\n\n"
        self.paper_lean.write_text(updated, encoding="utf-8")
        return line_number

    def get_paper_lean_path(self) -> str:
        """Retorna la ruta absoluta de Paper.lean (para Claude Code)."""
        return str(self.paper_lean.resolve())

    def get_processed_blocks(self) -> Dict[str, Dict[str, str]]:
        """Lee PAPER_INDEX.md y retorna un dict label -> info del bloque.

        info incluye 'status' (verified/axiom/failed/other) y campos crudos
        ('type', 'lean_line', 'depends_on'). Util para skipear en modo resume.

        Returns:
            Dict { label: { 'status': str, 'type': str, 'lean_line': str,
                            'depends_on': str, 'raw_status': str } }
            Si PAPER_INDEX.md no existe, retorna dict vacio.
        """
        if not self.paper_index.exists():
            return {}

        content = self.paper_index.read_text(encoding="utf-8")
        result: Dict[str, Dict[str, str]] = {}

        # Cada entrada empieza con '## <label>' y termina con '---'.
        # Capturamos las lineas Type/Status/File/Depends on.
        block_re = re.compile(
            r"^##\s+(?P<label>[^\n]+?)(?:\s+—\s+(?P<title>[^\n]+))?\s*\n"
            r"Type:\s*(?P<type>[^\n]+)\s*\n"
            r"Status:\s*(?P<status>[^\n]+)\s*\n"
            r"File:\s*Paper\.lean:(?P<lean_line>\d+)\s*\n"
            r"Depends on:\s*(?P<deps>[^\n]+)\s*\n",
            re.MULTILINE,
        )
        for m in block_re.finditer(content):
            label = m.group("label").strip()
            raw_status = m.group("status").strip()
            status_low = raw_status.lower()
            # Normalizamos el status a una etiqueta simple.
            if "verified" in status_low or "OK" in raw_status or "verifi" in status_low:
                norm = "verified"
            elif "axiom" in status_low or "external" in status_low:
                norm = "axiom"
            elif "fail" in status_low:
                norm = "failed"
            else:
                norm = "other"
            result[label] = {
                "status": norm,
                "raw_status": raw_status,
                "type": m.group("type").strip(),
                "lean_line": m.group("lean_line").strip(),
                "depends_on": m.group("deps").strip(),
            }
        return result

    # ── Gestión de PAPER_INDEX.md ──────────────

    def register_block(
        self,
        label: str,
        block_type: str,
        title: Optional[str],
        statement: str,
        status: str,
        lean_line: int,
        dependencies: Optional[List[str]] = None,
        source: Optional[str] = None,
    ):
        """Registra un bloque en PAPER_INDEX.md.
        
        Args:
            label:        Identificador único (ej: "thm:lagrange")
            block_type:   "definition" | "theorem" | "lemma" | "proposition" | "corollary"
            title:        Título opcional del bloque
            statement:    Enunciado informal en LaTeX
            status:       "✅ verified" | "⚠️ axiom" | "❌ failed"
            lean_line:    Línea en Paper.lean donde está el bloque
            dependencies: Lista de labels de los que depende
            source:       Si es axioma externo, la referencia bibliográfica
        """
        entry = self._build_index_entry(
            label, block_type, title, statement,
            status, lean_line, dependencies, source
        )

        current = self.paper_index.read_text(encoding="utf-8")
        self.paper_index.write_text(current + entry, encoding="utf-8")

        # Si el bloque necesita atencion humana, lo anotamos en REVIEW.md
        # tambien. Detectamos por palabras clave en el status (resiliente a
        # presencia/ausencia de emojis).
        status_low = status.lower()
        if "axiom" in status_low or "external" in status_low:
            self.append_review_axiom(
                label=label,
                block_type=block_type,
                title=title,
                statement=statement,
                source=source,
                lean_line=lean_line,
            )
        elif "fail" in status_low:
            self.append_review_failed(
                label=label,
                block_type=block_type,
                title=title,
                statement=statement,
                lean_line=lean_line,
                reason=source,  # reusamos el campo source como motivo si viene
            )

    # ── Gestion de REVIEW.md ──────────────────

    def append_review_axiom(
        self,
        label: str,
        block_type: str,
        title: Optional[str],
        statement: str,
        source: Optional[str] = None,
        lean_line: int = 0,
    ) -> None:
        """Anade una entrada a la seccion 'Axiomas declarados' de REVIEW.md."""
        title_str = f" — {title}" if title else ""
        src_str = f"\n- **Fuente**: {source}" if source else ""
        excerpt = statement.strip()
        if len(excerpt) > 600:
            excerpt = excerpt[:600] + " ..."

        entry = (
            f"\n### `{label}` ({block_type}){title_str}\n"
            f"- **Paper.lean**: linea {lean_line}{src_str}\n"
            f"- **Enunciado**:\n\n```\n{excerpt}\n```\n"
        )
        self._append_to_review_section("## Axiomas declarados", entry)

    def append_review_failed(
        self,
        label: str,
        block_type: str,
        title: Optional[str],
        statement: str,
        lean_line: int = 0,
        reason: Optional[str] = None,
    ) -> None:
        """Anade una entrada a la seccion 'Bloques fallidos' de REVIEW.md."""
        title_str = f" — {title}" if title else ""
        reason_str = f"\n- **Motivo**: {reason}" if reason else ""
        excerpt = statement.strip()
        if len(excerpt) > 600:
            excerpt = excerpt[:600] + " ..."

        entry = (
            f"\n### `{label}` ({block_type}){title_str}\n"
            f"- **Paper.lean**: linea {lean_line}{reason_str}\n"
            f"- **Enunciado**:\n\n```\n{excerpt}\n```\n"
        )
        self._append_to_review_section("## Bloques fallidos", entry)

    def _append_to_review_section(self, section_header: str, entry: str) -> None:
        """Inserta `entry` dentro de la seccion `section_header` de REVIEW.md.

        Limpia el placeholder '(ninguno todavia)' la primera vez que se
        registra algo en esa seccion.
        """
        if not self.review_md.exists():
            # Crea REVIEW.md si por algun motivo no existia
            self.review_md.write_text(
                REVIEW_MD_HEADER.format(paper_title=self.paper_title),
                encoding="utf-8",
            )

        content = self.review_md.read_text(encoding="utf-8")

        # Localiza la seccion. Asume estructura del template.
        try:
            start = content.index(section_header)
        except ValueError:
            # Seccion ausente: la anadimos al final
            content = content.rstrip() + f"\n\n{section_header}\n{entry}\n"
            self.review_md.write_text(content, encoding="utf-8")
            return

        # Encuentra el siguiente '## ' o '---' que cierra la seccion
        rest = content[start + len(section_header):]
        next_section_offset = len(rest)
        for marker in ("\n## ", "\n---"):
            idx = rest.find(marker)
            if idx != -1 and idx < next_section_offset:
                next_section_offset = idx

        section_body = rest[:next_section_offset]
        section_body_clean = section_body.replace("(ninguno todavia)", "").rstrip()

        new_section = (
            section_header + "\n"
            + section_body_clean + "\n"
            + entry.rstrip() + "\n"
        )

        new_content = (
            content[:start]
            + new_section
            + rest[next_section_offset:]
        )
        # Garantiza un salto de linea antes del siguiente bloque
        if not new_content.endswith("\n"):
            new_content += "\n"
        self.review_md.write_text(new_content, encoding="utf-8")

    def update_block_status(self, label: str, new_status: str):
        """Actualiza el status de un bloque en PAPER_INDEX.md.
        
        Args:
            label:      Label del bloque (ej: "thm:lagrange")
            new_status: Nuevo status ("✅ verified" | "⚠️ axiom" | "❌ failed")
        """
        content = self.paper_index.read_text(encoding="utf-8")

        # Busca la línea de status del bloque y la reemplaza
        pattern = rf'(## {re.escape(label)}.*?Status: )([^\n]+)'
        updated = re.sub(pattern, rf'\g<1>{new_status}', content, flags=re.DOTALL)

        self.paper_index.write_text(updated, encoding="utf-8")

    def get_verified_blocks(self) -> List[Dict]:
        """Retorna los bloques con status verified del PAPER_INDEX.
        
        Útil para pasarle contexto al Sketch Agent antes de formalizar.
        """
        content = self.paper_index.read_text(encoding="utf-8")
        blocks = []

        # Parsea cada entrada del índice
        entries = re.split(r'\n(?=## )', content)
        for entry in entries:
            if not entry.startswith('## '):
                continue

            label_match = re.match(r'## (\S+)', entry)
            status_match = re.search(r'Status: (.+)', entry)
            type_match = re.search(r'Type: (.+)', entry)
            file_match = re.search(r'File: Paper\.lean:(\d+)', entry)

            if label_match and status_match and '✅' in status_match.group(1):
                blocks.append({
                    'label': label_match.group(1),
                    'type': type_match.group(1).strip() if type_match else '',
                    'lean_line': int(file_match.group(1)) if file_match else 0,
                })

        return blocks

    # ── Helpers privados ───────────────────────

    def _build_index_entry(
        self,
        label: str,
        block_type: str,
        title: Optional[str],
        statement: str,
        status: str,
        lean_line: int,
        dependencies: Optional[List[str]],
        source: Optional[str],
    ) -> str:
        """Construye una entrada de PAPER_INDEX.md."""
        title_str = f" — {title}" if title else ""
        deps_str = ", ".join(dependencies) if dependencies else "—"
        source_str = f"\nSource: {source}" if source else ""

        # Trunca el enunciado si es muy largo
        stmt_preview = statement[:200] + "..." if len(statement) > 200 else statement
        stmt_preview = stmt_preview.replace('\n', ' ').strip()

        return (
            f"## {label}{title_str}\n"
            f"Type: {block_type}\n"
            f"Status: {status}\n"
            f"File: Paper.lean:{lean_line}\n"
            f"Depends on: {deps_str}"
            f"{source_str}\n"
            f"Statement: {stmt_preview}\n"
            f"\n---\n\n"
        )


# ─────────────────────────────────────────────
# Función de conveniencia
# ─────────────────────────────────────────────

def create_paper_project(
    paper_title: str,
    base_dir: str = "lean_papers",
    setup_mathlib: bool = False,
    parent_project: Optional[Path | str] = None,
) -> LeanProjectManager:
    """Crea un proyecto Lean para un paper y retorna el manager.

    Args:
        paper_title:    Titulo del paper
        base_dir:       Directorio donde crear el proyecto (modo standalone)
        setup_mathlib:  Si True, ejecuta lake update + cache get (solo standalone)
        parent_project: Si se da, crea el paper como sub-modulo dentro de
                        <parent_project>/Papers/. Comparte Mathlib con otros papers.

    Returns:
        LeanProjectManager listo para usar
    """
    manager = LeanProjectManager(
        paper_title,
        base_dir=base_dir,
        parent_project=parent_project,
    )
    manager.create()

    if setup_mathlib and parent_project is None:
        manager.setup_mathlib()

    return manager


# ─────────────────────────────────────────────
# Test rápido
# ─────────────────────────────────────────────

if __name__ == "__main__":
    # Prueba con un paper de ejemplo
    manager = create_paper_project(
        paper_title="On Boolean Algebras and Stone Duality",
        base_dir="lean_papers",
    )

    print(f"\nEstructura creada:")
    print(f"  Proyecto:     {manager.project_dir}")
    print(f"  Paper.lean:   {manager.paper_lean}")
    print(f"  PAPER_INDEX:  {manager.paper_index}")

    # Simular el registro de un bloque
    manager.register_block(
        label="def:boolean_algebra",
        block_type="definition",
        title="Boolean Algebra",
        statement=r"A Boolean algebra is a tuple $(B, \vee, \wedge, \neg, 0, 1)$ satisfying...",
        status="✅ verified",
        lean_line=7,
        dependencies=None,
    )

    manager.register_block(
        label="thm:stone_representation",
        block_type="theorem",
        title="Stone Representation Theorem",
        statement=r"Every Boolean algebra is isomorphic to a field of sets.",
        status="❌ failed",
        lean_line=20,
        dependencies=["def:boolean_algebra"],
        source="Stone, 1936",
    )

    print(f"\nPAPER_INDEX.md generado:")
    print(manager.paper_index.read_text(encoding="utf-8"))
