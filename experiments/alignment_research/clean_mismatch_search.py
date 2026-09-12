"""Post-discovery fixed 20 x 19 clean-reference mismatch control."""
import collections
import numpy as np
from study import eng, AudioSources, SR, HOP, SCRATCH, save, metadata, digest, curve_summary
from mismatch_search import families


def main():
    sources=AudioSources();features={};duration={};rows=[]
    for tid in sources.mapping['tracks']:
        y=sources.get('tracks',tid);duration[tid]=len(y)/SR
        # This cache was freshly built in the completed exhaustive search;
        # its exact equivalence was checked there on 21 preserved pairs.
        features[tid]=dict(np.load(SCRATCH/('features_'+tid+'.npz')))
    for vid,v in features.items():
        for mid,m in features.items():
            if vid==mid:continue
            fs=families(v,m)
            d=eng.decide_from_families(fs,SR,HOP,None,duration[vid],duration[mid])
            r={'query_track':vid,'reference_track':mid,'status':d.status,'offset':d.offset,'reason':d.reason_code,
               'methods':{f.method:curve_summary(f) for f in fs}}
            if d.accepted:
                r['clusters']=d.clusters
                print('ACCEPT',vid,mid,d.offset,flush=True)
            rows.append(r)
        save('clean_mismatch_search.json',{'metadata':metadata('python experiments/alignment_research/clean_mismatch_search.py'),
             'script_sha256':digest(__file__),'sources':sources.manifest,'rows':rows,
             'complete':len(rows)==380,'expected_n':380,
             'notes':'Post-discovery fixed exhaustive control. Queries contain only the named clean reference, no room recording. Directed pairs are dependent; a shared musical passage is still possible and must be distinguished from wrong song identity.'})
        print('completed',len(rows),flush=True)


if __name__=='__main__':main()
