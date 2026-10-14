# Core analyses that need only the raw chip data: QC + runs of homozygosity, ClinVar screen,
# PharmCAT medicine genes, mitochondrial and Y haplogroups.
import csv, gzip, re
from pathlib import Path
from ..util import run, capture, jdump, jload, java, say, progress
from ..refs import PHARMCAT_VER

KB = Path(__file__).resolve().parent.parent / 'kb'


# ------------------------------------------------------------------ QC, sex check, runs of homozygosity
def qc(ctx):
    w = ctx.work / 'plink'; w.mkdir(exist_ok=True)
    s = jload(ctx.work / 'sample.json')
    sexflag = {'male': 'M', 'female': 'F'}.get(s['sex'], '0')
    run(['plink', '--23file', ctx.genome, 'me', 'me', sexflag, '--allow-no-sex', '--make-bed', '--out', w / 'me', '--silent'])
    run(['plink', '--bfile', w / 'me', '--chr', '1-22', '--homozyg', '--homozyg-density', 50, '--homozyg-kb', 1000,
         '--homozyg-snp', 100, '--homozyg-window-het', 1, '--allow-no-sex', '--out', w / 'roh', '--silent'])
    segs = []
    for r in csv.DictReader(open(w / 'roh.hom'), delimiter=' ', skipinitialspace=True):
        segs.append(dict(chrom=r['CHR'], start=int(r['POS1']), end=int(r['POS2']), kb=float(r['KB'])))
    tot = sum(x['kb'] for x in segs) / 1000; longest = max([x['kb'] for x in segs], default=0) / 1000
    # Interpretation (chip ROH >= 1 Mb): long runs (> 10 Mb) or a large total (> 70 Mb) suggest related parents.
    if longest >= 20 or tot >= 150: verdict = 'close'       # e.g. first cousins or closer
    elif longest >= 10 or tot >= 70: verdict = 'distant'    # e.g. second cousins, or a small endogamous community
    else: verdict = 'none'
    roh = dict(n=len(segs), total_mb=round(tot, 1), longest_mb=round(longest, 1), verdict=verdict)
    s['roh'] = roh; jdump(s, ctx.work / 'sample.json')
    return f'{len(segs)} homozygous segments, {tot:.0f} Mb total, longest {longest:.1f} Mb'


# ------------------------------------------------------------------ ClinVar
PATHO = re.compile(r'(^|[|/,_])(Pathogenic|Likely_pathogenic)', re.I)


def clinvar(ctx):
    G = {}
    for l in open(ctx.genome):
        if l[0] == '#': continue
        rs, c, p, g = l.rstrip('\n').split('\t')
        if g != '--': G[(c, int(p))] = (rs, g)
    from ..kb.markers import MARKERS
    known = {(m['chrom'], m['pos']) for m in MARKERS}
    hits = []
    progress('checking your variants against 2.5 million ClinVar entries')
    with gzip.open(ctx.data / 'clinvar' / 'clinvar.vcf.gz', 'rt') as f:
        for line in f:
            if line[0] == '#': continue
            c, p, vid, ref, alt, _, _, info = line.rstrip('\n').split('\t')[:8]
            k = (c, int(p))
            if k not in G: continue
            d = dict(x.split('=', 1) for x in info.split(';') if '=' in x)
            sig = d.get('CLNSIG', '')
            if not PATHO.search(sig) or 'Conflicting' in sig: continue
            rs, gt = G[k]
            if len(ref) == 1 and len(alt) == 1:
                if any(a in 'DI' for a in gt) or any(a not in (ref, alt) for a in gt): continue
                n = gt.count(alt)
            else:
                continue  # indels: chip I/D probes cannot be matched to ClinVar alleles reliably
            if n == 0: continue
            rev = d.get('CLNREVSTAT', '')
            stars = 0 if 'no_assertion' in rev or 'no_classification' in rev else 1 if 'single_submitter' in rev or 'conflicting' in rev else 2 if 'multiple_submitters' in rev else 3 if 'expert_panel' in rev else 4 if 'practice_guideline' in rev else 1
            af = max([float(d[x]) for x in ('AF_EXAC', 'AF_ESP', 'AF_TGP') if x in d and d[x] not in ('', '.')] or [0])
            hits.append(dict(rsid=rs, chrom=c, pos=int(p), ref=ref, alt=alt, genotype=gt, copies=n, gene=d.get('GENEINFO', '').split(':')[0],
                             condition=d.get('CLNDN', '').replace('_', ' ').split('|')[0], significance=sig.replace('_', ' '),
                             stars=stars, af=af, clinvar_id=vid, known_marker=k in known))
    # Keep real candidates: not a curated marker (reported separately), not common (common "pathogenic" labels are usually
    # mild risk factors), and with at least one review star.
    keep = [h for h in hits if not h['known_marker'] and h['af'] < 0.02 and h['stars'] >= 1 and h['condition'] not in ('not provided', 'not specified')]
    for h in keep: h['likely_artifact'] = h['af'] < 0.001
    jdump(dict(all=hits, report=keep), ctx.work / 'clinvar.json')
    return f'{len(keep)} variant(s) to report ({len(hits)} ClinVar pathogenic matches before filtering)'


