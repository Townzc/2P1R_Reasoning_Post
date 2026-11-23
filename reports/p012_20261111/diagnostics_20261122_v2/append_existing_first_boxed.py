"""Copy the already published first-boxed diagnostics required by amendment6."""
import hashlib
import json
from pathlib import Path
import zipfile

HERE = Path(__file__).resolve().parent
BASE = Path('reports/p012_20261111/registered_analysis_169754c4_v1')
read = lambda p:json.loads(Path(p).read_text())
manifest = read(BASE/'INPUT_MANIFEST.json')
locations = {x['restore_path']:x for x in read(BASE/'SOURCE_LOCATIONS.json')}
inputs = read(HERE/'INPUT_MANIFEST.json')['endpoints']
rows = read(HERE/'RESULTS.json')['rows']
by_id = {x['endpoint_id']:x for x in inputs}
output=[]
for row in rows:
    if row['length_cap_rate'] <= .2:
        continue
    spec = manifest['settings'][row['setting']]['by_seed'][str(row['seed'])][row['cell']]['first_boxed_diagnostic']
    src = locations[spec['path']]['public_source']
    with zipfile.ZipFile(src['archive']) as z:
        value = z.read(src['member'])
    assert hashlib.sha256(value).hexdigest() == spec['sha256']
    diag=json.loads(value)
    assert diag['raw_sha256'] == by_id[row['endpoint_id']]['sources']['raw']['sha256']
    assert diag['responses'] == row['responses']
    assert diag['length_capped'] == row['length_cap_count']
    output.append({'endpoint_id':row['endpoint_id'],'model':row['model'],'seed':row['seed'],
        'cell':row['cell'],'cap_rate':row['length_cap_rate'],'registered_accuracy':row['accuracy'],
        'first_boxed_accuracy':diag['first_boxed_accuracy'],
        'source':{**src,'sha256':spec['sha256']}})
assert len(output)==7
with (HERE/'FIRST_BOXED_APPENDIX.json').open('x') as f:
    json.dump({'source_policy':'copy existing frozen diagnostics only; no rescoring', 'rows':output},f,indent=2)
    f.write('\n')
text=['','依修订 6，撞上限超过 20% 的七格另并列已有首个 boxed 答案诊断；两列均以完整 MATH 5,000 为分母，登记标签不变。', '',
      '| 模型/任务 | 格 | seed | 撞上限 % | 登记准确率 % | 已有首个 boxed 诊断 % |',
      '|---|---|---:|---:|---:|---:|']
for x in output:
    text.append(f"| {x['model'].split('/')[-1]} / MATH | {x['cell']} | {x['seed']} | {100*x['cap_rate']:.2f} | {100*x['registered_accuracy']:.2f} | {100*x['first_boxed_accuracy']:.2f} |")
table=HERE/'TABLE.md'
assert '依修订 6，' not in table.read_text()
with table.open('a') as f:
    f.write('\n'.join(text)+'\n')
print('Appended seven existing first-boxed diagnostics; no scoring call.')
