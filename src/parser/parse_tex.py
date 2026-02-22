#!/usr/bin/env python3
"""
AVID LaTeX Parser - CLI
=======================
Interfaz de línea de comandos para parsear archivos LaTeX.

Uso:
    python parse_tex.py input.tex                    # Muestra resumen en consola
    python parse_tex.py input.tex -o output.json     # Exporta a JSON
    python parse_tex.py input.tex --stats            # Muestra estadísticas
    python parse_tex.py input.tex --validate         # Valida bloques extraídos
"""

import argparse
import json
import sys
from pathlib import Path
from latex_parser import LaTeXParser


def print_summary(blocks):
    """Imprime resumen de bloques extraídos."""
    if not blocks:
        print("⚠️  No se encontraron bloques matemáticos en el archivo.")
        return
    
    print(f"\n{'=' * 80}")
    print(f"RESUMEN: {len(blocks)} bloques extraídos")
    print(f"{'=' * 80}\n")
    
    for i, block in enumerate(blocks, 1):
        title_str = f" [{block['title']}]" if block['title'] else ""
        proof_str = " ✓ Con prueba" if block['proof_latex'] else ""
        label_str = f" (label: {block['label']})" if block['label'] else ""
        
        print(f"{i}. {block['type'].upper()}{title_str}{label_str}{proof_str}")
        
        # Mostrar referencias si existen
        if block['references']:
            print(f"   Referencias: {', '.join(block['references'])}")
        
        # Mostrar preview del contenido
        content_preview = block['content_latex'][:120]
        if len(block['content_latex']) > 120:
            content_preview += "..."
        print(f"   {content_preview}\n")


def print_dependencies(blocks):
    """Muestra el grafo de dependencias entre bloques."""
    if not blocks:
        print("⚠️  No hay bloques para analizar.")
        return
    
    print(f"\n{'=' * 80}")
    print("GRAFO DE DEPENDENCIAS")
    print(f"{'=' * 80}\n")
    
    # Crear mapa de labels
    label_map = {}
    for i, block in enumerate(blocks):
        if block['label']:
            label_map[block['label']] = {
                'index': i + 1,
                'type': block['type'],
                'title': block['title']
            }
    
    print(f"Bloques con label: {len(label_map)}/{len(blocks)}")
    
    # Contar bloques con referencias
    with_refs = sum(1 for b in blocks if b['references'])
    print(f"Bloques con referencias: {with_refs}/{len(blocks)}\n")
    
    if with_refs == 0:
        print("No se encontraron dependencias entre bloques.")
        return
    
    # Mostrar dependencias
    print("Dependencias detectadas:\n")
    has_dependencies = False
    
    for i, block in enumerate(blocks, 1):
        if block['references']:
            has_dependencies = True
            
            # Encabezado del bloque
            title_str = f" [{block['title']}]" if block['title'] else ""
            label_str = f" ({block['label']})" if block['label'] else ""
            print(f"{i}. {block['type'].upper()}{title_str}{label_str}")
            print(f"   ↓ depende de:")
            
            # Mostrar cada dependencia
            for ref in block['references']:
                if ref in label_map:
                    dep = label_map[ref]
                    dep_title = f" [{dep['title']}]" if dep['title'] else ""
                    print(f"      → Bloque {dep['index']}: {dep['type'].upper()}{dep_title}")
                else:
                    print(f"      → ⚠️  {ref} (no encontrado en documento)")
            
            print()
    
    if not has_dependencies:
        print("No se encontraron dependencias entre bloques.")
    
    print()


def print_statistics(blocks):
    """Imprime estadísticas detalladas de los bloques."""
    if not blocks:
        print("⚠️  No hay bloques para analizar.")
        return
    
    print(f"\n{'=' * 80}")
    print("ESTADÍSTICAS")
    print(f"{'=' * 80}\n")
    
    # Conteo total
    print(f"Total de bloques: {len(blocks)}")
    
    # Por tipo
    by_type = {}
    for block in blocks:
        by_type[block['type']] = by_type.get(block['type'], 0) + 1
    
    print("\nDistribución por tipo:")
    for tipo, count in sorted(by_type.items(), key=lambda x: -x[1]):
        percentage = (count / len(blocks)) * 100
        print(f"  {tipo.capitalize():<15} {count:>3} ({percentage:>5.1f}%)")
    
    # Con/sin título
    with_title = sum(1 for b in blocks if b['title'])
    print(f"\nCon título: {with_title}/{len(blocks)} ({with_title/len(blocks)*100:.1f}%)")
    
    # Con/sin label
    with_label = sum(1 for b in blocks if b['label'])
    print(f"Con label: {with_label}/{len(blocks)} ({with_label/len(blocks)*100:.1f}%)")
    
    # Con/sin prueba
    with_proof = sum(1 for b in blocks if b['proof_latex'])
    print(f"Con prueba: {with_proof}/{len(blocks)} ({with_proof/len(blocks)*100:.1f}%)")
    
    # Con referencias
    with_refs = sum(1 for b in blocks if b['references'])
    print(f"Con referencias: {with_refs}/{len(blocks)} ({with_refs/len(blocks)*100:.1f}%)")
    
    # Total de referencias
    total_refs = sum(len(b['references']) for b in blocks if b['references'])
    if total_refs > 0:
        print(f"Total de referencias: {total_refs}")
    
    # Longitudes promedio
    avg_content = sum(len(b['content_latex']) for b in blocks) / len(blocks)
    proof_blocks = [b for b in blocks if b['proof_latex']]
    avg_proof = sum(len(b['proof_latex']) for b in proof_blocks) / len(proof_blocks) if proof_blocks else 0
    
    print(f"\nLongitud promedio del contenido: {avg_content:.0f} caracteres")
    if avg_proof > 0:
        print(f"Longitud promedio de pruebas: {avg_proof:.0f} caracteres")
    
    print()