# ------------------------------------------------------------------ PharmCAT
def pharmcat(ctx):
    G, pos = {}, {}
    for l in open(ctx.genome):
        if l[0] == '#': continue
        rs, c, p, g = l.rstrip('\n').split('\t')
        if g == '--': continue
        G[rs] = g; pos[(c, p)] = rs
    # chips use internal IDs for some sites (23andMe "i" IDs): map them to rsIDs through ClinVar positions
    alias = {}
    with gzip.open(ctx.data / 'clinvar' / 'clinvar.vcf.gz', 'rt') as f:
        for line in f:
            if line[0] == '#': continue
            c, p, _, _, _, _, _, info = line.split('\t')[:8]
            k = (c, p)
            if k in pos and not pos[k].startswith('rs') and 'RS=' in info:
                alias.setdefault('rs' + info.split('RS=')[1].split(';')[0], G[pos[k]])
    for r, g in alias.items(): G.setdefault(r, g)
    out, used = [], 0
    for line in open(ctx.data / 'tools' / f'pharmcat_positions_{PHARMCAT_VER}.vcf'):
        if line.startswith('##'): out.append(line); continue
        if line.startswith('#'): out.append(line.replace('PharmCAT', 'SAMPLE')); continue
        f = line.rstrip('\n').split('\t')
        ids = f[2].split(';'); ref = f[3]; alts = f[4].split(',')
        gt = next((G[i] for i in ids if i in G), None)
        if gt is None: continue
        if any(a in 'DI' for a in gt):
            # 23andMe I/D probes: a homozygous non-variant call (II at deletions, DD at insertions) means reference
            isdel = len(ref) > len(alts[0])
            if len(alts) == 1 and ((isdel and gt in ('II', 'I')) or (not isdel and gt in ('DD', 'D'))):
                f[9] = '0/0'; out.append('\t'.join(f) + '\n'); used += 1
            continue
        if len(ref) != 1 or any(len(a) != 1 for a in alts): continue
        alleles = [ref] + alts
        if any(a not in alleles for a in gt): continue
        idx = [str(alleles.index(a)) for a in gt]
        if len(idx) == 1: idx = idx * 2
        f[9] = '/'.join(idx); out.append('\t'.join(f) + '\n'); used += 1
    pc = ctx.work / 'pharmcat'; pc.mkdir(exist_ok=True)
    open(pc / 'input.vcf', 'w').writelines(out)
    cmd = [java(), '-jar', ctx.data / 'tools' / f'pharmcat-{PHARMCAT_VER}-all.jar', '-vcf', pc / 'input.vcf', '-o', pc,
           '-reporterJson', '-reporterCallsOnlyTsv']
    hla = jload(ctx.work / 'hla.json', {})
    if hla.get('A') and hla.get('B'):
        with open(pc / 'outside.tsv', 'w') as o:
            for loc in ('A', 'B'): o.write(f'HLA-{loc}\t*{hla[loc]["allele1"]}/*{hla[loc]["allele2"]}\n')
        cmd += ['-po', pc / 'outside.tsv']
    run(cmd, cwd=pc)  # PharmCAT writes pharmcat.log into its working directory
    return f'{used} medicine-gene positions read'


