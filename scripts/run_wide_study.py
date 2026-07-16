"""Wide Study v2 — Fixed: auto-exclusion, v1 cache lookup, explicit skip reasons."""
import sys, os, csv, json, logging, shutil, time, re, hashlib

sys.path.insert(0, '.')
from dotenv import load_dotenv; load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

import yaml
with open('config/control_candidates.yaml', encoding='utf-8') as f:
    candidates = yaml.safe_load(f)
with open('config/wide_study.yaml', encoding='utf-8') as f:
    config = yaml.safe_load(f)

T_STRONG = config['thresholds']['strong_match']['theoremsearch_min_score']

# ── Build complete cache map from meta files ─────────────────────────
CACHE = 'cache/retracted_dataset'
cache_map = {}  # arxiv_id_v1 → src_dir

for fn in os.listdir(CACHE):
    if not fn.endswith('.json'):
        continue
    try:
        with open(os.path.join(CACHE, fn)) as f:
            data = json.load(f)
        v1 = data.get('arxiv_id_v1', data.get('arxiv_id', ''))
        if not v1:
            continue
        m = re.search(r'meta_([a-f0-9]+)\.json', fn)
        if not m:
            continue
        h = m.group(1)
        if fn.startswith('ctrl_meta_'):
            src_dir = f'{CACHE}/ctrl_src_{h}'
        else:
            src_dir = f'{CACHE}/src_{h}'
        if os.path.isdir(src_dir):
            cache_map[v1] = src_dir
    except:
        pass

logging.info("Cache map: %d entries", len(cache_map))

# ── Build paper list with theorem extraction ─────────────────────────
papers = []
for pair in candidates['pairs']:
    # Retracted
    papers.append({
        'arxiv_id': pair['retracted_arxiv_id'],
        'role': 'retracted',
        'title': pair.get('retracted_title', ''),
        'paired_with': pair['controls'][0]['arxiv_id'] if pair.get('controls') else None,
    })
    # First control
    if pair.get('controls'):
        ctrl = pair['controls'][0]
        papers.append({
            'arxiv_id': ctrl['arxiv_id'],
            'role': 'control',
            'title': ctrl.get('title', ''),
            'paired_with': pair['retracted_arxiv_id'],
        })

# Extract theorem text for each paper
for p in papers:
    aid = p['arxiv_id']
    base = re.sub(r'v\d+$', '', aid)
    v1 = base + 'v1'
    
    src_dir = cache_map.get(v1)
    if not src_dir:
        # Try hash of the ID itself
        ck = hashlib.sha256(aid.encode()).hexdigest()[:16]
        for prefix in ['src_', 'ctrl_src_']:
            test = os.path.join(CACHE, f'{prefix}{ck}')
            if os.path.isdir(test):
                src_dir = test
                break
    
    if not src_dir:
        p['theorem'] = None
        p['skip_reason'] = 'source_not_cached'
        continue
    
    # Find tex file > 1KB
    tex_path = None
    for root, dirs, files in os.walk(src_dir):
        for f in files:
            if f.endswith('.tex'):
                path = os.path.join(root, f)
                if os.path.getsize(path) > 1000:
                    tex_path = path
                    break
        if tex_path:
            break
    
    if not tex_path:
        p['theorem'] = None
        p['skip_reason'] = 'no_tex_file'
        continue
    
    with open(tex_path, encoding='utf-8', errors='replace') as f:
        content = f.read()
    
    doc_start = content.find(r'\begin{document}')
    if doc_start < 0:
        doc_start = 0
    after_doc = content[doc_start:]
    
    theorem_text = None
    for env in ['theorem', 'proposition', 'lemma', 'corollary']:
        pat = re.compile(r'\\begin\{' + env + r'\}(.*?)\\end\{' + env + r'\}', re.DOTALL)
        m = pat.search(after_doc)
        if m:
            body = m.group(1).strip()
            body = re.sub(r'\\label\{[^}]*\}', '', body).strip()
            body = ' '.join(body.split())
            theorem_text = body[:1000]
            break
    
    if theorem_text:
        p['theorem'] = theorem_text
        p['skip_reason'] = None
    else:
        p['theorem'] = None
        p['skip_reason'] = 'no_theorem_env'

# Counts
with_text = sum(1 for p in papers if p['theorem'])
without_text = sum(1 for p in papers if not p['theorem'])
logging.info("Papers with text: %d, without: %d", with_text, without_text)
for p in papers:
    if not p['theorem']:
        logging.info("  SKIP %s (%s): %s", p['arxiv_id'], p['role'], p['skip_reason'])

