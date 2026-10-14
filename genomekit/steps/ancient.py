# Ancestry against the Allen Ancient DNA Resource (AADR v66, "HO" panel: ~600k SNPs, modern + ancient genomes).
#  1. Worldwide PCA of present-day populations (the person included as one sample) -> closest populations.
#  2. For West-Eurasian ancestry: a regional PCA, ancient genomes projected onto it, and mixture models
#     (non-negative least squares on PC coordinates, like nMonte/G25) with deep-time and historic-era sources.
# Chip genotypes are used; imputed calls are added only when the chip overlaps the panel poorly.
import re, subprocess
from pathlib import Path
import numpy as np, pandas as pd
from scipy.optimize import nnls
from ..util import jdump, progress

BAD = re.compile(r'(QCremove|-o|_o\b|_o[A-Z]|outlier|Relative|-Dup|Ignore|_lc|contam|WGA)')
WEST_COUNTRIES = {
    'Abkhazia', 'Albania', 'Algeria', 'Armenia', 'Austria', 'Azerbaijan', 'Belarus', 'Belgium', 'Bosnia and Herzegovina', 'Bulgaria', 'Croatia',
    'Cyprus', 'Czechia', 'Czech Republic', 'Denmark', 'Egypt', 'England', 'Estonia', 'Finland', 'France', 'Georgia', 'Germany', 'Greece',
    'Hungary', 'Iceland', 'Iran', 'Iraq', 'Ireland', 'Israel', 'Italy', 'Jordan', 'Kazakhstan', 'Kyrgyzstan', 'Lebanon', 'Libya', 'Lithuania',
    'Latvia', 'Malta', 'Moldova', 'Montenegro', 'Morocco', 'North Macedonia', 'Norway', 'Pakistan', 'Poland', 'Portugal', 'Romania', 'Russia',
    'Saudi Arabia', 'Serbia', 'Slovakia', 'Slovenia', 'Spain', 'Sweden', 'Switzerland', 'Syria', 'Tajikistan', 'Tunisia', 'Turkey',
    'Turkmenistan', 'Ukraine', 'United Kingdom', 'United Arab Emirates', 'Uzbekistan', 'Yemen', 'Kuwait', 'Oman', 'Qatar', 'Bahrain'}
DEEP = {'Anatolian Neolithic farmers': ['Turkey_N', 'Turkey_Catalhoyuk_N', 'Turkey_Catalhoyuk_EN'],
        'Iranian Neolithic farmers': ['Iran_GanjDareh_N'],
        'Caucasus hunter-gatherers': ['Georgia_Kotias_Mesolithic', 'Georgia_KotiasKlde_Mesolithic', 'Georgia_Satsurblia_LateUP'],
        'Levantine Neolithic farmers': ['Israel_PPNB', 'Jordan_PPNB'],
        'Western hunter-gatherers': ['Luxembourg_Loschbour_Mesolithic', 'Italy_North_Villabruna_HG', 'Serbia_IronGates_Mesolithic'],
        'Yamnaya steppe herders': ['Russia_Samara_EBA_Yamnaya', 'Russia_Kalmykia_EBA_Yamnaya', 'Russia_Caspian_Steppe_EBA_Yamnaya'],
        'East Asian': ['Han']}
HIST = {'Byzantine Anatolia': ['Turkey_Medieval_Byzantine', 'Turkey_EarlyMedieval_Byzantine', 'Turkey_LateAntiquity_Byzantine'],
        'Roman Anatolia': ['Turkey_LateAntiquity_ImperialRoman', 'Turkey_ImperialRoman'],
        'Medieval Armenia': ['Armenia_Beniamin_EarlyMedieval', 'Armenia_AgarakTownStadium_Medieval', 'Armenia_Beniamin_Antiquity'],
        'Imperial Rome (Lazio)': ['Italy_Lazio_ImperialRoman_Roman', 'Italy_Lazio_LateAntiquity_ImperialRoman_Roman'],
        'Early Slavs (Poland)': ['Poland_EarlySlav', 'Poland_EarlyMedieval_Slav'],
        'Early-medieval Croatia (Slavic period)': ['Croatia_EarlyMedieval'],
        'Anglo-Saxon England': ['England_EarlyMedieval_Saxon', 'England_Saxon'],
        'Viking-age Scandinavia': ['Sweden_Viking', 'Norway_Viking', 'Denmark_Viking'],
        'Early-medieval Ireland': ['Ireland_EarlyMedieval'],
        'Medieval Iberia': ['Spain_LateAntiquity', 'Spain_Medieval'],
        'Phoenician Levant': ['Israel_Phoenician', 'Lebanon_IA3'],
        'Iron-Age Iran': ['Iran_Hasanlu_IA'],
        'Scythians (Ukraine)': ['Ukraine_LIA_Scythian', 'Ukraine_MIA_Scythian'],
        'Medieval Turkic (Kazakhstan)': ['Kazakhstan_EarlyMedieval_Karakhanid', 'Kazakhstan_Medieval_Nomad', 'Kazakhstan_TurkicPeriod', 'Kazakhstan_Kimak'],
        'Hungarian Conquerors': ['Hungary_Conqueror', 'Hungary_Conqueror_Commoner', 'Hungary_Elite_Conqueror'],
        'Avars (Hungary)': ['Hungary_Avar']}


