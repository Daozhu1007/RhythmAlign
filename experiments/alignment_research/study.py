"""Frozen-implementation research; writes only this directory and ignored scratch.

Run from repository root with Python 3.10 and the recorded scientific stack.
Commands: audit, corpus, probes, summarize. No production monkeypatch persists.
"""
from __future__ import annotations

import argparse
import collections
import contextlib
import dataclasses
import hashlib
import importlib.metadata
import itertools
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

import numpy as np
from scipy import fft, signal, stats

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import alignment_engine_v2 as eng
import auto_sync
import librosa
import imageio_ffmpeg
from experiments.low_snr_alignment import semi_synthetic as ss
from experiments.low_snr_alignment.semi_synthetic_eval import _iter_split_cases

BASE = ROOT / 'experiments/low_snr_alignment'
OUT = Path(__file__).resolve().parent / 'results'
SCRATCH = ROOT / 'results/alignment_research'
SHA = 'ffa6b07a591dbdb54ae8350f3d27dce3ed74c847'
SR, HOP, SEED = 22050, 512, 20260912


def read(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


def clean(x):
    if isinstance(x, dict):
        return {str(k): clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [clean(v) for v in x]
    if isinstance(x, np.ndarray):
        return clean(x.tolist())
    if isinstance(x, (np.integer, np.bool_)):
        return x.item()
    if isinstance(x, (float, np.floating)):
        return float(x) if np.isfinite(x) else None
    return x


def save(name, payload):
    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / name
    tmp = target.with_suffix(target.suffix + '.tmp')
    tmp.write_text(json.dumps(clean(payload), indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    tmp.replace(target)


def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(4 << 20), b''):
            h.update(block)
    return h.hexdigest()


def metadata(command):
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    # Research commits may advance HEAD. Pin the actual scientific inputs,
    # tolerating only checkout newline conversion, never algorithm changes.
    pinned = ['auto_sync.py', 'alignment_engine_v2.py',
              'experiments/low_snr_alignment/semi_synthetic.py',
              'experiments/low_snr_alignment/semi_synthetic_plan.json']
    for name in pinned:
        original = subprocess.check_output(['git', 'show', SHA + ':' + name], cwd=ROOT)
        current = (ROOT/name).read_bytes()
        if current.replace(b'\r\n', b'\n') != original.replace(b'\r\n', b'\n'):
            raise RuntimeError('Frozen scientific input changed: ' + name)
    return {'baseline_sha': SHA, 'research_head': head, 'command': command, 'python': platform.python_version(),
            'platform': platform.system(), 'machine': platform.machine(), 'seed': SEED,
            'sr': SR, 'hop': HOP, 'policy': dataclasses.asdict(eng.DEFAULT_POLICY),
            'dependencies': {p: importlib.metadata.version(p) for p in
                             ['numpy', 'scipy', 'librosa', 'numba', 'soundfile', 'imageio-ffmpeg', 'matplotlib', 'pytest']},
            'source_hashes': {str(p.relative_to(ROOT)).replace('\\', '/'): digest(p)
                              for p in [ROOT/'auto_sync.py', ROOT/'alignment_engine_v2.py', Path(__file__), BASE/'semi_synthetic.py', BASE/'semi_synthetic_plan.json']},
            'epistemic_status': 'exploratory; historical sources already exposed during development'}


def audit():
    plan = read(BASE/'semi_synthetic_plan.json')
    files = sorted((BASE/'results').glob('*.json'))
    info = {'metadata': metadata('python experiments/alignment_research/study.py audit'),
            'committed_results': {p.name: {'sha256': digest(p), 'entries': len(read(p))} for p in files},
            'current_split_audit': ss.audit_split(plan)}
    prior = read(BASE/'results/real_corpus_ra12b.json')
    prior_ids = {r['case_id'] for r in prior}
    ho = plan['split']['holdout_projects']
    ho_recs = [rid for pid in ho for rid in plan['split']['projects'][pid]['recordings']]
    info['historical_holdout_recordings_seen_in_ra12b'] = sorted(set(ho_recs) & prior_ids)
    info['historical_holdout_projects_seen_in_ra12b'] = ho
    for split in ['calibration', 'holdout']:
        rows = read(BASE/f'results/semi_synthetic_{split}_ra12c.json')
        negatives = [r for r in rows if r['class'] != 'semi_synthetic_positive']
        info[split] = {'n': len(rows), 'outcomes': dict(collections.Counter(r['outcome'] for r in rows)),
                       'per_level': {lv: dict(collections.Counter(r['outcome'] for r in rows if r.get('level') == lv)) for lv in ['L1','L2','L3','L4']},
                       'negative_rows': [{'case_id': r['case_id'], 'class': r['class'], **r['family_null_stats']} for r in negatives]}
    info['all_positive_seeds_unique'] = len({c['seed'] for c in plan['positives']}) == len(plan['positives'])
    info['split_auditor_enforces_seed_uniqueness'] = False
    info['pcen_sweep_actual_config_count'] = 3 * 2 * 3 * 2
    save('audit.json', info)
    print(json.dumps({k:v for k,v in info.items() if k not in ['metadata','committed_results','calibration','holdout']}, indent=2))


class AudioSources:
    def __init__(self):
        self.mapping = read(BASE/'local_sources.json')
        self.manifest = {}
        SCRATCH.mkdir(parents=True, exist_ok=True)

    def get(self, kind, sid):
        source = Path(self.mapping[kind][sid])
        key = kind + ':' + sid
        if key not in self.manifest:
            self.manifest[key] = {'id': sid, 'kind': kind, 'sha256': digest(source), 'bytes': source.stat().st_size}
        hashed = self.manifest[key]['sha256']
        cache = SCRATCH / (hashed + f'_{SR}.npy')
        if not cache.exists():
            # Decode from original media, bypass the historical first-megabyte cache.
            cmd = [imageio_ffmpeg.get_ffmpeg_exe(), '-v', 'error', '-i', str(source),
                   '-vn', '-ac', '1', '-ar', str(SR), '-acodec', 'pcm_s16le', '-f', 's16le', '-']
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                  **auto_sync._subprocess_no_window_kwargs())
            if proc.returncode:
                raise RuntimeError(f'Audio decode failed for {sid}; exit {proc.returncode}')
            y = np.frombuffer(proc.stdout, dtype='<i2').astype(np.float32) / 32768
            np.save(cache, y)
        y = np.load(cache)
        self.manifest[key].update({'samples':len(y), 'decoded_sha256': hashlib.sha256(y.tobytes()).hexdigest()})
        return y


def curve_summary(fr):
    if fr.error or not fr.curve.size:
        raise RuntimeError('Feature generator failed: ' + fr.method)
    peaks = eng._independent_peak_indices(fr.curve, int(1.5 * SR / HOP))
    margin = fr.curve[peaks[0]] / fr.curve[peaks[1]] if len(peaks)>1 and fr.curve[peaks[1]]>0 else np.inf
    return {'offset': eng._index_to_offset(int(peaks[0]), fr.n_video_frames, HOP, SR),
            'z': float(auto_sync._correlation_z_score(fr.curve)), 'margin':float(margin),
            'top4_offsets': [eng._index_to_offset(int(i), fr.n_video_frames, HOP, SR) for i in peaks[:4]],
            'runtime_s': fr.runtime_s}


def outcome(offset, spec):
    if offset is None:
        return 'SAFE_ABSTAIN'
    if spec['kind'] in ['positive','manual']:
        return 'CORRECT_ACCEPT' if abs(offset-spec['offset_s']) <= spec['tolerance_s'] else 'WRONG_ACCEPT'
    if spec['kind'] == 'tiled':
        distance = abs(offset / spec['tile_s'] - round(offset / spec['tile_s'])) * spec['tile_s']
        return 'AMBIGUOUS_CONTENT_ACCEPT' if distance <= 0.15 else 'WRONG_ACCEPT'
    return 'WRONG_ACCEPT'


def waveform_baselines(v, m):
    # Explicit common resampling for both waveform baselines: 22,050 -> 7,350 Hz.
    rate = SR / 3
    v = signal.resample_poly(v, 1, 3).astype(np.float64)
    m = signal.resample_poly(m, 1, 3).astype(np.float64)
    v -= v.mean(); m -= m.mean()
    nv,nm = len(v),len(m)
    lags = np.arange(-(nv-1),nm)
    ms,me = np.maximum(0,lags), np.minimum(nm,lags+nv)
    vs,ve = np.maximum(0,-lags), np.minimum(nv,nm-lags)
    overlap = me-ms
    valid = overlap >= 30*rate
    if not np.any(valid):
        return {'wave_ncc': {'offset':None}, 'gcc_phat': {'offset':None}}
    cm,cv = np.r_[0.,np.cumsum(m*m)],np.r_[0.,np.cumsum(v*v)]
    sm,sv = np.r_[0.,np.cumsum(m)],np.r_[0.,np.cumsum(v)]
    cross=signal.correlate(m,v,mode='full',method='fft')
    # Pearson NCC with means and energies recomputed over each lag's overlap.
    n=np.maximum(overlap,1)
    em=cm[me]-cm[ms]-(sm[me]-sm[ms])**2/n
    ev=cv[ve]-cv[vs]-(sv[ve]-sv[vs])**2/n
    numerator=cross-(sm[me]-sm[ms])*(sv[ve]-sv[vs])/n
    denom=np.sqrt(np.maximum(em,0)*np.maximum(ev,0))
    valid &= denom>1e-12
    ncc=np.where(valid,numerator/np.maximum(denom,1e-12),-np.inf)
    k=int(np.argmax(ncc))
    out={'wave_ncc':{'offset':float(-lags[k]/rate),'peak':float(ncc[k]),'analysis_sr':rate,'min_overlap_s':30}}
    nfft=fft.next_fast_len(nm+nv-1)
    spectrum=fft.rfft(m,nfft)*np.conj(fft.rfft(v,nfft))
    cc=fft.irfft(spectrum/np.maximum(np.abs(spectrum),1e-12),nfft)
    cc=np.r_[cc[-(nv-1):],cc[:nm]]
    k=int(np.argmax(np.where(valid,cc,-np.inf)))
    out['gcc_phat']={'offset':float(-lags[k]/rate),'peak':float(cc[k]),'analysis_sr':rate,'min_overlap_s':30}
    return out


def decision_record(d, spec):
    return {'offset':d.offset,'outcome':outcome(d.offset,spec),'reason':d.reason_code}


def compute_case(v,m,spec):
    t0=time.perf_counter()
    fams=eng._run_generators(v,m,SR,HOP)
    d=eng.decide_from_families(fams,SR,HOP,None,len(v)/SR,len(m)/SR)
    methods={f.method:curve_summary(f) for f in fams}
    for r in methods.values():
        r['outcome']=outcome(r['offset'],spec)
    byname={f.method:f for f in fams}
    # Extract chroma separately to quantify onset contamination in the tonal family.
    ct=time.perf_counter()
    co,cz,cc=auto_sync._align_chroma(v,m,SR,HOP)
    cf=eng.FamilyResult('chroma',eng.FAMILY_TONAL,cc,1+len(v)//HOP,float(cz),time.perf_counter()-ct)
    methods['chroma']=curve_summary(cf);methods['chroma']['outcome']=outcome(co,spec)
    fused=sum(auto_sync._normalize_correlation(byname[k].curve) for k in ['hybrid','pcen_hpss','onset'])/3
    ff=eng.FamilyResult('equal_fusion','fusion',fused,1+len(v)//HOP,float(auto_sync._correlation_z_score(fused)),0)
    methods['equal_fusion']=curve_summary(ff);methods['equal_fusion']['outcome']=outcome(methods['equal_fusion']['offset'],spec)
    wave=waveform_baselines(v,m)
    for name,r in wave.items():
        r['outcome']=outcome(r['offset'],spec)
        methods[name]=r
    ho=methods['hybrid']['offset'] if methods['hybrid']['z']>=2 else None
    if ho is None:
        of=byname['onset']
        ratio=auto_sync._independent_peak_ratio(of.curve,int(1.5*SR/HOP))
        if methods['onset']['z']>=2 and ratio>=1.05:
            ho=methods['onset']['offset']
    predictions={'v1':{'offset':ho,'outcome':outcome(ho,spec)},'v2':decision_record(d,spec)}
    # Naive 2-of-4 method vote with deterministic greatest-support/highest-Z tie break.
    votes=[]
    for anchor in fams:
        off=methods[anchor.method]['offset']
        group=[f.method for f in fams if abs(methods[f.method]['offset']-off)<=.15]
        if len(group)>=2:
            votes.append((len(group),max(methods[g]['z'] for g in group),off))
    off=max(votes)[2] if votes else None
    predictions['naive_vote']={'offset':off,'outcome':outcome(off,spec)}
    variants={
        'no_hpss':([f for f in fams if f.method!='pcen_hpss'],None),
        'no_plain_pcen':([f for f in fams if f.method!='pcen'],None),
        'no_tonal':([f for f in fams if f.family!=eng.FAMILY_TONAL],None),
        'no_overlap':(fams,dataclasses.replace(eng.DEFAULT_POLICY,min_overlap_s=0)),
        'no_uniqueness':(fams,dataclasses.replace(eng.DEFAULT_POLICY,margin_floor_a=0,margin_floor_b=0)),
        'pure_tonal':([dataclasses.replace(cf,method='hybrid') if f.method=='hybrid' else f for f in fams],None),
    }
    for name,(fs,policy) in variants.items():
        dd=eng.decide_from_families(fs,SR,HOP,policy,len(v)/SR,len(m)/SR)
        predictions[name]=decision_record(dd,spec)
    # Isolated removal of onset corroboration from CASE B, retaining CASE A.
    original=eng._case_b_failed_checks
    try:
        eng._case_b_failed_checks=lambda cl,p:[s for s in original(cl,p) if not s.startswith('onset_')]
        dd=eng.decide_from_families(fams,SR,HOP,None,len(v)/SR,len(m)/SR)
    finally:
        eng._case_b_failed_checks=original
    predictions['no_onset_corroboration']=decision_record(dd,spec)
    # Explicitly bypass both ambiguity mechanisms; strongest qualifying cluster wins.
    cls=eng._build_clusters(fams,eng.DEFAULT_POLICY,SR,HOP,len(v)/SR,len(m)/SR)
    qualifying=[c for c in cls if c['overlap_s']>=30 and
                (not eng._case_a_failed_checks(c,eng.DEFAULT_POLICY) or not eng._case_b_failed_checks(c,eng.DEFAULT_POLICY))]
    off=eng._choose_offset(max(qualifying,key=eng._cluster_score)) if qualifying else None
    predictions['no_ambiguity']={'offset':off,'outcome':outcome(off,spec)}
    curves={**{f.method:f.curve for f in fams},'chroma':cc}
    dep={a+'|'+b:float(np.corrcoef(curves[a],curves[b])[0,1]) for a,b in itertools.combinations(curves,2)}
    SCRATCH.mkdir(parents=True,exist_ok=True)
    np.savez_compressed(SCRATCH/(spec['case_id']+'_curves.npz'),**curves)
    return {'case':spec,'video_s':len(v)/SR,'music_s':len(m)/SR,'methods':methods,
            'predictions':predictions,'curve_correlations':dep,'clusters':d.clusters,
            'runtime_s':time.perf_counter()-t0}


def corpus(limit=None):
    sources=AudioSources();plan=read(BASE/'semi_synthetic_plan.json')
    specs=[]
    for split in ['calibration','holdout']:
        specs.extend([{**c,'split':'historical_'+split} for c in _iter_split_cases(plan,split)])
    specs.append({'kind':'manual','case_id':'manual_anchor','background':'lingduihua_132','target':'tr_lingduihua',
                  'offset_s':12.4,'tolerance_s':.4,'split':'development_manual'})
    # Existing wrong-song cases are a separate development stratum.
    local=read(BASE/'local_corpus.json')['cases']
    for c in local:
        if c['class']!='negative_mismatch':continue
        rid=next(k for k,p in sources.mapping['recordings'].items() if p==c['video'])
        tid=next(k for k,p in sources.mapping['tracks'].items() if p==c['music'])
        specs.append({'kind':'hard_negative','case_id':c['case_id'],'background':rid,'target':tid,'split':'development_mismatch'})
    if limit is not None:specs=specs[:limit]
    rows=[]
    for i,spec in enumerate(specs):
        v=sources.get('recordings',spec['background']);m=sources.get('tracks',spec['target'])
        if spec['kind']=='positive':
            v,_=ss.build_positive(v,m,spec['offset_s'],spec['gain_db'],spec['condition'],spec['seed'])
            spec['sample_exact_offset_s']=round(spec['offset_s']*SR)/SR
        elif spec['kind']=='tiled':
            v,_=ss.build_tiled(v,m,spec['tile_s'],spec['gain_db'],spec['condition'],spec['seed'])
        row=compute_case(v,m,spec);rows.append(row)
        save('corpus.json',{'metadata':metadata('python experiments/alignment_research/study.py corpus'),
                            'sources':sources.manifest,'rows':rows,'expected_n':len(specs),'complete':len(rows)==len(specs)})
        print(f'{i+1}/{len(specs)} {spec["case_id"]} {row["predictions"]["v2"]} {row["runtime_s"]:.1f}s',flush=True)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('command',choices=['audit','corpus'])
    ap.add_argument('--limit',type=int)
    args=ap.parse_args()
    if args.command=='audit':audit()
    else:corpus(args.limit)


if __name__=='__main__':
    main()
