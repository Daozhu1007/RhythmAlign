"""Follow-up to the single accepted exhaustive mismatch; no threshold tuning."""
from __future__ import annotations
import dataclasses
import hashlib
import numpy as np
from study import (eng, auto_sync, AudioSources, SR, HOP, OUT, SCRATCH, SEED,
                   read, save, metadata, digest, waveform_baselines, curve_summary)
from probes import single_run


def main():
    sources=AudioSources()
    v=sources.get('recordings','haiditan_ds_1')
    m=sources.get('tracks','tr_hongzhoutian')
    own=sources.get('tracks','tr_haiditan')
    out={'metadata':metadata('python experiments/alignment_research/investigate_counterexample.py'),
         'script_sha256':digest(__file__),'sources':sources.manifest,
         'followup_design':'After discovery: direct file entry point twice, independent generators, own-track control, clean own-track wrong-reference control; attribution is descriptive, not threshold selection.'}
    out['file_entry_repeats']=[]
    for rep in range(2):
        d=eng.find_offset_v2(sources.mapping['recordings']['haiditan_ds_1'],sources.mapping['tracks']['tr_hongzhoutian'])
        out['file_entry_repeats'].append(dataclasses.asdict(d))
        print('file repeat',rep,d.status,d.offset,flush=True)
        save('counterexample_validation.json',out)
    fs=eng._run_generators(v,m,SR,HOP)
    out['independent_generator_methods']={f.method:curve_summary(f) for f in fs}
    out['waveform_baselines_wrong_reference']=waveform_baselines(v,m)
    out['own_reference_control']=single_run(v,own,{'case_id':'haiditan_ds_1_own_reference','kind':'unlabeled_real_positive','contract':'Pairing evidence only; no newly invented manual ground truth.'})
    print('own reference',out['own_reference_control']['offset'],flush=True)
    out['clean_own_track_wrong_reference']=single_run(own,m,{'case_id':'clean_haiditan_x_hongzhoutian','kind':'wrong_project_reference','contract':'Exactly known reference-only source; cross-song overlap remains a content question.'})
    print('clean wrong reference',out['clean_own_track_wrong_reference']['status'],out['clean_own_track_wrong_reference']['offset'],flush=True)
    # Decompose the full-curve HPSS correlation at its accepted peak into
    # signed per-reference-time products. No per-window restandardization.
    vf=eng._pcen_hpss_features(v,SR,HOP);mf=eng._pcen_hpss_features(m,SR,HOP)
    off=out['file_entry_repeats'][0]['offset'];shift=round(off*SR/HOP)
    ms=max(0,-shift);me=min(mf.shape[1],vf.shape[1]-shift)
    products=(mf[:,ms:me]*vf[:,ms+shift:me+shift]).sum(axis=0)
    bins=[]
    for start in range(0,len(products),round(5*SR/HOP)):
        end=min(len(products),start+round(5*SR/HOP))
        bins.append({'reference_start_s':(ms+start)*HOP/SR,'reference_end_s':(ms+end)*HOP/SR,
                     'video_start_s':(ms+shift+start)*HOP/SR,'signed_product_sum':float(products[start:end].sum()),
                     'positive_product_sum':float(np.maximum(products[start:end],0).sum())})
    out['hpss_contribution_bins_5s']=bins
    out['hpss_total_product_sum']=float(products.sum())
    out['decoded_array_hashes']={'recording':hashlib.sha256(v.tobytes()).hexdigest(),'wrong_reference':hashlib.sha256(m.tobytes()).hexdigest()}
    save('counterexample_validation.json',out)
    print('top contribution bins',sorted(bins,key=lambda b:b['signed_product_sum'],reverse=True)[:5],flush=True)


