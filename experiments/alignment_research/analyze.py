"""Descriptive analysis of preserved corpus and new probes; never fits a policy."""
from __future__ import annotations
import collections
import itertools
import json
import numpy as np
from scipy import stats
from study import (read, save, metadata, OUT, ROOT, BASE, SCRATCH, eng, SR, HOP,
                   digest, clean)


def counts(values):
    c=collections.Counter(values);n=len(values)
    a=n-c['SAFE_ABSTAIN']
    return {'n':n,'correct':c['CORRECT_ACCEPT'],'wrong':c['WRONG_ACCEPT'],
            'abstain':c['SAFE_ABSTAIN'],'ambiguous_accept':c['AMBIGUOUS_CONTENT_ACCEPT'],
            'coverage':a/n if n else None,'risk':c['WRONG_ACCEPT']/a if a else None}


def rc(scores,correct):
    scores=np.asarray(scores);correct=np.asarray(correct,dtype=bool)
    out=[]
    # Keep ties together; thresholds below are retrospective plots, not fitted policies.
    for threshold in sorted(set(scores),reverse=True):
        mask=scores>=threshold;n=int(mask.sum());wrong=int((~correct[mask]).sum())
        out.append({'threshold':float(threshold),'accepted':n,'wrong':wrong,
                    'coverage':n/len(scores),'risk':wrong/n})
    return out


