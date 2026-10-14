# Protein-changing (missense) variants scored with AlphaMissense (hg19) and REVEL v1.3, filtered to genes with
# well-supported disease links in ClinVar -> work/effects.json
import gzip, re, subprocess
from pathlib import Path
from ..util import jdump, progress

CHROMS = [str(c) for c in range(1, 23)]
NOTES = {
    ('HABP2', 'G534E'): 'Known as “Marburg I”. About 2–3 in 100 Europeans carry it; studies disagree on whether it matters, so it needs no action.',
    ('SLC45A2', 'L374F'): 'One of the main skin-colour genes; this version makes skin lighter and is the usual one in Europe.',
    ('ABCC11', 'G180R'): 'The earwax gene: two copies give dry earwax (common in East Asia).',
    ('TPMT', 'A154T'): 'Part of the TPMT*3A type; see the medicines section.',
    ('AMPD1', 'P81L'): 'A common, usually harmless change in a muscle-energy enzyme.',
    ('ACADS', 'G209S'): 'A common change that slows a fat-processing enzyme a little; considered harmless.',
}


def candidates(ctx):
    """Non-reference SNPs: chip calls, plus imputed sites with dosage >= 0.5 when imputation was run."""
    me = {}
    imp = ctx.work / 'imputed'
    if (imp / 'me.chr22.vcf.gz').exists():
        for c in CHROMS:
            v = subprocess.run(['bcftools', 'view', '-M2', '-v', 'snps', '-i', 'FORMAT/DS>=0.5', str(imp / f'me.chr{c}.vcf.gz'), '-Ou'], capture_output=True).stdout
            q = subprocess.run(['bcftools', 'query', '-f', '%CHROM\t%POS\t%REF\t%ALT\t[%DS]\n'], input=v, capture_output=True).stdout.decode()
            for l in q.splitlines():
                ch, p, r, a, ds = l.split('\t'); me[(ch, int(p), r, a)] = dict(ds=float(ds), source='imputed')
    chip = {}
    for l in open(ctx.genome):
        if l[0] == '#': continue
        rs, c, p, g = l.rstrip('\n').split('\t')
        if c in CHROMS and len(g) == 2 and g != '--' and set(g) <= set('ACGT'): chip[(c, int(p))] = (rs, g)
    return me, chip


def run(ctx):
    V = ctx.data / 'vep'
    progress('collecting your protein-changing variants')
    me, chip = candidates(ctx)
    progress('scoring with AlphaMissense (reads a 600 MB table)')
    am = {}
    proc = subprocess.Popen(['gzip', '-dc', str(V / 'AlphaMissense_hg19.tsv.gz')], stdout=subprocess.PIPE, text=True, bufsize=1 << 20)
    for l in proc.stdout:
        if l[0] == '#': continue
        f = l.split('\t')
        c, p, r, a = f[0][3:], int(f[1]), f[2], f[3]
        k = (c, p, r, a)
        g = chip.get((c, p))
        n = None
        if g and set(g[1]) <= {r, a}:  # the chip measured this position: its call wins
            n = g[1].count(a)
            if n == 0: continue
            src = 'measured'
        elif k in me:
            n = round(me[k]['ds']); src = 'estimated'
            if abs(me[k]['ds'] - n) >= 0.1 or n == 0: continue  # uncertain imputation
        else:
            continue
        s = float(f[8])
        if k not in am or s > am[k]['am']:
            am[k] = dict(uniprot=f[5], protein_change=f[7], am=s, am_class=f[9].strip(), copies=n, source=src)
    proc.wait()
    progress('scoring with REVEL')
    rv = {}
    proc = subprocess.Popen(['unzip', '-p', str(V / 'revel-v1.3_all_chromosomes.zip')], stdout=subprocess.PIPE, text=True, bufsize=1 << 20)
    next(proc.stdout)
    for l in proc.stdout:
        f = l.split(',')
        if f[1] == '.': continue
        k = (f[0], int(f[1]), f[3], f[4])
        if k in am: rv[k] = max(float(f[7]), rv.get(k, 0))
    proc.wait()
    uni = {}
    import csv
    for r in csv.DictReader(open(V / 'hgnc_complete_set.txt'), delimiter='\t'):
        for u in (r.get('uniprot_ids') or '').split('|'):
            if u: uni.setdefault(u, r['symbol'])
    # genes with well-supported disease variants (ClinVar, >= 2 review stars)
    disease = set()
    with gzip.open(ctx.data / 'clinvar' / 'clinvar.vcf.gz', 'rt') as f:
        for line in f:
            if line[0] == '#': continue
            info = line.split('\t', 8)[7]
            if 'CLNSIG=Pathogenic' not in info and 'CLNSIG=Likely_pathogenic' not in info: continue
            if 'multiple_submitters' not in info and 'expert_panel' not in info and 'practice_guideline' not in info: continue
            m = re.search(r'GENEINFO=([^:;]+)', info)
            if m: disease.add(m.group(1))
    # population frequency from the shared 1000 Genomes site lists (when available)
    af = {}
    for c in CHROMS:
        sf = ctx.data / 'panel' / f'sites.chr{c}.tsv.gz'
        if not sf.exists(): continue
        want = {k[1]: k for k in am if k[0] == c}
        for l in gzip.open(sf, 'rt'):
            f = l.rstrip('\n').split('\t')
            if len(f) < 4: break
            k = want.get(int(f[0]))
            if k and f[1] == k[2] and f[2] == k[3]: af[k] = float(f[3])
    rows = []
    for k, a in am.items():
        gene = uni.get(a['uniprot'], '')
        rev = rv.get(k)
        dmg = (a['am_class'] == 'pathogenic' and (rev or 0) >= 0.5) or (rev or 0) >= 0.75
        freq = af.get(k)
        rows.append(dict(chrom=k[0], pos=k[1], ref=k[2], alt=k[3], gene=gene, protein_change=a['protein_change'], am=a['am'], revel=rev,
                         copies=a['copies'], source=a['source'], af=freq, damaging=dmg, disease_gene=gene in disease))
    notable = [r for r in rows if r['damaging'] and r['disease_gene'] and (r['af'] is None or r['af'] < 0.01)]
    notable.sort(key=lambda r: -r['am'])
    for r in notable:
        r['copies_text'] = f'{"two copies" if r["copies"] == 2 else "one copy"}, {r["source"]}'
        r['note'] = NOTES.get((r['gene'], r['protein_change']), 'Rare and predicted damaging. Confirm clinically before drawing conclusions.' if r['source'] == 'measured'
                              else 'Estimated, not measured: imputation is unreliable for rare variants.')
        r['revel'] = round(r['revel'], 2) if r['revel'] is not None else None
    meas = [r for r in notable if r['source'] == 'measured']
    summ = (f'{len(notable)} rare variant{"s" if len(notable) != 1 else ""} predicted damaging in genes with known disease links '
            f'({len(meas)} measured directly by the chip). ' +
            ('Everyone carries a few of these; most have no effect, and many recessive-disease genes only matter with two broken copies.' if notable else 'Nothing worrying was found.'))
    jdump(dict(n_missense=len(rows), n_damaging=sum(r['damaging'] for r in rows), notable=notable[:40], summary=summ), ctx.work / 'effects.json')
    return f'{len(rows):,} missense variants, {len(notable)} notable'