def clean_controls():
    # Fixed after the clean grid: validate its first accepted directed pair.
    out=read(OUT/'counterexample_validation.json');sources=AudioSources()
    a='tr_lingduihua';b='tr_yanwulieche'
    v=sources.get('tracks',a);m=sources.get('tracks',b)
    results={'query_track':a,'reference_track':b,'file_entry_repeats':[],
             'metadata':metadata('python experiments/alignment_research/investigate_counterexample.py clean'),
             'script_sha256':digest(__file__),'sources':sources.manifest}
    for rep in range(2):
        d=eng.find_offset_v2(sources.mapping['tracks'][a],sources.mapping['tracks'][b])
        results['file_entry_repeats'].append(dataclasses.asdict(d))
        print('clean file repeat',rep,d.status,d.offset,flush=True)
    results['waveform_baselines']=waveform_baselines(v,m)
    fs=eng._run_generators(v,m,SR,HOP)
    from mismatch_search import features, families
    vf=features(v);mf=features(m)
    original=families(vf,mf)
    results['feature_reuse_max_abs_difference']={f.method:float(np.max(np.abs(f.curve-original[j].curve))) for j,f in enumerate(fs)}
    d=results['file_entry_repeats'][0];shift=round(d['offset']*SR/HOP)
    contributions={}
    for method in ['pcen_hpss','pcen']:
        x=vf[method];y=mf[method]
        ms=max(0,-shift);me=min(y.shape[1],x.shape[1]-shift)
        prod=(y[:,ms:me]*x[:,ms+shift:me+shift]).sum(axis=0)
        bins=[]
        for start in range(0,len(prod),round(SR/HOP)):
            end=min(len(prod),start+round(SR/HOP))
            bins.append({'reference_start_s':(ms+start)*HOP/SR,'video_start_s':(ms+shift+start)*HOP/SR,
                         'signed_sum':float(prod[start:end].sum()),'positive_sum':float(np.maximum(prod[start:end],0).sum())})
        contributions[method]={'total_signed':float(prod.sum()),'bins_1s':bins}
    results['contributions']=contributions
    # Preserve original coordinates and normalization. Mask first/last 5 s
    # feature support only; this is causal localization, not a production fix.
    edge=round(5*SR/HOP)
    modified_v={k:arr.copy() for k,arr in vf.items()};modified_m={k:arr.copy() for k,arr in mf.items()}
    for feats in [modified_v,modified_m]:
        for k,arr in feats.items():
            arr[..., :edge]=0;arr[..., -edge:]=0
    edgefs=families(modified_v,modified_m)
    results['mask_first_last_5s_features']=dataclasses.asdict(eng.decide_from_families(edgefs,SR,HOP,None,len(v)/SR,len(m)/SR))
    # A clean crop is a separate waveform-level mismatch control, with fresh
    # features. It does not inherit any cached boundary normalizations.
    results['crop_first_last_5s_audio']=single_run(v[5*SR:-5*SR],m[5*SR:-5*SR],
        {'case_id':'clean_mismatch_interior','kind':'wrong_project_reference','crop_s_each_end':5})
    # Direct signal comparison at the reported lag; no listening verdict.
    shift_samples=round(d['offset']*SR);ms=max(0,-shift_samples);me=min(len(m),len(v)-shift_samples)
    corr=[]
    for s in range(ms,me-SR+1,SR):
        x=v[s+shift_samples:s+shift_samples+SR];y=m[s:s+SR]
        corr.append({'reference_start_s':s/SR,'pearson':float(np.corrcoef(x,y)[0,1]) if x.std()>0 and y.std()>0 else None})
    results['waveform_1s_pearson_at_engine_offset']=corr
    out['clean_pair_validation']=results
    save('counterexample_validation.json',out)
    for method,vals in contributions.items():
        print('clean contribution',method,vals['total_signed'],sorted(vals['bins_1s'],key=lambda x:x['signed_sum'],reverse=True)[:4],flush=True)
    print('mask',results['mask_first_last_5s_features']['status'],'crop',results['crop_first_last_5s_audio']['status'],flush=True)


def ablate_clean_pair():
    from mismatch_search import families
    out=read(OUT/'counterexample_validation.json');cv=out['clean_pair_validation']
    a=cv['query_track'];b=cv['reference_track']
    fs=families(dict(np.load(SCRATCH/('features_'+a+'.npz'))),dict(np.load(SCRATCH/('features_'+b+'.npz'))))
    vd=cv['sources']['tracks:'+a]['samples']/SR;md=cv['sources']['tracks:'+b]['samples']/SR
    cv['single_method_removal']={name:dataclasses.asdict(eng.decide_from_families([f for f in fs if f.method!=name],SR,HOP,None,vd,md)) for name in ['pcen','pcen_hpss','onset','hybrid']}
    cv['single_method_removal_command']='python experiments/alignment_research/investigate_counterexample.py ablate'
    cv['final_script_sha256']=digest(__file__)
    save('counterexample_validation.json',out)


if __name__=='__main__':
    import sys
    command=sys.argv[1] if len(sys.argv)>1 else 'original'
    {'original':main,'clean':clean_controls,'ablate':ablate_clean_pair}[command]()
