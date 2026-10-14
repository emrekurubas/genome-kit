# Polygenic scores with ancestry-adjusted percentiles (the pgsc_calc "Z_norm2" method, run locally on the
# 1000 Genomes panel): PCA of the panel, the person projected onto it, score mean and variance modelled along the PCs.
# Also writes the continental-ancestry estimate (ancestry.json) and a PCA plot.
import json, os, subprocess
from pathlib import Path
import numpy as np, pandas as pd
from ..util import run as sh, jdump, jload, progress
from ..kb.pgs import SCORES

CHROMS = [str(c) for c in range(1, 23)]
POPNAME = dict(GBR='British', FIN='Finnish', CEU='Utah residents (NW-European ancestry)', TSI='Tuscan (Italy)', IBS='Iberian (Spain)',
               CHB='Han Chinese (Beijing)', JPT='Japanese', CHS='Southern Han Chinese', CDX='Dai Chinese', KHV='Kinh (Vietnam)',
               YRI='Yoruba (Nigeria)', LWK='Luhya (Kenya)', GWD='Gambian', MSL='Mende (Sierra Leone)', ESN='Esan (Nigeria)',
               ASW='African American (SW USA)', ACB='African Caribbean (Barbados)', MXL='Mexican (Los Angeles)', PUR='Puerto Rican',
               CLM='Colombian', PEL='Peruvian', GIH='Gujarati (India)', PJL='Punjabi (Pakistan)', BEB='Bengali (Bangladesh)',
               STU='Sri Lankan Tamil', ITU='Indian Telugu')
HIGHLD = '6\t25000000\t34000000\tMHC\n8\t7000000\t13000000\tinv8\n17\t40000000\t46000000\tinv17\n5\t44000000\t51500000\tr5\n11\t45000000\t57000000\tr11\n'


def panel_shared(data, threads):
    """Merge the per-chromosome panel subsets and run the reference PCA once (shared, public)."""
    p = Path(data) / 'panel'
    for kind in ('pgs', 'pca'):
        if not (p / f'{kind}_all.pgen').exists():
            (p / f'{kind}.list').write_text('\n'.join(str(p / f'{kind}.chr{c}') for c in CHROMS) + '\n')
            sh(['plink2', '--pmerge-list', p / f'{kind}.list', 'pfile', '--threads', threads, '--memory', '6000', '--out', p / f'{kind}_all', '--silent'])
            for c in CHROMS:
                for ext in ('pgen', 'pvar', 'psam', 'log'): (p / f'{kind}.chr{c}.{ext}').unlink(missing_ok=True)
    if not (p / 'pca.eigenvec.allele').exists():
        (p / 'highld.txt').write_text(HIGHLD)
        sh(['plink2', '--pfile', p / 'pca_all', '--exclude', 'bed1', p / 'highld.txt', '--indep-pairwise', '1000kb', '1', '0.1',
            '--threads', threads, '--out', p / 'prune', '--silent'])
        sh(['plink2', '--pfile', p / 'pca_all', '--extract', p / 'prune.prune.in', '--pca', '10', 'allele-wts', '--freq', 'counts',
            '--threads', threads, '--out', p / 'pca', '--silent'])
        project(p / 'pca_all', p, p / 'pca_ref', threads)


def project(pfile, p, out, threads):
    sh(['plink2', '--pfile', pfile, '--extract', p / 'prune.prune.in', '--read-freq', p / 'pca.acount',
        '--score', p / 'pca.eigenvec.allele', '2', '5', 'header-read', 'no-mean-imputation', 'variance-standardize', 'cols=+scoresums',
        '--score-col-nums', '6-15', '--threads', threads, '--out', out, '--silent'])


