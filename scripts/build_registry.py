"""Rebuild compact run registry from immutable run records, including failures."""
import json
from pathlib import Path

entries=[]
for directory in sorted(Path('runs').iterdir()):
    receipt_path=directory/'resource_receipt.json'
    if not receipt_path.exists(): continue
    receipt=json.loads(receipt_path.read_text())
    def read(name):
        p=directory/name
        return json.loads(p.read_text()) if p.exists() else {}
    manifest, metrics, budget=read('run_manifest.json'),read('metrics.json'),read('actual_budget.json')
    valid=not (directory/'INVALIDATED.md').exists()
    entries.append({'run_id':directory.name,'status':receipt['status'],'evidence_valid':valid,
        'git_commit':manifest.get('git_commit'),'config':manifest.get('config'),
        'model':manifest.get('model'),'charged_gpu_seconds':receipt['charged_seconds'],
        'overfit_passed':metrics.get('overfit_passed') if valid else None,
        'steps':metrics.get('steps'), 'supervised_response_tokens':budget.get('supervised_response_tokens'),
        'train_accuracy':metrics.get('train',{}).get('accuracy_macro') if valid else None,
        'dev_accuracy':metrics.get('dev',{}).get('accuracy_macro') if valid else None,
        'throughput':metrics.get('throughput'), 'exception_type':manifest.get('exception_type'),
        'records':str(directory)})
report={'scope':'engineering experiments only; no treatment-effect evidence',
        'charged_gpu_seconds':sum(e['charged_gpu_seconds'] for e in entries),'runs':entries}
Path('reports/run_registry.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'runs':len(entries),'charged_gpu_seconds':report['charged_gpu_seconds']}))
