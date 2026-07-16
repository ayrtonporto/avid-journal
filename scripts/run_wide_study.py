"""Wide Study — TheoremSearch on 52 papers with backup after each paper."""
import sys, os, csv, json, logging, shutil, time, re

sys.path.insert(0, '.')
from dotenv import load_dotenv; load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

# Load paper list from wide_study_statements.md
with open('docs/wide_study_statements.md', encoding='utf-8') as f:
    content = f.read()

import yaml
with open('config/control_candidates.yaml', encoding='utf-8') as f:
    candidates = yaml.safe_load(f)

with open('config/wide_study.yaml', encoding='utf-8') as f:
    config = yaml.safe_load(f)

T_STRONG = config['thresholds']['strong_match']['theoremsearch_min_score']

# Build paper list with theorem text
papers = []
for pair in candidates['pairs']:
    ret_aid = pair['retracted_arxiv_id']
    ctrl = pair['controls'][0] if pair.get('controls') else None
    
    papers.append({
        'arxiv_id': ret_aid,
        'role': 'retracted',
        'title': pair.get('retracted_title', ''),
        'paired_with': ctrl['arxiv_id'] if ctrl else None,
    })
    if ctrl:
        papers.append({
            'arxiv_id': ctrl['arxiv_id'],
            'role': 'control',
            'title': ctrl.get('title', ''),
            'paired_with': ret_aid,
        })

# Extract theorem text from the statements doc
current_aid = None
current_text = ''
theorem_map = {}
in_code = False
for line in content.split('\n'):
    m = re.match(r'## \d+\. [🔴🔵] (\S+) \(', line)
    if m:
        if current_aid and current_text.strip():
            theorem_map[current_aid] = current_text.strip()
        current_aid = m.group(1)
        current_text = ''
        in_code = False
    elif line.strip() == '```latex':
        in_code = True
    elif line.strip() == '```':
        in_code = False
    elif in_code and current_aid:
        current_text += line + '\n'

if current_aid and current_text.strip():
    theorem_map[current_aid] = current_text.strip()

# CSV setup
csv_path = 'results/wide_study.csv'
csv_bak = csv_path + '.bak'
fieldnames = [
    'arxiv_id', 'role', 'paired_with', 'title',
    'top1_score', 'top1_title', 'top1_arxiv_id',
    'top3_scores', 'top10_json',
    'strong_match', 'strong_match_reason',
]

rows = []
for i, p in enumerate(papers):
    aid = p['arxiv_id']
    theorem_text = theorem_map.get(aid, '')
    
    if not theorem_text or '⚠️' in theorem_text:
        rows.append({
            'arxiv_id': aid, 'role': p['role'],
            'paired_with': p.get('paired_with', ''),
            'title': (p.get('title', '') or '')[:100],
            'strong_match': 'false',
            'strong_match_reason': 'no theorem text available',
        })
        continue
    
    logging.info('=== %s (%s) [%d/%d] ===', aid, p['role'], i+1, len(papers))
    
    row = {
        'arxiv_id': aid, 'role': p['role'],
        'paired_with': p.get('paired_with', ''),
        'title': (p.get('title', '') or '')[:150],
    }
    
    try:
        from src.novelty.theoremsearch import search_theoremsearch
        results = search_theoremsearch(theorem_text[:1000], top_k=10)
        
        top1 = results[0] if results else {}
        row['top1_score'] = round(top1.get('score', 0), 4)
        row['top1_title'] = (top1.get('title', '') or '')[:150]
        row['top1_arxiv_id'] = top1.get('arxiv_id', '') or ''
        
        top3 = [round(r.get('score', 0), 4) for r in results[:3]]
        row['top3_scores'] = json.dumps(top3)
        
        top10 = []
        for r in results[:10]:
            top10.append({
                'title': (r.get('title', '') or '')[:100],
                'score': round(r.get('score', 0), 4),
                'arxiv_id': r.get('arxiv_id', '') or '',
            })
        row['top10_json'] = json.dumps(top10)
        
        strong = row['top1_score'] >= T_STRONG
        row['strong_match'] = str(strong).lower()
        row['strong_match_reason'] = f'top-1 score {row["top1_score"]} >= {T_STRONG}' if strong else f'top-1 score {row["top1_score"]} < {T_STRONG}'
        
        logging.info('  top-1: %.4f "%s"', row['top1_score'], row['top1_title'][:60])
        
    except Exception as e:
        logging.error('  Error: %s', e)
        row['strong_match'] = 'false'
        row['strong_match_reason'] = f'error: {str(e)[:100]}'
    
    rows.append(row)
    
    # Atomic backup after each paper
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)
    shutil.copy(csv_path, csv_bak)

strong = sum(1 for r in rows if r.get('strong_match') == 'true')
logging.info('=== DONE: %d papers, %d strong matches ===', len(rows), strong)