def load(ctx):
    A = ctx.data / 'aadr'
    snp = pd.read_csv(A / 'v66_HO.snp', sep=r'\s+', header=None, names=['id', 'chr', 'cm', 'pos', 'a1', 'a2'], dtype={'chr': str})
    ind = pd.read_csv(A / 'v66_HO.ind', sep=r'\s+', header=None, names=['iid', 'sex', 'pop'])
    anno = pd.read_csv(A / 'v66_HO.anno', sep='\t', dtype=str, keep_default_na=False)
    ac = anno.columns
    anno = anno.rename(columns={ac[0]: 'gid', ac[10]: 'bp', ac[16]: 'country', ac[29]: 'nsnp'})
    for k in ('bp', 'nsnp'): anno[k] = pd.to_numeric(anno[k], errors='coerce').fillna(0)
    ind = ind.merge(anno[['gid', 'bp', 'country', 'nsnp']].drop_duplicates('gid'), left_on='iid', right_on='gid', how='left')
    ind[['bp', 'nsnp']] = ind[['bp', 'nsnp']].fillna(0)
    ind['ok'] = ~ind.iid.str.contains(BAD) & ~ind['pop'].str.contains(BAD)
    return snp, ind


def person_dosage(ctx, snp):
    me = {}
    for l in open(ctx.genome):
        if l[0] == '#': continue
        rs, c, p, g = l.rstrip('\n').split('\t')
        if c.isdigit() and len(g) == 2 and g != '--': me[(c, int(p))] = g
    amb = {('A', 'T'), ('T', 'A'), ('C', 'G'), ('G', 'C')}
    keep, dos = [], []
    for i, r in enumerate(snp.itertuples()):
        if not r.chr.isdigit() or (r.a1, r.a2) in amb: continue
        g = me.get((r.chr, r.pos))
        if g is None or any(x not in (r.a1, r.a2) for x in g): continue
        keep.append(i); dos.append(g.count(r.a1))
    used_imp = False
    imp = ctx.work / 'imputed'
    if len(keep) < 15000 and (imp / 'me.chr22.vcf.gz').exists():
        # poor chip overlap: add confidently imputed sites (|DS - round(DS)| < 0.1)
        have = set(keep); pos2i = {(r.chr, r.pos): i for i, r in enumerate(snp.itertuples()) if r.chr.isdigit()}
        reg = ctx.work / 'ancient' / 'regions.txt'
        reg.write_text(''.join(f'{c}\t{p}\n' for c, p in pos2i))
        for c in range(1, 23):
            v = subprocess.run(['bcftools', 'view', '-M2', '-T', reg, str(imp / f'me.chr{c}.vcf.gz'), '-Ou'], capture_output=True).stdout
            q = subprocess.run(['bcftools', 'query', '-f', '%CHROM\t%POS\t%REF\t%ALT\t[%DS]\n'], input=v, capture_output=True).stdout.decode()
            for l in q.splitlines():
                ch, p, ref, alt, ds = l.split('\t')
                i = pos2i.get((ch, int(p)))
                if i is None or i in have: continue
                r = snp.iloc[i]; ds = float(ds)
                if (r.a1, r.a2) in amb or {ref, alt} != {r.a1, r.a2} or abs(ds - round(ds)) >= 0.1: continue
                na = round(ds); keep.append(i); dos.append(na if alt == r.a1 else 2 - na); have.add(i)
        o = np.argsort(keep); keep = list(np.array(keep)[o]); dos = list(np.array(dos)[o]); used_imp = True
    return np.array(keep), np.array(dos, float), used_imp