def validate_blocks(blocks):
    """Valida bloques y reporta problemas potenciales."""
    if not blocks:
        print("⚠️  No hay bloques para validar.")
        return
    
    print(f"\n{'=' * 80}")
    print("VALIDACIÓN")
    print(f"{'=' * 80}\n")
    
    issues = []
    warnings = []
    
    for i, block in enumerate(blocks, 1):
        # Verificar que teoremas/lemas/proposiciones tengan prueba
        if block['type'] in ['theorem', 'lemma', 'proposition', 'corollary']:
            if not block['proof_latex']:
                issues.append(f"Bloque {i} ({block['type']}): Sin demostración")
        
        # Verificar que tengan contenido matemático
        has_math = any(marker in block['content_latex'] for marker in ['$', '\\[', '\\(', '\\begin{equation'])
        if not has_math:
            warnings.append(f"Bloque {i} ({block['type']}): Sin fórmulas matemáticas")
        
        # Verificar longitud mínima
        if len(block['content_latex'].strip()) < 20:
            warnings.append(f"Bloque {i} ({block['type']}): Contenido muy corto")
        
        # Verificar título para teoremas importantes
        if block['type'] in ['theorem', 'proposition'] and not block['title']:
            warnings.append(f"Bloque {i} ({block['type']}): Sin título")
    
    # Reportar resultados
    if not issues and not warnings:
        print("✅ Todos los bloques pasaron la validación")
    else:
        if issues:
            print(f"❌ PROBLEMAS ENCONTRADOS ({len(issues)}):")
            for issue in issues:
                print(f"  • {issue}")
            print()
        
        if warnings:
            print(f"⚠️  ADVERTENCIAS ({len(warnings)}):")
            for warning in warnings:
                print(f"  • {warning}")
    
    print()


def main():
    parser = argparse.ArgumentParser(
        description='AVID LaTeX Parser - Extrae bloques matemáticos de archivos .tex',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  python parse_tex.py documento.tex
  python parse_tex.py documento.tex -o salida.json
  python parse_tex.py documento.tex --stats --validate
  python parse_tex.py documento.tex -o salida.json --pretty
        """
    )
    
    parser.add_argument(
        'input',
        type=str,
        help='Archivo .tex de entrada'
    )
    
    parser.add_argument(
        '-o', '--output',
        type=str,
        help='Archivo JSON de salida (opcional)'
    )
    
    parser.add_argument(
        '--stats',
        action='store_true',
        help='Mostrar estadísticas detalladas'
    )
    
    parser.add_argument(
        '--validate',
        action='store_true',
        help='Validar bloques extraídos'
    )
    
    parser.add_argument(
        '--deps',
        action='store_true',
        help='Mostrar grafo de dependencias entre bloques'
    )
    
    parser.add_argument(
        '--pretty',
        action='store_true',
        help='Formatear JSON con indentación (solo con -o)'
    )
    
    parser.add_argument(
        '--no-auto-detect',
        action='store_true',
        help='Desactivar detección automática de entornos personalizados'
    )
    
    args = parser.parse_args()
    
    # Verificar que el archivo existe
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"❌ Error: Archivo no encontrado: {args.input}", file=sys.stderr)
        sys.exit(1)
    
    if input_path.suffix.lower() != '.tex':
        print(f"⚠️  Advertencia: El archivo no tiene extensión .tex", file=sys.stderr)
    
    # Parsear archivo
    print(f"📄 Parseando: {input_path.name}")
    
    try:
        latex_parser = LaTeXParser()
        
        # Leer archivo
        with open(input_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parsear con o sin auto-detección
        blocks = latex_parser.parse_text(content, auto_detect_envs=not args.no_auto_detect)
        
        print(f"✓ Completado: {len(blocks)} bloques extraídos\n")
        
    except Exception as e:
        print(f"❌ Error al parsear archivo: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Mostrar resumen por defecto
    if not args.stats and not args.validate and not args.deps:
        print_summary(blocks)
    
    # Mostrar estadísticas si se solicita
    if args.stats:
        print_statistics(blocks)
    
    # Mostrar dependencias si se solicita
    if args.deps:
        print_dependencies(blocks)
    
    # Validar si se solicita
    if args.validate:
        validate_blocks(blocks)
    
    # Exportar a JSON si se especifica
    if args.output:
        output_path = Path(args.output)
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                indent = 2 if args.pretty else None
                json.dump(blocks, f, indent=indent, ensure_ascii=False)
            
            print(f"💾 JSON exportado a: {output_path}")
            print(f"   Tamaño: {output_path.stat().st_size:,} bytes\n")
            
        except Exception as e:
            print(f"❌ Error al exportar JSON: {e}", file=sys.stderr)
            sys.exit(1)


if __name__ == '__main__':
    main()