def user_pgen(ctx):
    """Imputed dosages at score + PCA variants -> work/pgs/me.pgen."""
    w = ctx.work / 'pgs'; w.mkdir(exist_ok=True)
    if (w / 'me.pgen').exists(): return w / 'me'
    p = ctx.data / 'panel'
    keep = w / 'keep_ids.txt'
    ids = set(open(ctx.data / 'pgs' / 'plink' / 'all_ids.txt').read().split()) | set(open(p / 'prune.prune.in').read().split())
    keep.write_text('\n'.join(sorted(ids)) + '\n')
    lst = []
    for c in CHROMS:
        tmp = w / f'tmp.chr{c}.vcf.gz'
        sh(['bcftools', 'view', '-M2', '-Oz', '-o', tmp, ctx.work / 'imputed' / f'me.chr{c}.vcf.gz'])
        sh(['plink2', '--vcf', tmp, 'dosage=DS', '--set-all-var-ids', '@:#:$r:$a', '--new-id-max-allele-len', '100', 'truncate',
            '--extract', keep, '--make-pgen', '--threads', ctx.threads, '--out', w / f'me.chr{c}', '--silent'])
        tmp.unlink(); lst.append(str(w / f'me.chr{c}'))
    (w / 'me.list').write_text('\n'.join(lst) + '\n')
    sh(['plink2', '--pmerge-list', w / 'me.list', 'pfile', '--threads', ctx.threads, '--out', w / 'me', '--silent'])
    for c in CHROMS:
        for ext in ('pgen', 'pvar', 'psam', 'log'): (w / f'me.chr{c}.{ext}').unlink(missing_ok=True)
    return w / 'me'


def read_pcs(f):
    d = pd.read_csv(f, sep='\t').rename(columns={'#IID': 'IID', '#FID': 'FID'})
    cols = [c for c in d.columns if c.startswith('PC') and c.endswith('_SUM')]
    d = d[['IID'] + cols]; d.columns = ['IID'] + [f'PC{i + 1}' for i in range(len(cols))]
    return d