# ── Run TheoremSearch ────────────────────────────────────────────────
csv_path = 'results/wide_study.csv'
fieldnames = [
    'arxiv_id', 'role', 'paired_with', 'title',
    'top1_score', 'top1_title', 'top1_arxiv_id',
    'top3_scores', 'top10_json',
    'strong_match', 'strong_match_reason',
    'skip_reason',
]

rows = []
for i, p in enumerate(papers):
    aid = p['arxiv_id']
    row = {
        'arxiv_id': aid, 'role': p['role'],
        'paired_with': p.get('paired_with', ''),
        'title': (p.get('title', '') or '')[:150],
    }
    
    if not p['theorem']:
        row['skip_reason'] = p.get('skip_reason', 'unknown')
        row['strong_match'] = 'false'
        reason = row['skip_reason']
        row['strong_match_reason'] = 'skip: ' + reason
        rows.append(row)
        continue
    
    logging.info('=== %s (%s) [%d/%d] ===', aid, p['role'], i+1, len(papers))
    
    try:
        from src.novelty.theoremsearch import search_theoremsearch
        # FIX: exclude own arxiv_id
        results = search_theoremsearch(p['theorem'][:1000], top_k=10, exclude_arxiv_ids=[aid])
        
        top1 = results[0] if results else None
        row['top1_score'] = round(top1.similarity_score, 4) if top1 else 0
        row['top1_title'] = (top1.title or '')[:150] if top1 else ''
        row['top1_arxiv_id'] = (top1.arxiv_id or '') if top1 else ''
        
        top3 = [round(r.similarity_score, 4) for r in results[:3]]
        row['top3_scores'] = json.dumps(top3)
        
        top10 = []
        for r in results[:10]:
            top10.append({
                'title': (r.title or '')[:100],
                'score': round(r.similarity_score, 4),
                'arxiv_id': r.arxiv_id or '',
            })
        row['top10_json'] = json.dumps(top10)
        
        strong = row['top1_score'] >= T_STRONG
        row['strong_match'] = str(strong).lower()
        row['strong_match_reason'] = (
            f'top-1 score {row["top1_score"]} >= {T_STRONG}'
            if strong else f'top-1 score {row["top1_score"]} < {T_STRONG}'
        )
        
        # Verify self-exclusion worked
        if top1 and top1.arxiv_id:
            top1_base = re.sub(r'v\d+$', '', top1.arxiv_id)
            query_base = re.sub(r'v\d+$', '', aid)
            if top1_base == query_base:
                logging.error('  ⚠️ SELF-MATCH STILL PRESENT: %s matched itself!', aid)
        
        logging.info('  top-1: %.4f "%s"', row['top1_score'], row['top1_title'][:60])
        
    except Exception as e:
        logging.error('  Error: %s', e)
        row['skip_reason'] = f'error: {str(e)[:100]}'
        row['strong_match'] = 'false'
        row['strong_match_reason'] = f'error: {str(e)[:100]}'
    
    rows.append(row)
    
    # Atomic backup after each paper
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)
    shutil.copy(csv_path, csv_path + '.bak')

# ── Summary ──────────────────────────────────────────────────────────
with_text = sum(1 for r in rows if not r.get('skip_reason') or 'error' in str(r.get('skip_reason','')))
strong = sum(1 for r in rows if r.get('strong_match') == 'true')
ret_with = sum(1 for r in rows if r['role'] == 'retracted' and not r.get('skip_reason'))
ctrl_with = sum(1 for r in rows if r['role'] == 'control' and not r.get('skip_reason'))
ret_strong = sum(1 for r in rows if r['role'] == 'retracted' and r.get('strong_match') == 'true')
ctrl_strong = sum(1 for r in rows if r['role'] == 'control' and r.get('strong_match') == 'true')

logging.info('=== DONE ===')
logging.info('Evaluable: %d/%d (ret=%d, ctrl=%d)', with_text, len(rows), ret_with, ctrl_with)
logging.info('Strong matches: %d (ret=%d, ctrl=%d)', strong, ret_strong, ctrl_strong)
logging.info('Skipped: %d', len(rows) - with_text)
for r in rows:
    if r.get('skip_reason') and 'error' not in str(r.get('skip_reason','')):
        logging.info('  SKIP %s (%s): %s', r['arxiv_id'], r['role'], r['skip_reason'])
