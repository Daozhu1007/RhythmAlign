"""Read-only baseline/RA-1.2D comparison and scientific harness controls."""
import ast
import hashlib
import subprocess
import sys
import numpy as np
from study import ROOT, SHA, SR, SEED, OUT, read, save, metadata, digest, waveform_baselines

D_SHA='20d48169803a0e62e4379f197a51b92f9ac6555b'


def git_text(ref,path):
    return subprocess.check_output(['git','show',ref+':'+path],cwd=ROOT).decode('utf-8')


class ScientificAST(ast.NodeTransformer):
    def __init__(self,ignore):self.ignore=ignore
    def generic_visit(self,node):
        super().generic_visit(node)
        if isinstance(node,(ast.Module,ast.ClassDef,ast.FunctionDef,ast.AsyncFunctionDef)):
            if node.body and isinstance(node.body[0],ast.Expr) and isinstance(node.body[0].value,ast.Constant) and isinstance(node.body[0].value.value,str):node.body=node.body[1:]
        if isinstance(node,ast.Module):
            node.body=[s for s in node.body if not (isinstance(s,ast.Assign) and any(isinstance(t,ast.Name) and t.id in self.ignore for t in s.targets))]
        return node


def main():
    result={'metadata':metadata('python experiments/alignment_research/verify.py'),'script_sha256':digest(__file__)}
    check={'scientific_baseline':SHA,'integration_commit':D_SHA,'comparisons':{}}
    for path,ignore in [('alignment_engine_v2.py',{'ENGINE_LABEL'}),('auto_sync.py',{'_ANALYSIS_ESTIMATE_REALTIME_FACTOR'})]:
        a=ast.dump(ScientificAST(ignore).visit(ast.parse(git_text(SHA,path))),include_attributes=False)
        b=ast.dump(ScientificAST(ignore).visit(ast.parse(git_text(D_SHA,path))),include_attributes=False)
        check['comparisons'][path]={'equal_executable_AST_after_explicit_exclusions':a==b,
            'excluded_top_level_assignments':sorted(ignore),'docstrings_excluded':True,
            'baseline_normalized_ast_sha256':hashlib.sha256(a.encode()).hexdigest(),
            'integration_normalized_ast_sha256':hashlib.sha256(b.encode()).hexdigest()}
        assert a==b,path
    check['requirements_txt_unchanged']=git_text(SHA,'requirements.txt')==git_text(D_SHA,'requirements.txt')
    ui=git_text(D_SHA,'ui_main.py');tree=ast.parse(ui)
    inspected=[]
    for cl in tree.body:
        if isinstance(cl,ast.ClassDef) and cl.name in ['BaseMediaWorker','SyncWorker','AnalyzeWorker']:
            for fn in cl.body:
                if isinstance(fn,ast.FunctionDef) and fn.name in ['_run_find_offset','run','_on_offset_found','_on_abstained']:
                    inspected.append({'class':cl.name,'function':fn.name,'start_line':fn.lineno,
                                      'source':ast.get_source_segment(ui,fn)})
    check['integration_call_path_inspected']=inspected
    check['inference']='Both GUI workers use find_offset_v2 without policy overrides. ACCEPT dispatches its offset; SyncWorker exports. ABSTAIN stops. The algorithmic counterexamples remain relevant; no RA-1.2D experimental result was used for tuning.'
    check['owner_listening_context']='RA-1.2D documentation records owner PASS for the one motivating export. This post-baseline documentation is context only, not new quantitative ground truth or a scientific input.'
    result['ra12d_relevance']=check
    controls=[]
    rng=np.random.default_rng(SEED+500);m=rng.normal(0,.1,45*SR).astype(np.float32)
    for offset in [-2.5,2.5]:
        v=np.zeros(60*SR,dtype=np.float32);shift=round(offset*SR)
        start=max(0,shift);ms=max(0,-shift);n=min(len(v)-start,len(m)-ms)
        v[start:start+n]=m[ms:ms+n]
        pred=waveform_baselines(v,m)
        assert all(abs(p['offset']-offset)<=1/7350 for p in pred.values()),pred
        controls.append({'known_offset_s':offset,'methods':pred})
    result['waveform_baseline_sign_and_exact_shift_controls']=controls
    original={}
    for path in ['experiments/alignment_research/results/corpus.json','experiments/alignment_research/results/audit.json']:
        expected=subprocess.check_output(['git','show','5b1fcd472a94470872dc1f837a7f473c0edd5282:'+path],cwd=ROOT)
        actual=(ROOT/path).read_bytes()
        same=expected.replace(b'\r\n',b'\n')==actual.replace(b'\r\n',b'\n')
        original[path]={'git_content_unchanged_from_wip':same,'raw_checkout_bytes_equal_git_blob':expected==actual,
                        'checkout_sha256':digest(ROOT/path),'git_blob_sha256':hashlib.sha256(expected).hexdigest(),
                        'note':'Git checkout may convert LF to CRLF; this check permits only that conversion.'}
        assert same,path
    result['preserved_results']=original
    tests=subprocess.run([sys.executable,'-m','pytest','-q'],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    result['baseline_test_suite']={'command':'python -m pytest -q','returncode':tests.returncode,
        'summary':tests.stdout.strip().splitlines()[-1],
        'stdout_sha256':hashlib.sha256(tests.stdout.encode()).hexdigest()}
    result['research_result_counts']={name:len(read(OUT/(name+'.json'))['rows']) for name in ['corpus','feature_nulls','audio_nulls','safeguards','curve_counterexamples','mismatch_search','clean_mismatch_search']}
    save('verification.json',result)
    print(result['baseline_test_suite']);print('AST equal; preserved Git content unchanged; shift controls passed')
    if tests.returncode:raise RuntimeError('Baseline suite failed; inspect console separately')


if __name__=='__main__':main()
