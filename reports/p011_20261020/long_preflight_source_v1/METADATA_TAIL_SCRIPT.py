from pathlib import Path
from datetime import datetime,timezone
import ast,hashlib,json,shutil
R=Path('.local/p011_20261020/r1');P=Path('reports/p011_20261020/long_preflight_source_v1')
assert sorted(p.name for p in P.iterdir())==['OWNER_BINDING.json']
def h(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def write(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x') as f:f.write(x if isinstance(x,str) else json.dumps(x,ensure_ascii=False,indent=2,sort_keys=True)+'\n')
now=datetime.now(timezone.utc).isoformat();owner=read(R/'OWNER_BUDGET_GPU_PREFLIGHT_REPORTED_DECISION.json')
raw=(R/'build_long_preflight_source_once.py').read_text()
tail=raw[raw.index('roots='):]
tail=tail.replace("   assert n.level==0,'Relative import needs explicit resolution'\n   if n.module:modules=[n.module]+[n.module+'.'+v.name for v in n.names if v.name!='*']", "   base=n.module or ''\n   if n.level:\n    parts=list(p.parent.parts);assert n.level<=len(parts)\n    prefix='.'.join(parts[:len(parts)-n.level+1]);base=prefix+('.'+base if base else '')\n   if base:modules=[base]+[base+'.'+v.name for v in n.names if v.name!='*']")
tail=tail.replace("shutil.copyfile(__file__,P/'BUILD_SCRIPT.py')", "shutil.copyfile(R/'build_long_preflight_source_once.py',P/'BUILD_SCRIPT.py')\nshutil.copyfile(__file__,P/'METADATA_TAIL_SCRIPT.py')\nwrite(P/'PREPARATION_NOTE.md','Initial metadata source-closure walk rejected a relative local import after only OWNER_BINDING was written. That original file and failing script are retained. Only missing metadata was completed with explicit relative-import resolution. No production path, input selection, model, test or paid task repeated.\\n')")
exec(compile(tail,str(R/'build_long_preflight_source_once.py')+'[missing-tail]','exec'))