def analyze():
    data=read(OUT/'corpus.json');rows=data['rows']
    assert data['complete'] and len(rows)==81
    groups={'exact_positives':[r for r in rows if r['case']['kind']=='positive'],
            'wrong_song':[r for r in rows if r['case']['kind']=='hard_negative'],
            'tiled':[r for r in rows if r['case']['kind']=='tiled'],
            'manual':[r for r in rows if r['case']['kind']=='manual']}
    primary=groups['exact_positives']+groups['wrong_song']
    duplicates=collections.defaultdict(list)
    for r in groups['wrong_song']:
        key=(r['case']['background'],r['case']['target'])
        duplicates[key].append(r['case']['case_id'])
    unique=[];seen=set()
    for r in primary:
        key=(r['case']['kind'],r['case']['background'],r['case']['target']) if r['case']['kind']=='hard_negative' else r['case']['case_id']
        if key not in seen:unique.append(r);seen.add(key)
    groups['primary_76']=primary;groups['primary_deduplicated']=unique
    tables={}
    for group,rs in groups.items():
        tables[group]={}
        for scope in ['methods','predictions']:
            for name in rs[0][scope]:
                tables[group][scope+':'+name]=counts([r[scope][name]['outcome'] for r in rs])
        for name,zfloor,mfloor in [('pcen_z_only',7.,0.),('pcen_margin_only',0.,1.4),('pcen_z_margin',7.,1.4)]:
            vals=[]
            for r in rs:
                m=r['methods']['pcen_hpss'];accept=m['z']>=zfloor and (m['margin'] or 1e10)>=mfloor
                vals.append(m['outcome'] if accept else 'SAFE_ABSTAIN')
            tables[group][name]=counts(vals)
        tables[group]['v2_reason_counts']=dict(collections.Counter(r['predictions']['v2']['reason'] for r in rs))
    scores={};curves={};aucs={}
    for name,method,scorefn in [
        ('HPSS Z','pcen_hpss',lambda x:x['z']),
        ('HPSS margin','pcen_hpss',lambda x:x['margin']),
        ('HPSS Z + margin','pcen_hpss',lambda x:min(x['z']/7,x['margin']/1.4)),
        ('Hybrid Z','hybrid',lambda x:x['z']),
        ('Equal fusion Z','equal_fusion',lambda x:x['z']),
        ('GCC-PHAT peak','gcc_phat',lambda x:x['peak'])]:
        s=[scorefn(r['methods'][method]) for r in primary]
        y=[r['methods'][method]['outcome']=='CORRECT_ACCEPT' for r in primary]
        curves[name]=rc(s,y)
        pos=np.asarray(s)[y];neg=np.asarray(s)[~np.asarray(y)]
        aucs[name]=float(np.mean((pos[:,None]>neg[None,:])+.5*(pos[:,None]==neg[None,:]))) if len(pos) and len(neg) else None
        scores[name]={'scores':s,'correct':y,'case_ids':[r['case']['case_id'] for r in primary]}
    dependence={}
    for a,b in itertools.combinations(['hybrid','onset','pcen_hpss','pcen','chroma'],2):
        exact=groups['exact_positives']
        ea=np.array([r['methods'][a]['outcome']!='CORRECT_ACCEPT' for r in exact])
        eb=np.array([r['methods'][b]['outcome']!='CORRECT_ACCEPT' for r in exact])
        key=a+'|'+b;reverse=b+'|'+a
        cc=[r['curve_correlations'].get(key,r['curve_correlations'].get(reverse)) for r in exact]
        dependence[key]={'both_correct':int((~ea & ~eb).sum()),'only_a_wrong':int((ea & ~eb).sum()),
                         'only_b_wrong':int((~ea & eb).sum()),'both_wrong':int((ea & eb).sum()),
                         'error_phi':float(np.corrcoef(ea,eb)[0,1]) if ea.std() and eb.std() else None,
                         'median_full_curve_r':float(np.median(cc)),
                         'top1_agree_within_015':sum(abs(r['methods'][a]['offset']-r['methods'][b]['offset'])<=.15 for r in exact),
                         'low_snr_L3_L4_curve_r_median':float(np.median([r['curve_correlations'].get(key,r['curve_correlations'].get(reverse)) for r in exact if r['case']['level'] in ['L3','L4']]))}
    # Replay preserved curves through the untouched policy. Quantify that the
    # stored decisions and current frozen implementation are consistent.
    replay=[]
    for r in rows:
        p=SCRATCH/(r['case']['case_id']+'_curves.npz')
        if not p.exists():continue
        fs=[]
        with np.load(p) as arrays:
            for method in ['hybrid','onset','pcen_hpss','pcen']:
                c=arrays[method]
                fs.append(eng.FamilyResult(method,eng.METHOD_FAMILY[method],c,
                       1+round(r['video_s']*SR)//HOP,r['methods'][method]['z'],0))
        d=eng.decide_from_families(fs,SR,HOP,None,r['video_s'],r['music_s'])
        old=r['predictions']['v2']
        match=(d.reason_code==old['reason'] and
               ((d.offset is None and old['offset'] is None) or
                (d.offset is not None and old['offset'] is not None and abs(d.offset-old['offset'])<1e-9)))
        replay.append({'case_id':r['case']['case_id'],'exact_decision_match':match})
    levels={}
    for level in ['L1','L2','L3','L4']:
        rs=[r for r in groups['exact_positives'] if r['case']['level']==level]
        levels[level]={name:counts([r[scope][name]['outcome'] for r in rs]) for scope,name in
                       [('methods','pcen_hpss'),('methods','pcen'),('methods','gcc_phat'),('predictions','v2'),('predictions','no_onset_corroboration')]}
    # Report discrepancies with committed RA-1.2C diagnostics, not only outputs.
    original={r['case_id']:r for split in ['calibration','holdout'] for r in read(BASE/f'results/semi_synthetic_{split}_ra12c.json')}
    discrepancies=[]
    for r in rows:
        old=original.get(r['case']['case_id'])
        if old and (r['predictions']['v2']['outcome']!=old['outcome'] or r['predictions']['v2']['reason']!=old['reason_code']):
            discrepancies.append({'case_id':r['case']['case_id'],'old_outcome':old['outcome'],'new':r['predictions']['v2'],'old_reason':old['reason_code']})
    out={'metadata':metadata('python experiments/alignment_research/analyze.py'),'script_sha256':digest(__file__),
         'preserved_corpus_sha256':digest(OUT/'corpus.json'),'tables':tables,'levels':levels,
         'duplicate_negative_pairs':[{'sources':list(k),'case_ids':v} for k,v in duplicates.items() if len(v)>1],
         'dependence':dependence,'risk_coverage':curves,'descriptive_auc':aucs,'score_data':scores,
         'curve_replay':replay,'historical_decision_discrepancies':discrepancies,
         'zero_error_iid_illustrations':{'n9_95pct_upper':1-.05**(1/9),'n26_95pct_upper':1-.05**(1/26),
                                       'zero_failures_needed_for_1pct_upper_95pct':int(np.ceil(np.log(.05)/np.log(.99)))},
         'notes':'AUCs measure correctness ranking, not probability calibration. Sources and variants are dependent. No fitted thresholds or population confidence claims.'}
    out['additional_probe_summary']=probe_summary()
    save('analysis.json',out)
    print('duplicates',out['duplicate_negative_pairs'])
    print('replay',len(replay),sum(x['exact_decision_match'] for x in replay))
    print('AUC',aucs)
    for name,entry in tables['primary_76'].items():print(name,entry)
    figures(out)


def probe_summary():
    feature=read(OUT/'feature_nulls.json')['rows']
    audio=read(OUT/'audio_nulls.json')['rows']
    real=read(OUT/'mismatch_search.json')['rows']
    clean=read(OUT/'clean_mismatch_search.json')['rows']
    cells=[]
    for duration,dim,ar in itertools.product([30,60,180,600],[1,12,96],[0.,.9]):
        rs=[r for r in feature if r['duration_s']==duration and r['dimensions']==dim and r['ar']==ar]
        cells.append({'duration_s':duration,'dimensions':dim,'ar':ar,'n':len(rs),
                      'max_z_mean':float(np.mean([r['max_z'] for r in rs])),
                      'max_z_min':min(r['max_z'] for r in rs),'max_z_max':max(r['max_z'] for r in rs),
                      'margin_mean':float(np.mean([r['margin'] for r in rs]))})
    mismatch={}
    for name,rows in [('real_wrong_project',real),('clean_wrong_project',clean)]:
        accepted=[r for r in rows if r['offset'] is not None]
        keys=('recording','track') if name.startswith('real') else ('query_track','reference_track')
        mismatch[name]={'n':len(rows),'accepted':len(accepted),'abstained':len(rows)-len(accepted),
            'accept_ids':[[r[keys[0]],r[keys[1]]] for r in accepted],
            'reason_counts':dict(collections.Counter(r['reason'] for r in rows)),
            'hpss_z7_accepts':sum(r['methods']['pcen_hpss']['z']>=7 for r in rows),
            'hpss_margin14_accepts':sum(r['methods']['pcen_hpss']['margin']>=1.4 for r in rows),
            'hpss_both_accepts':sum(r['methods']['pcen_hpss']['z']>=7 and r['methods']['pcen_hpss']['margin']>=1.4 for r in rows)}
    return {'feature_null_cells':cells,'audio_null_n':len(audio),
            'audio_null_accepted':sum(r['offset'] is not None for r in audio),
            'audio_null_method_max_z':{m:max(r['methods'][m]['z'] for r in audio) for m in ['hybrid','onset','pcen','pcen_hpss']},
            'mismatches':mismatch,
            'notes':'The original 20 mismatches are included in the 551; do not add their denominators. Clean directions are paired. Discovery controls are exploratory.'}


def figures(data):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axs=plt.subplots(1,2,figsize=(12,4.4))
    for name in ['HPSS Z','HPSS margin','HPSS Z + margin','Equal fusion Z','GCC-PHAT peak']:
        c=data['risk_coverage'][name]
        axs[0].step([p['coverage'] for p in c],[p['risk'] for p in c],where='post',label=name)
    v=data['tables']['primary_76']['predictions:v2']
    axs[0].scatter(v['coverage'],v['risk'],marker='*',s=160,c='black',label='Frozen v2',zorder=10)
    axs[0].set(xlabel='Coverage (56 exact positives + 20 wrong-song cases)',ylabel='Wrong accepts / accepts',ylim=(-.02,.5),title='Exploratory risk-coverage; no probability calibration')
    axs[0].legend(fontsize=8)
    labels=['L1','L2','L3','L4'];x=np.arange(4)
    for j,(name,color) in enumerate([('v2','#222222'),('no_onset_corroboration','#868686'),('gcc_phat','#2f7294')]):
        vals=[data['levels'][lv][name]['correct']/data['levels'][lv][name]['n'] for lv in labels]
        axs[1].bar(x+(j-1)*.25,vals,.25,label={'v2':'Frozen v2','no_onset_corroboration':'Remove onset gate','gcc_phat':'GCC-PHAT argmax'}[name],color=color)
    axs[1].set(xticks=x,xticklabels=[f'{lv}\nN={data["levels"][lv]["v2"]["n"]}' for lv in labels],ylabel='Correct outputs / exact positives',ylim=(0,1.15),title='Corruption packages confound SNR and processing')
    axs[1].legend(fontsize=8)
    fig.tight_layout();fig.savefig(OUT/'risk_coverage.png',dpi=180);plt.close(fig)
    fig,axs=plt.subplots(1,2,figsize=(12,4.3))
    cells=data['additional_probe_summary']['feature_null_cells']
    for ar,label in [(0.,'Independent frames'),(.9,'AR(1), coefficient 0.9')]:
        rs=[r for r in cells if r['dimensions']==12 and r['ar']==ar]
        x=np.array([r['duration_s'] for r in rs]);y=np.array([r['max_z_mean'] for r in rs])
        low=np.array([r['max_z_min'] for r in rs]);high=np.array([r['max_z_max'] for r in rs])
        axs[0].plot(x,y,'o-',label=label)
        axs[0].fill_between(x,low,high,alpha=.12)
    axs[0].set(xscale='log',xlabel='Duration of each feature sequence (seconds)',ylabel='Maximum full-curve Z',title='12-band null: mean and observed range (16 seeds)')
    axs[0].set_xticks([30,60,180,600],labels=['30','60','180','600']);axs[0].legend(fontsize=8)
    cv=read(OUT/'counterexample_validation.json')['clean_pair_validation']['contributions']['pcen']
    bins=cv['bins_1s'];total=cv['total_signed']
    axs[1].bar([b['reference_start_s'] for b in bins],[100*b['signed_sum']/total for b in bins],width=1.,color='#923f32')
    axs[1].set(xlabel='Reference time (seconds)',ylabel='Signed contribution / total correlation (%)',
               title='Wrong-song ACCEPT: one second contributes 94.6%')
    axs[1].annotate('Global geometric overlap: 148.57 s',xy=(.97,.93),xycoords='axes fraction',ha='right',fontsize=8)
    fig.tight_layout();fig.savefig(OUT/'null_and_counterexample.png',dpi=180);plt.close(fig)


if __name__=='__main__':analyze()
