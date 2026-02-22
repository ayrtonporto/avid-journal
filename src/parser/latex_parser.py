"""
AVID LaTeX Parser - Extractor de Bloques Matemáticos
====================================================
Parser estructural para archivos .tex que extrae entornos matemáticos
y los prepara para formalización en Lean 4.

Autor: AVID Platform
"""

import re
import json
from typing import List, Dict, Optional, Tuple
from pathlib import Path


class LaTeXParser:
    """Parser para extraer bloques matemáticos estructurados de archivos LaTeX."""
    
    # Entornos matemáticos a extraer (base)
    MATH_ENVIRONMENTS = ['definition', 'theorem', 'lemma', 'proposition', 'corollary']
    
    # Variantes comunes en español e inglés
    ENVIRONMENT_VARIANTS = {
        'teorema': 'theorem',
        'definicion': 'definition',
        'definición': 'definition',
        'lema': 'lemma',
        'proposicion': 'proposition',
        'proposición': 'proposition',
        'corolario': 'corollary',
        'thm': 'theorem',
        'defn': 'definition',
        'def': 'definition',
        'lem': 'lemma',
        'prop': 'proposition',
        'cor': 'corollary',
        'corol': 'corollary'
    }
    
    def __init__(self, custom_environments=None):
        """
        Inicializa el parser con patrones de regex compilados.
        
        Args:
            custom_environments: Lista adicional de nombres de entornos personalizados
        """
        # Combinar entornos base con variantes
        all_envs = set(self.MATH_ENVIRONMENTS)
        all_envs.update(self.ENVIRONMENT_VARIANTS.keys())
        
        # Agregar entornos personalizados si los hay
        if custom_environments:
            all_envs.update(custom_environments)
        
        # Crear patrón que capture cualquier entorno válido
        env_pattern_str = r'\\begin\{(' + '|'.join(re.escape(env) for env in all_envs) + r')\*?\}(?:\[([^\]]*)\])?'
        self.env_pattern = re.compile(env_pattern_str, re.IGNORECASE)
        
        # Patrón para detectar entorno proof (también variantes)
        proof_variants = ['proof', 'prueba', 'demostracion', 'demostración', 'dem']
        proof_pattern_str = r'\\begin\{(' + '|'.join(proof_variants) + r')\*?\}'
        self.proof_start_pattern = re.compile(proof_pattern_str, re.IGNORECASE)
        
        proof_end_pattern_str = r'\\end\{(' + '|'.join(proof_variants) + r')\*?\}'
        self.proof_end_pattern = re.compile(proof_end_pattern_str, re.IGNORECASE)
    
    def remove_comments(self, text: str) -> str:
        """
        Elimina comentarios LaTeX (líneas que empiezan con %).
        
        Args:
            text: Texto LaTeX con posibles comentarios
            
        Returns:
            Texto sin comentarios
        """
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Buscar % que no esté escapado
            comment_pos = -1
            i = 0
            while i < len(line):
                if line[i] == '%' and (i == 0 or line[i-1] != '\\'):
                    comment_pos = i
                    break
                i += 1
            
            if comment_pos >= 0:
                cleaned_lines.append(line[:comment_pos])
            else:
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def clean_content(self, content: str) -> str:
        """
        Limpia el contenido eliminando comandos de formato irrelevantes.
        Preserva matemáticas y estructura lógica.
        
        Args:
            content: Contenido LaTeX a limpiar
            
        Returns:
            Contenido limpio
        """
        # Eliminar comandos de espaciado
        content = re.sub(r'\\vspace\{[^}]+\}', '', content)
        content = re.sub(r'\\hspace\{[^}]+\}', '', content)
        content = re.sub(r'\\newpage', '', content)
        content = re.sub(r'\\clearpage', '', content)
        content = re.sub(r'\\pagebreak', '', content)
        
        # Simplificar formato de texto (pero mantener el contenido)
        content = re.sub(r'\\textbf\{([^}]+)\}', r'\1', content)
        content = re.sub(r'\\textit\{([^}]+)\}', r'\1', content)
        content = re.sub(r'\\emph\{([^}]+)\}', r'\1', content)
        
        # Eliminar espacios múltiples y líneas vacías excesivas
        content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)
        content = re.sub(r'[ \t]+', ' ', content)
        
        return content.strip()
    
    def extract_references(self, text: str) -> List[str]:
        """
        Extrae todas las referencias \\ref{} y \\eqref{} del texto.
        
        Args:
            text: Contenido LaTeX donde buscar referencias
            
        Returns:
            Lista de labels referenciados (sin duplicados)
        """
        references = []
        
        # Patrón para \ref{label} y \eqref{label}
        ref_pattern = re.compile(r'\\(?:eq)?ref\{([^}]+)\}')
        
        for match in ref_pattern.finditer(text):
            ref_label = match.group(1).strip()
            if ref_label and ref_label not in references:
                references.append(ref_label)
        
        return references
    
    def extract_label(self, text: str, start_pos: int) -> Tuple[Optional[str], int]:
        """
        Extrae el \\label{} que puede aparecer justo después del inicio del entorno.
        
        Args:
            text: Texto completo
            start_pos: Posición justo después de \\begin{theorem}[titulo]
            
        Returns:
            Tupla (label, nueva_posición_inicio_contenido) donde label puede ser None
        """
        # Patrón para capturar \label{nombre_del_label}
        # Permitimos espacios en blanco, saltos de línea, etc. antes del \label
        label_pattern = re.compile(r'^\s*\\label\{([^}]+)\}', re.MULTILINE)
        
        # Buscar en los primeros 200 caracteres después del inicio
        search_text = text[start_pos:start_pos + 200]
        match = label_pattern.match(search_text)
        
        if match:
            label = match.group(1).strip()
            # Retornar el label y la nueva posición (después del \label)
            new_pos = start_pos + match.end()
            return label, new_pos
        
        # No hay label
        return None, start_pos
    
    def normalize_env_type(self, env_type: str) -> str:
        """
        Normaliza el nombre del entorno a su forma estándar.
        
        Args:
            env_type: Nombre del entorno (puede ser variante o personalizado)
            
        Returns:
            Nombre normalizado del entorno
        """
        env_lower = env_type.lower().rstrip('*')
        
        # Si es una variante conocida, devolver el nombre estándar
        if env_lower in self.ENVIRONMENT_VARIANTS:
            return self.ENVIRONMENT_VARIANTS[env_lower]
        
        # Si es un nombre estándar, devolverlo
        if env_lower in self.MATH_ENVIRONMENTS:
            return env_lower
        
        # Si es personalizado, intentar clasificarlo
        # Heurística simple: si contiene "th" probablemente es theorem, "def" es definition, etc.
        if 'th' in env_lower or 'teo' in env_lower:
            return 'theorem'
        elif 'def' in env_lower:
            return 'definition'
        elif 'lem' in env_lower:
            return 'lemma'
        elif 'prop' in env_lower:
            return 'proposition'
        elif 'cor' in env_lower:
            return 'corollary'
        
        # Si no se puede clasificar, devolver como está (pero lowercase)
        return env_lower
    
    def extract_environment(self, text: str, start_pos: int, env_type: str) -> Tuple[str, int]:
        """
        Extrae el contenido de un entorno desde una posición dada.
        
        Args:
            text: Texto completo
            start_pos: Posición de inicio del entorno
            env_type: Tipo de entorno (theorem, lemma, etc.)
            
        Returns:
            Tupla (contenido, posición_fin)
        """
        # Buscar el \end correspondiente, manejando anidamiento
        # Permitir variantes con * (ej. theorem*)
        env_base = env_type.rstrip('*')
        depth = 1
        current_pos = start_pos
        
        # Patrón más flexible que acepta el entorno con o sin *
        end_pattern = re.compile(
            r'\\(begin|end)\{' + re.escape(env_base) + r'\*?\}', 
            re.IGNORECASE
        )
        
        while depth > 0 and current_pos < len(text):
            match = end_pattern.search(text, current_pos)
            if not match:
                # No se encontró cierre, tomar hasta el final
                return text[start_pos:], len(text)
            
            if match.group(1).lower() == 'begin':
                depth += 1
            else:
                depth -= 1
            
            if depth == 0:
                return text[start_pos:match.start()], match.end()
            
            current_pos = match.end()
        
        return text[start_pos:], len(text)
    
    def extract_proof(self, text: str, start_pos: int) -> Optional[Tuple[str, int]]:
        """
        Intenta extraer un entorno proof que sigue inmediatamente.
        
        Args:
            text: Texto completo
            start_pos: Posición desde donde buscar
            
        Returns:
            Tupla (contenido_proof, posición_fin) o None si no hay proof
        """
        # Buscar \begin{proof} ignorando espacios en blanco
        remaining = text[start_pos:]
        match = self.proof_start_pattern.search(remaining)
        
        if not match:
            return None
        
        # Verificar que solo hay espacios en blanco entre el entorno y el proof
        between = remaining[:match.start()].strip()
        if between:
            return None
        
        # Extraer contenido del proof
        proof_content_start = start_pos + match.end()
        depth = 1
        current_pos = proof_content_start
        
        while depth > 0 and current_pos < len(text):
            begin_match = self.proof_start_pattern.search(text, current_pos)
            end_match = self.proof_end_pattern.search(text, current_pos)
            
            # Determinar cuál viene primero
            next_match = None
            is_begin = False
            
            if begin_match and end_match:
                if begin_match.start() < end_match.start():
                    next_match = begin_match
                    is_begin = True
                else:
                    next_match = end_match
            elif begin_match:
                next_match = begin_match
                is_begin = True
            elif end_match:
                next_match = end_match
            else:
                # No hay más matches
                return text[proof_content_start:], len(text)
            
            if is_begin:
                depth += 1
                current_pos = next_match.end()
            else:
                depth -= 1
                if depth == 0:
                    return text[proof_content_start:next_match.start()], next_match.end()
                current_pos = next_match.end()
        
        return text[proof_content_start:], len(text)
    
    def detect_custom_environments(self, text: str) -> List[str]:
        """
        Detecta entornos personalizados definidos con \newtheorem en el documento.
        
        Args:
            text: Texto LaTeX completo
            
        Returns:
            Lista de nombres de entornos personalizados encontrados
        """
        custom_envs = []
        
        # Patrón para \newtheorem{nombre}{Título}
        newtheorem_pattern = re.compile(
            r'\\newtheorem\*?\{([^}]+)\}(?:\[[^\]]*\])?\{[^}]+\}',
            re.MULTILINE
        )
        
        # Patrón para \theoremstyle y \newtheorem
        theoremstyle_pattern = re.compile(
            r'\\theoremstyle\{[^}]+\}\s*\\newtheorem\*?\{([^}]+)\}',
            re.MULTILINE | re.DOTALL
        )
        
        # Buscar todas las definiciones de \newtheorem
        for match in newtheorem_pattern.finditer(text):
            env_name = match.group(1).strip()
            if env_name and env_name not in self.MATH_ENVIRONMENTS:
                custom_envs.append(env_name)
        
        # Buscar definiciones con \theoremstyle
        for match in theoremstyle_pattern.finditer(text):
            env_name = match.group(1).strip()
            if env_name and env_name not in self.MATH_ENVIRONMENTS and env_name not in custom_envs:
                custom_envs.append(env_name)
        
        return custom_envs
    
    def parse_text(self, text: str, auto_detect_envs: bool = True) -> List[Dict[str, Optional[str]]]:
        """
        Parsea un texto LaTeX y extrae todos los bloques matemáticos.
        
        Args:
            text: Texto LaTeX completo
            auto_detect_envs: Si es True, detecta automáticamente entornos personalizados
            
        Returns:
            Lista de diccionarios con los bloques extraídos
        """
        # Eliminar comentarios primero
        text = self.remove_comments(text)
        
        # Detectar entornos personalizados si está habilitado
        if auto_detect_envs:
            custom_envs = self.detect_custom_environments(text)
            if custom_envs:
                # Reinicializar el parser con los entornos personalizados
                self.__init__(custom_environments=custom_envs)
        
        blocks = []
        pos = 0
        
        while pos < len(text):
            # Buscar siguiente entorno matemático
            match = self.env_pattern.search(text, pos)
            
            if not match:
                break
            
            env_type_raw = match.group(1)  # El nombre del entorno tal como aparece
            env_type = self.normalize_env_type(env_type_raw)  # Nombre normalizado
            title = match.group(2).strip() if match.group(2) else None
            
            # Intentar extraer label justo después del \begin{entorno}[titulo]
            label, content_start = self.extract_label(text, match.end())
            
            # Extraer contenido del entorno usando el nombre raw
            content, content_end = self.extract_environment(text, content_start, env_type_raw)
            
            # Limpiar contenido
            content_clean = self.clean_content(content)
            
            # Solo guardar bloques que tengan contenido relevante
            if not content_clean or len(content_clean.strip()) < 3:
                pos = content_end
                continue
            
            # Extraer referencias del contenido
            content_refs = self.extract_references(content)
            
            # Intentar extraer proof asociado
            proof_result = self.extract_proof(text, content_end)
            proof_clean = None
            proof_refs = []
            next_pos = content_end
            
            if proof_result:
                proof_content, proof_end = proof_result
                proof_clean = self.clean_content(proof_content)
                # Solo guardar la prueba si tiene contenido significativo
                if proof_clean and len(proof_clean.strip()) < 3:
                    proof_clean = None
                else:
                    # Extraer referencias de la prueba
                    proof_refs = self.extract_references(proof_content)
                next_pos = proof_end
            
            # Combinar todas las referencias (contenido + prueba) sin duplicados
            all_refs = content_refs.copy()
            for ref in proof_refs:
                if ref not in all_refs:
                    all_refs.append(ref)
            
            # Crear bloque con label y referencias incluidas
            block = {
                'type': env_type,
                'label': label,
                'title': title,
                'content_latex': content_clean,
                'proof_latex': proof_clean,
                'references': all_refs if all_refs else None
            }
            
            blocks.append(block)
            pos = next_pos
        
        return blocks
    
    def parse_file(self, file_path: str) -> List[Dict[str, Optional[str]]]:
        """
        Parsea un archivo LaTeX.
        
        Args:
            file_path: Ruta al archivo .tex
            
        Returns:
            Lista de bloques matemáticos extraídos
        """
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {file_path}")
        
        if path.suffix.lower() != '.tex':
            raise ValueError(f"El archivo debe tener extensión .tex: {file_path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            text = f.read()
        
        return self.parse_text(text)
    
    def to_json(self, blocks: List[Dict[str, Optional[str]]], indent: int = 2) -> str:
        """
        Convierte los bloques a formato JSON.
        
        Args:
            blocks: Lista de bloques
            indent: Nivel de indentación
            
        Returns:
            String JSON
        """
        return json.dumps(blocks, indent=indent, ensure_ascii=False)


def parse_latex(file_path: str) -> List[Dict[str, Optional[str]]]:
    """
    Función principal para parsear un archivo LaTeX.
    
    Args:
        file_path: Ruta al archivo .tex
        
    Returns:
        Lista de diccionarios con los bloques matemáticos
    """
    parser = LaTeXParser()
    return parser.parse_file(file_path)


def test_parser():
    """Función de prueba con ejemplos de LaTeX."""
    
    test_latex = r"""
\documentclass{article}
\usepackage{amsmath, amsthm}

\newtheorem{theorem}{Teorema}
\newtheorem{lemma}{Lema}
\newtheorem{definition}{Definición}

\begin{document}

% Esto es un comentario que debe ser ignorado

\begin{definition}[Grupo]
Un \textbf{grupo} es un par $(G, \cdot)$ donde $G$ es un conjunto no vacío
y $\cdot: G \times G \to G$ es una operación binaria que satisface:
\begin{enumerate}
    \item Asociatividad: $(a \cdot b) \cdot c = a \cdot (b \cdot c)$ para todo $a, b, c \in G$
    \item Elemento neutro: Existe $e \in G$ tal que $e \cdot a = a \cdot e = a$ para todo $a \in G$
    \item Inversos: Para todo $a \in G$, existe $a^{-1} \in G$ tal que $a \cdot a^{-1} = a^{-1} \cdot a = e$
\end{enumerate}
\end{definition}

\vspace{1cm}

\begin{theorem}[Teorema de Lagrange]
Sea $G$ un grupo finito y $H$ un subgrupo de $G$. Entonces el orden de $H$ 
divide al orden de $G$. Es decir:
$$|G| = |H| \cdot [G:H]$$
donde $[G:H]$ denota el índice de $H$ en $G$.
\end{theorem}

\begin{proof}
Sea $\{g_1H, g_2H, \ldots, g_kH\}$ el conjunto de clases laterales izquierdas 
de $H$ en $G$. Estas clases forman una partición de $G$, y cada clase tiene 
exactamente $|H|$ elementos.

Por tanto, $|G| = k \cdot |H|$, donde $k = [G:H]$ es el número de clases laterales.
\end{proof}

\newpage

\begin{lemma}
Si $G$ es un grupo abeliano, entonces $(ab)^n = a^n b^n$ para todo $a, b \in G$ 
y todo $n \in \mathbb{Z}$.
\end{lemma}

% Este lema no tiene demostración en el documento

\begin{proposition}[Unicidad del Neutro]
En un grupo $(G, \cdot)$, el elemento neutro es único.
\end{proposition}

\begin{proof}
Supongamos que $e$ y $e'$ son ambos elementos neutros. Entonces:
$$e = e \cdot e' = e'$$
donde la primera igualdad usa que $e'$ es neutro, y la segunda que $e$ es neutro.
\end{proof}

\end{document}
"""
    
    print("=" * 80)
    print("AVID LaTeX Parser - Test de Funcionalidad")
    print("=" * 80)
    print()
    
    parser = LaTeXParser()
    blocks = parser.parse_text(test_latex)
    
    print(f"Bloques extraídos: {len(blocks)}\n")
    
    for i, block in enumerate(blocks, 1):
        print(f"{'─' * 80}")
        print(f"Bloque {i}: {block['type'].upper()}")
        print(f"{'─' * 80}")
        
        if block['title']:
            print(f"Título: {block['title']}")
        
        print(f"\nContenido:")
        print(block['content_latex'][:200] + "..." if len(block['content_latex']) > 200 else block['content_latex'])
        
        if block['proof_latex']:
            print(f"\nPrueba vinculada: ✓")
            print(block['proof_latex'][:200] + "..." if len(block['proof_latex']) > 200 else block['proof_latex'])
        else:
            print(f"\nPrueba vinculada: ✗")
        
        print()
    
    # Mostrar JSON
    print("=" * 80)
    print("Salida JSON:")
    print("=" * 80)
    print(parser.to_json(blocks))
    
    # Verificar casos específicos
    print("\n" + "=" * 80)
    print("Verificación de Funcionalidad:")
    print("=" * 80)
    
    # Verificar que se encontraron los bloques esperados
    assert len(blocks) == 4, f"Se esperaban 4 bloques, se encontraron {len(blocks)}"
    print("✓ Número correcto de bloques extraídos")
    
    # Verificar definición
    assert blocks[0]['type'] == 'definition', "El primer bloque debe ser una definición"
    assert blocks[0]['title'] == 'Grupo', "La definición debe tener título 'Grupo'"
    assert blocks[0]['proof_latex'] is None, "La definición no debe tener prueba"
    print("✓ Definición extraída correctamente")
    
    # Verificar teorema con prueba
    assert blocks[1]['type'] == 'theorem', "El segundo bloque debe ser un teorema"
    assert blocks[1]['title'] == 'Teorema de Lagrange', "El teorema debe tener el título correcto"
    assert blocks[1]['proof_latex'] is not None, "El teorema debe tener prueba vinculada"
    print("✓ Teorema con prueba vinculada correctamente")
    
    # Verificar lema sin prueba
    assert blocks[2]['type'] == 'lemma', "El tercer bloque debe ser un lema"
    assert blocks[2]['proof_latex'] is None, "El lema no debe tener prueba"
    print("✓ Lema sin prueba extraído correctamente")
    
    # Verificar proposición con prueba
    assert blocks[3]['type'] == 'proposition', "El cuarto bloque debe ser una proposición"
    assert blocks[3]['title'] == 'Unicidad del Neutro', "La proposición debe tener el título correcto"
    assert blocks[3]['proof_latex'] is not None, "La proposición debe tener prueba vinculada"
    print("✓ Proposición con prueba vinculada correctamente")
    
    print("\n✓ Todas las pruebas pasaron exitosamente!")


if __name__ == '__main__':
    test_parser()
