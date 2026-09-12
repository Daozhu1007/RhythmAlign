"""Exhaustive existing-source wrong-project search, with exact feature reuse."""
from __future__ import annotations
import collections
import itertools
import numpy as np
from scipy import signal
from study import (eng, auto_sync, librosa, AudioSources, SR, HOP, BASE, OUT,
                   SCRATCH, read, save, metadata, digest, curve_summary)


def features(y):
    c=librosa.feature.chroma_cens(y=y,sr=SR,hop_length=HOP)
    c=np.diff(c,axis=1,prepend=c[:,:1])
    return {'chroma':c,'onset':librosa.onset.onset_strength(y=y,sr=SR,hop_length=HOP),
            'pcen_hpss':eng._pcen_hpss_features(y,SR,HOP),'pcen':eng._pcen_features(y,SR,HOP)}


def families(v,m):
    chroma=eng._correlate_rows(v['chroma'],m['chroma'])
    oc=signal.correlate(m['onset']-m['onset'].mean(),v['onset']-v['onset'].mean(),mode='full',method='fft')
    curves={'hybrid':auto_sync._normalize_correlation(chroma)+.2*auto_sync._normalize_correlation(oc),
            'onset':signal.correlate(m['onset'],v['onset'],mode='full',method='fft'),
            'pcen_hpss':eng._correlate_rows(v['pcen_hpss'],m['pcen_hpss']),
            'pcen':eng._correlate_rows(v['pcen'],m['pcen'])}
    return [eng.FamilyResult(k,eng.METHOD_FAMILY[k],c,v['chroma'].shape[1],float(auto_sync._correlation_z_score(c)),0.) for k,c in curves.items()]


def main():
    sources=AudioSources();plan=read(BASE/'semi_synthetic_plan.json')
    corpus=read(OUT/'corpus.json')
    fmap={};durations={}
    for kind in ['tracks','recordings']:
        for sid in sources.mapping[kind]:
            y=sources.get(kind,sid);durations[sid]=len(y)/SR
            path=SCRATCH/('features_'+sid+'.npz')
            # Always generate for this run; no stale feature cache can enter.
            np.savez_compressed(path,**features(y));fmap[sid]=path
            print('features',sid,flush=True)
    equivalence=[]
    existing=[r for r in corpus['rows'] if r['case']['kind'] in ['manual','hard_negative']]
    for r in existing:
        with np.load(fmap[r['case']['background']]) as v,np.load(fmap[r['case']['target']]) as m:
            fs=families(v,m)
        with np.load(SCRATCH/(r['case']['case_id']+'_curves.npz')) as prior:
            diff={f.method:float(np.max(np.abs(f.curve-prior[f.method]))) for f in fs}
        assert max(diff.values())<1e-7,(r['case']['case_id'],diff)
        equivalence.append({'case_id':r['case']['case_id'],'max_abs_curve_differences':diff})
    projects=plan['split']['projects']
    own={rid:spec['track'] for spec in projects.values() for rid in spec['recordings']}
    rows=[]
    targets={sid:dict(np.load(path)) for sid,path in fmap.items() if sid.startswith('tr_')}
    for rid in sources.mapping['recordings']:
        with np.load(fmap[rid]) as v:
            for tid,m in targets.items():
                if own[rid]==tid:continue
                fs=families(v,m)
                d=eng.decide_from_families(fs,SR,HOP,None,durations[rid],durations[tid])
                row={'recording':rid,'track':tid,'status':d.status,'offset':d.offset,'reason':d.reason_code,
                     'methods':{f.method:curve_summary(f) for f in fs}}
                if d.accepted:row['clusters']=d.clusters
                rows.append(row)
                if d.accepted:print('ACCEPTED wrong-project pair',rid,tid,d.offset,flush=True)
        save('mismatch_search.json',{'metadata':metadata('python experiments/alignment_research/mismatch_search.py'),
                                     'script_sha256':digest(__file__),'sources':sources.manifest,
                                     'equivalence_checks':equivalence,'rows':rows,'expected_n':551,'complete':len(rows)==551,
                                     'reason_counts':dict(collections.Counter(r['reason'] for r in rows)),
                                     'notes':'All wrong-project pairs; no assumptions of case independence. Content identity is project provenance, not a guarantee that another song never appears in a background.'})
        print('pairs completed',len(rows),flush=True)


if __name__=='__main__':main()
