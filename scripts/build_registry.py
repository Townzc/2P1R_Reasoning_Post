"""Rebuild compact run registry from immutable run records, including failures."""
import json
from pathlib import Path

def build_registry(run_root=Path('runs')):
    entries=[]
    for directory in sorted(Path(run_root).iterdir()):
        receipt_path=directory/'resource_receipt.json'
        if not receipt_path.exists(): continue
        receipt=json.loads(receipt_path.read_text())
        def read(name):
            p=directory/name
            return json.loads(p.read_text()) if p.exists() else {}
        manifest,metrics,budget=read('run_manifest.json'),read('metrics.json'),read('actual_budget.json')
        valid=not (directory/'INVALIDATED.md').exists(); history=directory/'train_history.jsonl'
        steps=metrics.get('steps')
        if steps is None and history.exists(): steps=sum(bool(line.strip()) for line in history.read_text().splitlines())
        entry={'run_id':directory.name,'status':receipt['status'],'evidence_valid':valid,
            'git_commit':manifest.get('git_commit') or manifest.get('source_commit'),'config':manifest.get('config'),
            'mode':manifest.get('config',{}).get('mode'),'arm':manifest.get('config',{}).get('arm'),
            'model':manifest.get('model'),'charged_gpu_seconds':receipt['charged_seconds'],
            'overfit_passed':metrics.get('overfit_passed',metrics.get('engineering_gate',{}).get('passed')) if valid else None,
            'steps':steps,'supervised_response_tokens':budget.get('supervised_response_tokens'),
            'train_accuracy':metrics.get('train',{}).get('accuracy_macro') if valid else None,
            'train_sample16_accuracy':metrics.get('train_sample16',{}).get('accuracy_macro') if valid else None,
            'dev_accuracy':metrics.get('dev',{}).get('accuracy_macro') if valid else None,
            'dev_broad_accuracy':metrics.get('dev_broad',{}).get('accuracy_macro') if valid else None,
            'dev_sampled_pass_at_k':metrics.get('dev_sampled',{}).get('pass_at_k') if valid else None,
            'pilot_gate':metrics.get('pilot_gate') if valid else None,'throughput':metrics.get('throughput'),
            'exception_type':manifest.get('exception_type'),'records':str(directory)}
        if manifest.get('phase') in ('E011','E012'):
            entry['relation_diagnostic']={'phase':manifest['phase'],'engineering_gate':metrics.get('engineering_gate'),
                'train':metrics.get('train'),'dev':metrics.get('dev_by_view',metrics.get('dev')),
                'reference_measurement':metrics.get('teacher_forced_train',metrics.get('train_reference_nll')),
                'scope':'engineering_learning_measurements_not_scientific_treatment_comparison'}
        entries.append(entry)
    return {'scope':'Engineering checks and restricted development-only pilot runs; calibration is not a treatment comparison, and one seed does not establish a population effect.',
            'charged_gpu_seconds':sum(e['charged_gpu_seconds'] for e in entries),'runs':entries}


if __name__=='__main__':
    report=build_registry(); Path('reports/run_registry.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'runs':len(report['runs']),'charged_gpu_seconds':report['charged_gpu_seconds']}))