# ------------------------------------------------------------------ mtDNA haplogroup (Haplogrep 3)
def mtdna(ctx):
    ref = ''.join(l.strip() for l in open(KB / 'rCRS.txt') if not l.startswith('>'))
    rng, pol = [], []
    for l in open(ctx.genome):
        if l[0] == '#': continue
        rs, c, p, g = l.rstrip('\n').split('\t')
        if c != 'MT' or g in ('--', '') or len(set(g)) != 1 or g[0] not in 'ACGT': continue
        p = int(p); rng.append(str(p))
        if ref[p - 1] != g[0]: pol.append(f'{p}{g[0]}')
    if len(rng) < 50:
        jdump(dict(haplogroup=None, reason='too few mitochondrial markers on this chip'), ctx.work / 'mtdna.json'); return 'skipped: too few MT markers'
    d = ctx.work / 'mtdna'; d.mkdir(exist_ok=True)
    pol = sorted(set(pol), key=lambda x: int(x[:-1]))
    open(d / 'me.hsd', 'w').write('ID\tRange\tHaplogroup\tPolymorphisms\nme\t' + ';'.join(rng) + '\t?\t' + '\t'.join(pol) + '\n')
    hg = ctx.data / 'tools' / 'haplogrep3'
    for tree in ('phylotree-rcrs@17.2', 'phylotree-rcrs@17.0'):
        try:
            run([java(), '-jar', hg / 'haplogrep3.jar', 'classify', '--input', d / 'me.hsd', '--output', d / 'haplogrep.txt',
                 '--tree', tree, '--extend-report'], cwd=hg)
            break
        except RuntimeError:
            continue
    rows = list(csv.DictReader(open(d / 'haplogrep.txt'), delimiter='\t'))
    r = rows[0]
    out = dict(haplogroup=r['Haplogroup'].strip('"'), quality=float(r['Quality'].strip('"')), n_positions=len(rng), n_variants=len(pol))
    jdump(out, ctx.work / 'mtdna.json')
    return f'{out["haplogroup"]} (quality {out["quality"]:.2f})'


# ------------------------------------------------------------------ Y haplogroup (yhaplo)
def ydna(ctx):
    s = jload(ctx.work / 'sample.json')
    if s['sex'] != 'male':
        jdump(dict(haplogroup=None, reason='no Y chromosome'), ctx.work / 'ydna.json'); return 'skipped (no Y chromosome)'
    pos, gen = [], []
    for l in open(ctx.genome):
        if l[0] == '#': continue
        rs, c, p, g = l.rstrip('\n').split('\t')
        if c != 'Y' or g == '--' or len(set(g)) != 1 or g[0] not in 'ACGT': continue
        pos.append(p); gen.append(g[0])
    d = ctx.work / 'ydna'; d.mkdir(exist_ok=True)
    open(d / 'me.genos.txt', 'w').write('ID\t' + '\t'.join(pos) + '\nme\t' + '\t'.join(gen) + '\n')
    run(['yhaplo', '-i', d / 'me.genos.txt', '-o', d, '-hp'])
    line = open(d / 'haplogroups.me.txt').read().split()
    out = dict(haplogroup=line[2], haplogroup_long=line[3] if len(line) > 3 else '', n_markers=len(pos))
    jdump(out, ctx.work / 'ydna.json')
    return f'{out["haplogroup"]} ({out["haplogroup_long"]})'