def run(ctx):
    from scipy.stats import norm
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.linear_model import LinearRegression, GammaRegressor
    data, w, T = ctx.data, ctx.work / 'pgs', ctx.threads
    p = data / 'panel'
    progress('preparing the 1000 Genomes reference (once per computer)')
    panel_shared(data, T)
    progress('collecting your genotypes at the score positions')
    me = user_pgen(ctx)
    progress('placing you among the 1000 Genomes populations')
    project(me, p, w / 'pca_me', T)

    # ---- ancestry along the reference PCs
    samp = pd.read_csv(data / 'ref1kg' / 'integrated_call_samples_v3.20130502.ALL.panel', sep='\t', usecols=[0, 1, 2], names=['IID', 'pop', 'superpop'], header=0)
    ref = read_pcs(f'{p / "pca_ref"}.sscore').merge(samp, on='IID')
    mp = read_pcs(f'{w / "pca_me"}.sscore')
    PCS = [f'PC{i + 1}' for i in range(10)]
    X, Xme = ref[PCS].values, mp[PCS].values
    sd = X.std(0); Xs, Xmes = X / sd, Xme / sd
    rf = RandomForestClassifier(n_estimators=500, random_state=1).fit(Xs, ref.superpop)
    prob = dict(zip(rf.classes_, [float(x) for x in rf.predict_proba(Xmes)[0].round(3)]))
    best = max(prob, key=prob.get)
    cent = ref.groupby('pop')[PCS].mean()
    dist = pd.Series(np.sqrt(((cent.values - Xme) ** 2).sum(1)) / np.sqrt((sd ** 2).sum()), cent.index).sort_values()
    # Is the person a close match to any reference population? Compare their distance to the nearest population
    # centre with how far that population's own members lie from it (95th percentile).
    near = dist.index[0]
    own = ref[ref['pop'] == near][PCS].values
    spread = np.quantile(np.sqrt(((own - cent.loc[near].values) ** 2).sum(1)) / np.sqrt((sd ** 2).sum()), 0.95)
    close = bool(dist.iloc[0] <= spread)
    sp_of = ref.groupby('pop').superpop.first()
    jdump(dict(superpop_prob=prob, best=best, close_match=close, nearest=dist.head(10).round(3).to_dict(),
               nearest_superpops=[sp_of[k] for k in dist.index[:5]], nearest_names=[POPNAME.get(k, k) for k in dist.index[:10]]),
          ctx.work / 'ancestry.json')
    plot(ref, Xme, w / 'pca.png')

    # ---- scores
    meta = jload(data / 'pgs' / 'plink' / 'meta.json', {})
    (p / 'scores').mkdir(exist_ok=True); (w / 'scores').mkdir(exist_ok=True)
    out = []
    for i, s in enumerate(SCORES, 1):
        progress(f'score {i} of {len(SCORES)}: {s["label"]}')
        pid = s['id']; sf = data / 'pgs' / 'plink' / f'{pid}.score'
        for pf, o in ((p / 'pgs_all', p / 'scores' / pid), (me, w / 'scores' / pid)):
            if not Path(f'{o}.sscore').exists():
                sh(['plink2', '--pfile', pf, '--score', sf, '1', '2', '3', 'cols=+scoresums', 'no-mean-imputation', 'ignore-dup-ids',
                    'list-variants', '--threads', T, '--out', o, '--silent'], check=False)
        if not Path(f'{w / "scores" / pid}.sscore').exists() or not Path(f'{p / "scores" / pid}.sscore').exists(): continue
        r = pd.read_csv(f'{p / "scores" / pid}.sscore', sep='\t').rename(columns={'#IID': 'IID'})[['IID', 'SCORE1_SUM']].merge(ref, on='IID')
        m = float(pd.read_csv(f'{w / "scores" / pid}.sscore', sep='\t')['SCORE1_SUM'].iloc[0])
        y = r.SCORE1_SUM.values; Xr = r[PCS].values / sd
        lr = LinearRegression().fit(Xr, y); res = y - lr.predict(Xr)
        res_me = m - lr.predict(Xmes)[0]
        g = GammaRegressor(alpha=0, max_iter=1000).fit(Xr, np.maximum(res ** 2, 1e-12 * res.var()))
        z2 = res_me / np.sqrt(g.predict(Xmes)[0])
        pct = float(norm.cdf(z2) * 100)
        pct_eur = float((r.loc[r.superpop == 'EUR', 'SCORE1_SUM'] < m).mean() * 100)
        pct_best = float((r.loc[r.superpop == best, 'SCORE1_SUM'] < m).mean() * 100)
        nvar = sum(1 for _ in open(f'{w / "scores" / pid}.sscore.vars')) if Path(f'{w / "scores" / pid}.sscore.vars').exists() else None
        out.append(dict(id=pid, trait=meta.get(pid, {}).get('trait'), z=float(z2), pct=round(pct, 1), pct_eur=round(pct_eur, 1), pct_superpop=round(pct_best, 1),
                        n_weights=meta.get(pid, {}).get('n'), n_used=nvar, ancestry_sensitive=bool(abs(pct - pct_eur) > 25)))
    note = ('Percentiles are adjusted for ancestry using the 1000 Genomes reference (2,504 people from 26 populations), so you are compared with '
            'people of similar genetic ancestry. ' + ('' if close else 'Your DNA is not a close match to any single reference population '
            '(the reference has no Middle Eastern, Caucasus, North African or Central Asian groups), so these percentiles are somewhat less certain.'))
    jdump(dict(scores=out, reference_note=note, best_superpop=best), ctx.work / 'pgs.json')
    return f'{len(out)} scores; nearest reference population: {POPNAME.get(near, near)}{"" if close else " (not a close match)"}'


def plot(ref, Xme, path):
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    COL = {'EUR': '#2a78d6', 'EAS': '#eda100', 'SAS': '#1baf7a', 'AFR': '#4a3aa7', 'AMR': '#e87ba4'}
    NAME = {'EUR': 'European', 'EAS': 'East Asian', 'SAS': 'South Asian', 'AFR': 'African', 'AMR': 'Admixed American'}
    plt.rcParams.update({'font.size': 11, 'axes.spines.top': False, 'axes.spines.right': False})
    fig, ax = plt.subplots(figsize=(8, 6))
    for g in ['AFR', 'AMR', 'EAS', 'SAS', 'EUR']:
        sub = ref[ref.superpop == g]
        ax.scatter(sub.PC1, sub.PC2, s=8, alpha=.45, color=COL[g], label=NAME[g], linewidths=0)
    ax.scatter(Xme[0, 0], Xme[0, 1], s=260, marker='*', color='#e34948', edgecolor='black', linewidths=1, zorder=10, label='You')
    ax.set_xlabel('PC1'); ax.set_ylabel('PC2'); ax.legend(frameon=False, fontsize=9)
    fig.tight_layout(); fig.savefig(path, dpi=130, facecolor='white'); plt.close(fig)
