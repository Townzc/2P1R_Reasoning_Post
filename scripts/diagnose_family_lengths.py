"""CPU constraint ablation: common length versus one length per family."""
from collections import defaultdict
import networkx as nx
from scripts.audit_legal_support import FAMILIES, allocate_distinct_classes


def structure_witness(rows):
    """Length selection is a caller constraint; enforce four structures/family."""
    graph = nx.DiGraph()
    representatives = {}
    for family in FAMILIES:
        graph.add_edge(('source',),('family',family),capacity=4)
    for row in sorted(rows,key=lambda r:(r['expression'],r['family'])):
        family, structure, ac = row['family'], row['structure_id'], row['ac_class']
        graph.add_edge(('family',family),('structure',family,structure),capacity=1)
        graph.add_edge(('structure',family,structure),('class',ac),capacity=1)
        graph.add_edge(('class',ac),('sink',),capacity=1)
        representatives.setdefault((family,structure,ac),row)
    if ('sink',) not in graph:
        return None
    count,flow=nx.maximum_flow(graph,('source',),('sink',),flow_func=nx.algorithms.flow.edmonds_karp)
    if count!=8:
        return None
    selected=[]
    for (family,structure,ac),row in sorted(representatives.items()):
        if flow.get(('structure',family,structure),{}).get(('class',ac),0):
            selected.append(row)
    assert len(selected)==8 and len({r['ac_class'] for r in selected})==8
    return selected


def diagnose(records, problems):
    grouped=defaultdict(lambda:defaultdict(lambda:defaultdict(list)))
    for row in records:
        if row.get('encodable',True):
            grouped[row['problem_id']][row['family']][row['n_supervised']].append(row)
    results=[]
    for pid in sorted(problems):
        by_family=grouped[pid]
        eligible={f: sorted(length for length,rows in by_family[f].items() if len({r['ac_class'] for r in rows})>=4) for f in FAMILIES}
        common=set(eligible[FAMILIES[0]])&set(eligible[FAMILIES[1]])
        pairs={name:[] for name in ('common_class','common_structure','per_family_class','per_family_structure')}
        examples={}
        for li in eligible[FAMILIES[0]]:
            for ln in eligible[FAMILIES[1]]:
                left,right=by_family[FAMILIES[0]][li],by_family[FAMILIES[1]][ln]
                disjoint=allocate_distinct_classes({r['ac_class'] for r in left},{r['ac_class'] for r in right},4)
                if disjoint is None:
                    continue
                pairs['per_family_class'].append([li,ln])
                if li==ln:pairs['common_class'].append([li,ln])
                selected=structure_witness(left+right)
                if selected is None:
                    continue
                pairs['per_family_structure'].append([li,ln])
                if li==ln:pairs['common_structure'].append([li,ln])
                examples.setdefault('per_family_structure',selected)
                if li==ln:examples.setdefault('common_structure',selected)
        row={k:problems[pid][k] for k in ('problem_id','numbers','target')}
        row.update(individual_family_class_lengths=eligible,individual_family_lengths_intersect=bool(common),
                   feasible_length_pairs=pairs,flags={k:bool(v) for k,v in pairs.items()},
                   structure_witnesses=examples)
        results.append(row)
    stages={k:sorted(r['problem_id'] for r in results if r['flags'][k]) for k in ('common_class','common_structure','per_family_class','per_family_structure')}
    return {'per_problem':results,'stage_ids':stages,'counts':{k:len(v) for k,v in stages.items()},
            'interpretation':'Constraint feasibility only; different family lengths do not imply cross-family equal dose.'}