def reader(ctx, nsnp, keep):
    rlen = max(48, (nsnp + 3) // 4)
    def read(idx):
        out = np.empty((len(idx), len(keep)), np.float32)
        with open(ctx.data / 'aadr' / 'v66_HO.geno', 'rb') as f:
            for k, i in enumerate(idx):
                f.seek(48 + rlen * int(i)); b = np.frombuffer(f.read(rlen), np.uint8)
                g = np.stack([(b >> 6) & 3, (b >> 4) & 3, (b >> 2) & 3, b & 3], 1).ravel()[:nsnp]
                out[k] = g[keep]
        out[out == 3] = np.nan
        return out
    return read


def pca_fit(X, k):
    mu = np.nanmean(X, 0); p = mu / 2
    ok = (p > 0.01) & (p < 0.99) & (np.isnan(X).mean(0) < 0.05)
    Z = np.nan_to_num((X[:, ok] - mu[ok]) / np.sqrt(p[ok] * (1 - p[ok])))
    U, S, Vt = np.linalg.svd(Z, full_matrices=False)
    return dict(mu=mu[ok], p=p[ok], ok=ok, V=Vt[:k].T, pcs=Z @ Vt[:k].T, ev=S[:k] ** 2 / (S ** 2).sum())


def project(fit, g):
    z = (g[fit['ok']] - fit['mu']) / np.sqrt(fit['p'] * (1 - fit['p'])); m = ~np.isnan(z)
    return np.linalg.lstsq(fit['V'][m], z[m], rcond=None)[0]


def mixture(M, b):
    """Non-negative weights summing to 1 (soft constraint), as in nMonte/G25 calculators."""
    lam = 1000.0
    coef, _ = nnls(np.vstack([M, lam * np.ones(M.shape[1])]), np.append(b, lam))
    return coef, float(np.sqrt(((M @ coef - b) ** 2).sum()))


def plot(df, cent, me, path, title, anc=None):
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(10, 8))
    cm = plt.get_cmap('tab20')
    for j, (pname, sub) in enumerate(df.groupby('pop')):
        ax.scatter(sub.PC1, sub.PC2, s=7, alpha=.3 if anc is None else .15, color=cm(j % 20) if anc is None else 'lightgrey')
        ax.annotate(pname.replace('_', ' '), (cent.loc[pname, 'PC1'], cent.loc[pname, 'PC2']), fontsize=6.5, alpha=.8, color='black' if anc is None else 'grey')
    if anc:
        for j, (k, v) in enumerate(anc.items()): ax.scatter(v[:, 0], v[:, 1], s=16, color=cm(j % 20), label=k, alpha=.85)
        ax.legend(fontsize=7, loc='best', frameon=False)
    ax.scatter([me[0]], [me[1]], s=240, marker='*', color='#e34948', edgecolor='k', zorder=10)
    ax.annotate('You', (me[0], me[1]), xytext=(8, 8), textcoords='offset points', fontsize=11, fontweight='bold', color='#e34948')
    ax.set_xlabel('PC1'); ax.set_ylabel('PC2'); ax.set_title(title, loc='left', fontsize=12, fontweight='bold')
    for s in ('top', 'right'): ax.spines[s].set_visible(False)
    fig.tight_layout(); fig.savefig(path, dpi=120, facecolor='white'); plt.close(fig)


DEFAULTS = dict(cap=20, k_global=10, n_regional=45, k_regional=25)


def run(ctx):
    out = ctx.work / 'ancient'; out.mkdir(exist_ok=True)
    progress('reading the ancient-DNA reference')
    snp, ind = load(ctx)
    keep, dos, used_imp = person_dosage(ctx, snp)
    res = analyse(ctx, snp, ind, keep, dos, out)
    res['used_imputed'] = used_imp
    return res


