"""Predeclared falsification probes; all output is exploratory, no policy tuning."""
from __future__ import annotations
import argparse
import hashlib
import itertools
import time
import numpy as np
from scipy import signal
from study import (eng, auto_sync, ss, SR, HOP, SEED, OUT, SCRATCH, ROOT,
                   AudioSources, curve_summary, metadata, save, digest)
from experiments.low_snr_alignment.synthetic_eval import make_music, make_taps


def feature_nulls():
    rows=[]
    for duration,dimensions,ar in itertools.product([30,60,180,600],[1,12,96],[0.,.9]):
        n=round(duration*SR/HOP)
        for rep in range(16):
            seed=SEED+rep
            rng=np.random.default_rng(seed)
            a=rng.standard_normal((dimensions,n));b=rng.standard_normal((dimensions,n))
            if ar:
                a=signal.lfilter([1],[1,-ar],a,axis=1)
                b=signal.lfilter([1],[1,-ar],b,axis=1)
            a=(a-a.mean(axis=1,keepdims=True))/a.std(axis=1,keepdims=True)
            b=(b-b.mean(axis=1,keepdims=True))/b.std(axis=1,keepdims=True)
            c=eng._correlate_rows(a,b)
            peaks=eng._independent_peak_indices(c,int(1.5*SR/HOP))
            rows.append({'duration_s':duration,'dimensions':dimensions,'ar':ar,'seed':seed,
                         'lags':len(c),'max_z':float(auto_sync._correlation_z_score(c)),
                         'margin':float(c[peaks[0]]/c[peaks[1]]),
                         'central_half_overlap_max_z':float(auto_sync._correlation_z_score(c[n//2:-n//2]))})
        print(f'feature null duration={duration} dimensions={dimensions} ar={ar}',flush=True)
    save('feature_nulls.json',{'metadata':metadata('python experiments/alignment_research/probes.py feature-nulls'),
                              'script_sha256':digest(__file__),'n_per_cell':16,'rows':rows,
                              'notes':'Independent standard Gaussian features, optional AR(1), per-row standardization; full FFT correlation. Same seed across cells couples realizations; no iid population audio inference.'})


def audio_nulls():
    rows=[]
    for duration in [30,90,240]:
        m=make_music(duration_s=duration,seed=71)
        for kind in ['gaussian','gaussian_taps']:
            for rep in range(6):
                seed=SEED+100+rep
                v=(.02*np.random.default_rng(seed).standard_normal(len(m))).astype(np.float32)
                if kind=='gaussian_taps':v+=make_taps(duration,gain=.3,seed=seed)
                fs=eng._run_generators(v,m,SR,HOP)
                d=eng.decide_from_families(fs,SR,HOP,None,duration,duration)
                rows.append({'duration_s':duration,'noise_kind':kind,'seed':seed,
                             'methods':{f.method:curve_summary(f) for f in fs},
                             'status':d.status,'reason':d.reason_code,'offset':d.offset})
                save('audio_nulls.json',{'metadata':metadata('python experiments/alignment_research/probes.py audio-nulls'),
                                        'script_sha256':digest(__file__),'rows':rows,'complete':len(rows)==36,
                                        'notes':'No target mixed into recording. Reference is the historical deterministic musical generator, not a new independent song per trial. No input peak normalization.'})
                print(f'audio null {len(rows)}/36 {duration} {kind} -> {d.status}',flush=True)


def single_run(v,m,spec):
    fs=eng._run_generators(v,m,SR,HOP)
    d=eng.decide_from_families(fs,SR,HOP,None,len(v)/SR,len(m)/SR)
    return {'case':spec,'status':d.status,'offset':d.offset,'reason':d.reason_code,
            'video_s':len(v)/SR,'music_s':len(m)/SR,
            'methods':{f.method:curve_summary(f) for f in fs},'clusters':d.clusters,
            'video_array_sha256':hashlib.sha256(v.tobytes()).hexdigest(),
            'reference_array_sha256':hashlib.sha256(m.tobytes()).hexdigest()}


def safeguard():
    sources=AudioSources();rows=[]
    track=sources.get('tracks','tr_drops')[:60*SR]
    # A partial excerpt can have a mathematically correct local lag, while
    # geometric overlap greatly exceeds the actual duration of shared content.
    for support in [1,3,8,20,40]:
        rng=np.random.default_rng(SEED+200)
        v=(.002*rng.standard_normal(90*SR)).astype(np.float32)
        start=10*SR;end=start+support*SR
        v[20*SR:20*SR+support*SR]+=track[start:end]
        rows.append(single_run(v,track,{'case_id':f'partial_{support}s','kind':'partial_support',
                         'seed':SEED+200,'shared_support_s':support,'local_valid_offset_s':10.,
                         'contract':'Correct local match allowed; does not establish 30 seconds of shared support.'}))
        print('partial',support,rows[-1]['status'],rows[-1]['offset'],flush=True)
    # Full reference repeated at two disjoint placements, with deliberately
    # unequal strength; both placements really occur and both are valid lags.
    motif=track[:35*SR]
    for ratio in [1.,.85,.5]:
        v=(.001*np.random.default_rng(SEED+201).standard_normal(100*SR)).astype(np.float32)
        v[5*SR:40*SR]+=motif
        v[55*SR:90*SR]+=ratio*motif
        rows.append(single_run(v,motif,{'case_id':f'two_occurrences_{ratio}','kind':'multiple_valid_offsets',
                         'seed':SEED+201,'valid_offsets_s':[5.,55.],'second_gain_ratio':ratio,
                         'contract':'Both offsets content-correct; acceptance is a uniqueness-policy violation only if the task requires unique occurrence.'}))
        print('repeat',ratio,rows[-1]['status'],rows[-1]['offset'],flush=True)
    # Strong direct path + close replica exposes alternatives hidden by the
    # fixed 1.5-second peak-separation heuristic, not song-level uniqueness.
    for delta in [.35,.7,1.2,2.]:
        v=(.001*np.random.default_rng(SEED+202).standard_normal(90*SR)).astype(np.float32)
        v[5*SR:40*SR]+=motif
        second=round((5+delta)*SR)
        v[second:second+len(motif)]+=motif
        rows.append(single_run(v,motif,{'case_id':f'close_replica_{delta}','kind':'multiple_valid_offsets',
                         'seed':SEED+202,'valid_offsets_s':[5.,5+delta],
                         'contract':'Equal-strength superposed copies; no unique direct-path label.'}))
        print('replica',delta,rows[-1]['status'],rows[-1]['offset'],flush=True)
    save('safeguards.json',{'metadata':metadata('python experiments/alignment_research/probes.py safeguards'),
                          'script_sha256':digest(__file__),'sources':sources.manifest,'rows':rows,
                          'notes':'Original media read-only; new arrays explicitly cropped and mixed. These are support/uniqueness probes, not falsely labeled wrong-song nulls.'})


def curve_counterexamples():
    # No claim that arbitrary curves are attainable from natural audio.
    # Demonstrates a decision-layer contract gap using the public test seam.
    nv=4000;n=7000;x=np.arange(n)
    rows=[]
    for hpss_offset in [7.30,7.44,7.58]:
        fs=[]
        for j,(method,offset,height) in enumerate([
                ('hybrid',7.30,20.),('pcen',7.44,24.),
                ('onset',7.56,10.),('pcen_hpss',hpss_offset,5.)]):
            idx=eng._offset_to_index(offset,nv,HOP,SR)
            c=np.random.default_rng(SEED+300+j).normal(0,.1,n)+height*np.exp(-.5*((x-idx)/1.5)**2)
            fs.append(eng.FamilyResult(method,eng.METHOD_FAMILY[method],c,nv,float(auto_sync._correlation_z_score(c)),0))
        d=eng.decide_from_families(fs,SR,HOP,None,92.,80.)
        rows.append({'hpss_offset_s':hpss_offset,'reference_nomination_s':7.30,'status':d.status,
                     'offset':d.offset,'distance_from_tonal_nomination_s':None if d.offset is None else abs(d.offset-7.30),
                     'reason':d.reason_code,'clusters':d.clusters})
    save('curve_counterexamples.json',{'metadata':metadata('python experiments/alignment_research/probes.py curve-counterexamples'),
                                      'script_sha256':digest(__file__),'rows':rows,
                                      'limitation':'Synthetic feature curves only; not waveform-level correctness evidence. Nomination label is a test-seam anchor, not independent audio ground truth.'})
    print([(r['status'],r['offset'],r['distance_from_tonal_nomination_s']) for r in rows])


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('command',choices=['feature-nulls','audio-nulls','safeguards','curve-counterexamples'])
    arg=ap.parse_args().command
    {'feature-nulls':feature_nulls,'audio-nulls':audio_nulls,'safeguards':safeguard,'curve-counterexamples':curve_counterexamples}[arg]()
