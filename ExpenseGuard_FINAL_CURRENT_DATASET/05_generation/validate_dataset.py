from pathlib import Path
import json, csv
from collections import Counter
ROOT=Path(__file__).resolve().parents[1]
def jl(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
cases=jl(ROOT/'02_cases'/'all_cases.jsonl'); gt=jl(ROOT/'04_ground_truth_PRIVATE'/'ground_truth.jsonl')
meta=json.loads((ROOT/'01_policy_corpus'/'policy_metadata.json').read_text(encoding='utf-8'))
valid_policy={x for d in meta for x in d['clause_ids']}
errors=[]
if len(cases)!=120: errors.append(f'case count {len(cases)} != 120')
if len(gt)!=120: errors.append(f'gt count {len(gt)} != 120')
if len({c['case_id'] for c in cases})!=120: errors.append('duplicate case IDs')
if {c['case_id'] for c in cases}!={g['case_id'] for g in gt}: errors.append('case/gt ID mismatch')
for c in cases:
    for k in ['employee_id','transaction_date','submission_date','bill','employee_description','project_id','split']:
        if k not in c: errors.append(f'{c.get("case_id")}: missing {k}')
    forbidden={'expected_decision','required_policy_ids','architecture_group','case_family','acceptable_tool_paths','duplicate_status','split_transaction_status'}
    leak=forbidden.intersection(c)
    if leak: errors.append(f'{c["case_id"]}: leakage {sorted(leak)}')
for g in gt:
    bad=[p for p in g['required_policy_ids'] if p not in valid_policy]
    if bad: errors.append(f'{g["case_id"]}: unknown policies {bad}')
    req=['expected_decision','case_family','architecture_group','missing_fields','manual_touch_required','duplicate_status','split_transaction_status','workflow_sufficient','agent_required_candidate']
    for k in req:
        if k not in g: errors.append(f'{g["case_id"]}: missing gt {k}')
# distribution checks
split=Counter(c['split'] for c in cases)
if split!=Counter({'DEVELOPMENT':60,'FINAL_TEST':40,'VALIDATION':20}): errors.append(f'bad split {split}')
arch=Counter(g['architecture_group'] for g in gt)
if arch!=Counter({'A_SELF_CONTAINED':65,'B_WORKFLOW':40,'C_AGENT_DYNAMIC':15}): errors.append(f'bad architecture {arch}')
if sum(1 for g in gt if g['split']=='FINAL_TEST' and g['independent_challenge'])!=10: errors.append('final challenge count != 10')
# every agent candidate must be non-workflow and have branch trigger
for g in gt:
    if g['architecture_group']=='C_AGENT_DYNAMIC':
        if g['workflow_sufficient']: errors.append(f'{g["case_id"]}: agent marked workflow sufficient')
        if not g['branch_trigger']: errors.append(f'{g["case_id"]}: missing branch trigger')
# linked historical IDs exist
prev={r['expense_id'] for r in csv.DictReader(open(ROOT/'03_enterprise_data'/'previous_expenses.csv',encoding='utf-8'))}
for g in gt:
    for x in g['matched_expense_ids']+g['related_expense_ids']:
        if x not in prev: errors.append(f'{g["case_id"]}: linked previous expense missing {x}')
print('Architecture:',arch)
print('Outcomes:',Counter(g['expected_decision'] for g in gt))
print('Families:',Counter(g['case_family'] for g in gt))
print('Splits:',split)
print('Challenge cases:',sum(1 for g in gt if g['independent_challenge']))
if errors:
    print('\nFAIL')
    for e in errors[:100]: print('-',e)
    raise SystemExit(1)
print('\nPASS - all integrity/leakage/distribution checks succeeded.')
