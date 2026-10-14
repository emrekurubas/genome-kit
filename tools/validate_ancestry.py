# Validate the ancient-DNA ancestry step on PUBLIC reference genomes only (no user data).
# Present-day AADR individuals are held out of the reference one at a time, reduced to a chip-sized random SNP subset,
# and run through genomekit.steps.ancient.analyse exactly like a user. Settings are compared across all world regions.
#
# Usage (from the repo root, inside the tool environment, e.g. after one ./run.sh):
#   .tools/envs/core/bin/python tools/validate_ancestry.py --data data --out validation
# Writes validation/ancestry_holdout.tsv (one row per person x setting) and validation/ancestry_summary.md
import argparse, itertools, json, sys, time
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from genomekit.steps import ancient as A

REGION = {}
for r, cs in {
    'Europe': 'Belarus Bulgaria Croatia Czechia Estonia Finland France Greece Hungary Iceland Italy Lithuania Malta Moldova Norway Poland Romania Serbia Spain Ukraine United_Kingdom',
    'Middle East & North Africa': 'Algeria Egypt Iran Iraq Israel Jordan Lebanon Libya Morocco Tunisia Turkey United_Arab_Emirates Yemen',
    'Caucasus': 'Abkhazia Armenia Azerbaijan Georgia',
    'Central & South Asia': 'Bangladesh India Kazakhstan Kyrgyzstan Nepal Pakistan Sri_Lanka Tajikistan Uzbekistan',
    'East & Southeast Asia': 'Brunei Cambodia China Japan Laos Mongolia Myanmar Philippines Singapore Taiwan Thailand Vietnam',
    'Sub-Saharan Africa': 'Barbados Central_African_Republic Congo Gambia Kenya Malawi Namibia Nigeria Senegal Sierra_Leone South_Africa',
    'Americas': 'Brazil Colombia Mexico Peru Puerto_Rico',
    'Oceania': 'Australia Papua_New_Guinea Federated_States_of_Micronesia',
}.items():
    for c in cs.split(): REGION[c.replace('_', ' ')] = r
MIXED = ['Uyghur', 'Hazara', 'MXL', 'ASW', 'PUR', 'Turkmen', 'Kazakh', 'Tatar_Kazan', 'Gagauz', 'BedouinB']


class Ctx:
    def __init__(self, data): self.data = Path(data)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--data', default='data'); ap.add_argument('--out', default='validation')
    ap.add_argument('--per-region', type=int, default=4); ap.add_argument('--snps', type=int, default=25000)
    ap.add_argument('--quick', action='store_true', help='default settings only')
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    ctx = Ctx(a.data)
    snp, ind = A.load(ctx)
    amb = {('A', 'T'), ('T', 'A'), ('C', 'G'), ('G', 'C')}
    ok_snp = np.array([c.isdigit() and (x, y) not in amb for c, x, y in zip(snp.chr, snp.a1, snp.a2)])
    rng = np.random.default_rng(7)
    mod = ind[ind.ok & (ind.bp == 0)]
    cnt = mod['pop'].value_counts()
    country = mod.groupby('pop').country.agg(lambda x: x.mode().iat[0] if len(x.mode()) else '')
    eligible = [p for p in cnt.index if cnt[p] >= 12]  # still >= 8 left after holding one out
    # held-out people: per region, up to N populations (one person each), plus known mixed populations
    picks = []
    for reg in dict.fromkeys(REGION.values()):
        pops = [p for p in eligible if REGION.get(country.get(p, '')) == reg]
        for p in rng.permutation(pops)[:a.per_region]: picks.append((p, reg))
    picks += [(p, 'mixed') for p in MIXED if p in eligible and p not in [x for x, _ in picks]]
    print(f'{len(picks)} held-out people from {len({r for _, r in picks})} groups', flush=True)

    grid = [A.DEFAULTS] if a.quick else [dict(A.DEFAULTS, cap=c, k_regional=k, n_regional=n)
                                         for c, k, n in itertools.product((20, 50), (6, 10, 25), (30, 45, 70))]
    rows = []
    t0 = time.time()
    for i, (pop, reg) in enumerate(picks):
        iid = mod[mod['pop'] == pop].sample(1, random_state=i).iid.iat[0]
        # the person's genotypes at a random chip-sized SNP subset
        full = A.reader(ctx, len(snp), np.arange(len(snp)))(ind.index[ind.iid == iid].values)[0]
        cand = np.where(ok_snp & ~np.isnan(full))[0]
        keep = np.sort(rng.choice(cand, min(a.snps, len(cand)), replace=False))
        dos = full[keep].astype(float)
        for j, P in enumerate(grid):
            res = A.analyse(ctx, snp, ind, keep, dos, out=None, params=P, exclude=[iid], models=(j == 0 or a.quick))
            ranking = list(res['closest_modern'])
            rank = ranking.index(pop) + 1 if pop in ranking else 99
            top_reg = REGION.get(country.get(ranking[0], ''), '?')
            rows.append(dict(person=iid, population=pop, region=reg, **{k: P[k] for k in ('cap', 'k_regional', 'n_regional')},
                             own_rank=rank, top3=rank <= 3, top1_region_ok=(top_reg == reg) if reg != 'mixed' else None,
                             closest=', '.join(ranking[:5]), west=res['west_eurasian'],
                             modern_mix=json.dumps(res.get('mixture_modern', {})), deep=json.dumps(res.get('mixture_deep', {})),
                             historic=json.dumps(res.get('mixture_historic', {}))))
        print(f'  [{i + 1}/{len(picks)}] {pop} ({reg}): own rank {rows[-len(grid)]["own_rank"]} with default settings  ({(time.time() - t0) / 60:.0f} min)', flush=True)
        pd.DataFrame(rows).to_csv(out / 'ancestry_holdout.tsv', sep='\t', index=False)

    df = pd.DataFrame(rows)
    nm = df[df.region != 'mixed']
    by = nm.groupby(['cap', 'k_regional', 'n_regional']).agg(top3=('top3', 'mean'), median_rank=('own_rank', 'median'),
                                                           region_ok=('top1_region_ok', 'mean')).sort_values(['top3', 'median_rank'], ascending=[False, True])
    worst = nm.groupby(['cap', 'k_regional', 'n_regional', 'region']).top3.mean().unstack()
    d = df[(df.cap == A.DEFAULTS['cap']) & (df.k_regional == A.DEFAULTS['k_regional']) & (df.n_regional == A.DEFAULTS['n_regional'])]
    with open(out / 'ancestry_summary.md', 'w') as f:
        f.write(f'# Ancestry hold-out validation\n\n{len(picks)} public reference people held out, {a.snps:,} random SNPs each (chip-like overlap).\n\n')
        f.write('## Settings ranked (own population in top 3; median rank; top hit in the right region)\n\n' + '```\n' + by.round(3).to_string() + '\n```' + '\n\n')
        f.write('## Top-3 rate per region and setting\n\n' + '```\n' + worst.round(2).to_string() + '\n```' + '\n\n')
        f.write('## Mixture models with the default settings (check for invented components)\n\n' +
                '```\n' + d[['population', 'region', 'closest', 'modern_mix', 'deep', 'historic']].to_string(index=False) + '\n```' + '\n')
    print(by.round(3).to_string()); print('wrote', out / 'ancestry_summary.md')


if __name__ == '__main__':
    main()
