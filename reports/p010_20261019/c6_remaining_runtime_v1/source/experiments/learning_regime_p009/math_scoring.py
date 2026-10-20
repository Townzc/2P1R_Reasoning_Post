"""Candidate MATH scorer for P1 review, not admitted for student selection.

The final explicit box is extracted before symbolic parsing. A valid symbolic
False is final; string fallback is only for parser/tool failure. Each symbolic
operation is signal-bounded in a dedicated process with an outer wall timer.
No generated output, test subset or protocol is changed by this module.
"""
import importlib.metadata
import multiprocessing
import re
import unicodedata

VERSION = 'p009_last_box_math_verify_090_candidate_v1'
VERSIONS = {'math-verify':'0.9.0','latex2sympy2_extended':'1.11.0',
            'antlr4-python3-runtime':'4.13.2','sympy':'1.14.0','mpmath':'1.3.0'}
BOX = re.compile(r'\\(?:boxed|fbox)\s*\{')


def escaped(text, index):
    backslashes=0;index-=1
    while index>=0 and text[index]=='\\':
        backslashes+=1;index-=1
    return backslashes%2==1


def last_box(text):
    """Never backfill an earlier correct box after a malformed final box."""
    matches=list(BOX.finditer(text))
    if not matches:return dict(status='no_box',answer=None)
    match=matches[-1];depth=1;index=match.end()
    while index<len(text):
        char=text[index]
        if not escaped(text,index):
            depth+=(char=='{')-(char=='}')
        if depth==0:
            answer=text[match.end():index].strip()
            return dict(status='box' if answer else 'empty_box',answer=answer or None,
                        start=match.start(),end=index+1,box_count=len(matches))
        index+=1
    return dict(status='unclosed_last_box',answer=None,box_count=len(matches))


def normalized_string(text):
    value=unicodedata.normalize('NFC',text).strip()
    if len(value)>=2 and value.startswith('$') and value.endswith('$'):
        value=value[1:-1].strip()
    value=value.replace(r'\left','').replace(r'\right','').replace(r'\dfrac',r'\frac')
    return re.sub(r'\s+','',value)


def symbolic(gold, answer):
    from math_verify import parse,verify,LatexExtractionConfig
    from math_verify.utils import TimeoutException
    try:
        config=[LatexExtractionConfig(try_extract_without_anchor=False,boxed_match_priority=0)]
        kwargs=dict(extraction_config=config,fallback_mode='no_fallback',
                    extraction_mode='first_match',parsing_timeout=2,raise_on_error=True)
        left=parse('$\\boxed{'+gold+'}$',**kwargs)
        right=parse('$\\boxed{'+answer+'}$',**kwargs)
        if not left or not right:
            return dict(status='parse_failure',equivalent=None)
        # no_fallback must never silently contribute a string equivalence.
        if any(isinstance(x,str) for x in left+right):
            return dict(status='parse_failure',equivalent=None)
        value=verify(left,right,float_rounding=6,numeric_precision=15,
                     strict=True,allow_set_relation_comp=False,timeout_seconds=2,raise_on_error=True)
        return dict(status='compared',equivalent=bool(value))
    except TimeoutException:
        return dict(status='symbolic_timeout',equivalent=None)
    except Exception as exc:
        return dict(status='tool_error',equivalent=None,error_type=type(exc).__name__)


def child(connection,gold,answer):
    try:
        actual={name:importlib.metadata.version(name) for name in VERSIONS}
        if actual!=VERSIONS:
            connection.send(dict(status='dependency_mismatch',versions=actual));return
        connection.send(symbolic(gold,answer))
    finally:
        connection.close()


def decide(gold, extracted, symbolic_result, *, stop_reason):
    if stop_reason not in ('native_eos','new_problem_boundary','length_cap','invalid_special_token'):
        raise ValueError('Unknown/incomplete stream requires technical reconciliation')
    if not isinstance(gold,str) or not gold.strip():
        raise ValueError('Missing gold answer is not a scored zero')
    if stop_reason in ('length_cap','invalid_special_token'):
        return dict(version=VERSION,status=stop_reason,correct=False,parsed=False,
                    fallback_used=False,teacher_label_eligible=False,reasoning_validated=False)
    answer=extracted.get('answer')
    if not answer:
        return dict(version=VERSION,status=extracted['status'],correct=False,parsed=False,
                    fallback_used=False,teacher_label_eligible=False,reasoning_validated=False)
    status=symbolic_result['status']
    if status=='dependency_mismatch':
        raise ValueError('Scorer environment differs; not an answer error')
    string_equal=bool(normalized_string(gold)) and normalized_string(gold)==normalized_string(answer)
    if status=='compared':
        if type(symbolic_result['equivalent']) is not bool:
            raise ValueError('Invalid symbolic verdict')
        correct=symbolic_result['equivalent'];fallback=False
    elif status in ('parse_failure','symbolic_timeout','tool_error','outer_timeout'):
        correct=string_equal;fallback=True
    else:
        raise ValueError('Missing/unexpected symbolic result')
    label_eligible=status=='compared' or (fallback and correct)
    return dict(version=VERSION,status=status,correct=correct,parsed=label_eligible,
                box_extracted=True,teacher_label_eligible=label_eligible,
                extracted_answer=answer,normalized_string_equal=string_equal,
                symbolic=symbolic_result,fallback_used=fallback,
                string_symbolic_disagreement=(status=='compared' and correct!=string_equal),
                reasoning_validated=False)


def score(gold, answer_segment, *, stop_reason):
    extracted=last_box(answer_segment)
    if stop_reason in ('length_cap','invalid_special_token') or not extracted['answer']:
        return decide(gold,extracted,{},stop_reason=stop_reason)
    ctx=multiprocessing.get_context('spawn');parent,remote=ctx.Pipe(duplex=False)
    process=ctx.Process(target=child,args=(remote,gold,extracted['answer']),daemon=False)
    process.start();remote.close()
    try:
        if parent.poll(8):
            try:result=parent.recv()
            except EOFError:result=dict(status='tool_error',equivalent=None,error_type='worker_eof')
        else:result=dict(status='outer_timeout',equivalent=None)
    finally:
        process.join(timeout=.1)
        if process.is_alive():process.kill();process.join(timeout=2)
        parent.close()
    return decide(gold,extracted,result,stop_reason=stop_reason)