def analyse(ctx, snp, ind, keep, dos, out=None, params=None, exclude=(), models=True):
    """Core of the ancestry step, separated so validate_ancestry.py can run held-out reference genomes through it."""
    P = dict(DEFAULTS, **(params or {}))
    read = reader(ctx, len(snp), keep)
    mod = ind[ind.ok & (ind.bp == 0) & ~ind.iid.isin(set(exclude))]
    cnt = mod['pop'].value_counts(); pops = cnt[cnt >= 8].index
    sel = mod[mod['pop'].isin(pops)].sample(frac=1, random_state=1)
    sel = sel[sel.groupby('pop').cumcount() < P['cap']].sort_index()  # at most `cap` people per population
    progress(f'loading {len(sel):,} present-day reference genomes')
    X = read(sel.index.values)
    country = sel.groupby('pop').country.agg(lambda x: x.mode().iat[0] if len(x.mode()) else '')

    def run_pca(rows, k):
        fit = pca_fit(np.vstack([X[rows], dos[None, :]]), k)
        df = pd.DataFrame(fit['pcs'][:-1], columns=[f'PC{i + 1}' for i in range(k)]); df['pop'] = sel['pop'].values[rows]
        cent = df.groupby('pop').mean(); w = np.sqrt(fit['ev'] / fit['ev'][0])
        mep = fit['pcs'][-1]
        dist = pd.Series(np.sqrt((((cent.values - mep) * w) ** 2).sum(1)), cent.index).sort_values()
        return fit, df, cent, w, mep, dist

    # 1. worldwide
    progress('comparing you with 260 present-day populations')
    allrows = np.ones(len(sel), bool)
    fitG, dfG, centG, wG, meG, distG = run_pca(allrows, P['k_global'])
    if out: plot(dfG, centG, meG, out / 'pca_world.png', 'Present-day populations worldwide')
    top = list(distG.index[:10])
    west = sum(country.get(p, '') in WEST_COUNTRIES for p in top) >= 7
    res = dict(n_snps=int(len(keep)), west_eurasian=west, closest_world=distG.head(10).round(4).to_dict())

    # 2. regional zoom: the nearest populations
    near = list(distG.index[:P['n_regional']])
    rows = sel['pop'].isin(near).values
    fitR, dfR, centR, wR, meR, distR = run_pca(rows, P['k_regional'])
    res['closest_modern'] = distR.head(15).round(4).to_dict()
    M = (centR.values * wR).T
    coef, fd = mixture(M, meR * wR)
    mix = pd.Series(coef, centR.index); mix = mix[mix >= 0.03].sort_values(ascending=False)
    res['mixture_modern'] = (mix / mix.sum()).round(3).to_dict(); res['mixture_modern_fit'] = fd
    if out: plot(dfR, centR, meR, out / 'pca_west.png', 'Your region, zoomed in')

    # 3. ancient sources (West Eurasian ancestry only: the source panel is built for that region)
    if west and models:
        anc = {}
        for k, labels in {**DEEP, **HIST}.items():
            progress(f'placing ancient genomes: {k}')
            idx = ind[ind['pop'].isin(labels) & ind.ok & ((ind.bp == 0) | (ind.nsnp > 150000))].index.values
            if k == 'East Asian': idx = idx[:25]
            if not len(idx): continue
            G = read(idx)
            fitR['me_proj'] = project(fitR, dos)
            anc[k] = np.array([project(fitR, g) for g in G])
        b = fitR['me_proj'] * wR
        def model(names):
            names = [n for n in names if n in anc]
            M = np.array([anc[n].mean(0) * wR for n in names]).T
            c, d = mixture(M, b)
            s = pd.Series(c, names); s = s[s >= 0.02].sort_values(ascending=False)
            return (s / s.sum()).round(3).to_dict(), d
        res['mixture_deep'], res['deep_fit'] = model(list(DEEP))
        # historic era: try every 1-3 source combination; keep the simplest model whose fit is within 5% of the best
        progress('testing historic-era mixture models')
        from itertools import combinations
        names = [n for n in HIST if n in anc]
        fits = []
        for k in (1, 2, 3):
            for combo in combinations(names, k):
                w_, d_ = model(list(combo))
                if len(w_) == k: fits.append((d_, k, w_))
        fits.sort(key=lambda x: x[0])
        best_d = fits[0][0]
        simple = min((f for f in fits if f[0] <= best_d * 1.05), key=lambda f: (f[1], f[0]))
        res['mixture_historic'], res['historic_fit'] = simple[2], simple[0]
        res['historic_alternatives'] = [dict(weights=f[2], fit=round(f[0], 3)) for f in fits[:8]]
        nearest = {k: float(np.sqrt((((v - fitR['me_proj']) * wR) ** 2).sum(1)).min()) for k, v in anc.items() if k in HIST}
        res['nearest_historic'] = dict(sorted(nearest.items(), key=lambda x: x[1])[:6])
        if out: plot(dfR, centR, fitR['me_proj'], out / 'pca_ancient.png', 'Ancient groups projected onto present-day variation',
             anc={k: v for k, v in anc.items() if k in res['mixture_historic'] or k in res['mixture_deep']})
    return res
