# Imputation (Beagle 5.5 against 1000 Genomes phase 3, GRCh37) plus the shared public panel files that the
# polygenic-score step needs. Shared files (data/panel, data/pgs/plink) depend only on public data; everything
# derived from the person goes to results/<name>/work/imputed.
import gzip, os, subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from ..util import run as sh, jdump, jload, java, progress
from ..refs import BEAGLE_JAR, UNBREF_JAR
from ..kb.pgs import SCORES

CHROMS = [str(c) for c in range(1, 23)]


def mem_gb():
    try: return os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_PHYS_PAGES') / 1e9
    except (ValueError, OSError, AttributeError): return 8


def prep_scores(data):
    """PGS Catalog harmonised files -> plink2 --score files keyed chr:pos:ref:alt (shared, public)."""
    pd_ = Path(data) / 'pgs'; out = pd_ / 'plink'; out.mkdir(parents=True, exist_ok=True)
    meta = jload(out / 'meta.json', {})
    for s in SCORES:
        pid = s['id']; f = pd_ / f'{pid}_hmPOS_GRCh37.txt.gz'
        if (out / f'{pid}.score').exists() and meta.get(pid, {}).get('v') == 2: continue
        m, w_ = {}, {}
        with gzip.open(f, 'rt') as fh:
            cols = None
            for l in fh:
                if l.startswith('#'):
                    if '=' in l: k, v = l[1:].rstrip('\n').split('=', 1); m[k] = v
                    continue
                if cols is None: cols = l.rstrip('\n').split('\t'); ix = {c: i for i, c in enumerate(cols)}; continue
                r = l.rstrip('\n').split('\t')
                ch = r[ix['hm_chr']] if 'hm_chr' in ix else ''; pos = r[ix['hm_pos']] if 'hm_pos' in ix else ''
                if not ch or not pos or ch not in CHROMS: continue
                ea = r[ix['effect_allele']].upper()
                oa = r[ix['other_allele']].upper() if 'other_allele' in ix and r[ix['other_allele']] else ''
                if not oa and 'hm_inferOtherAllele' in ix: oa = r[ix['hm_inferOtherAllele']].upper()
                if not oa or '/' in oa: continue
                # some files list a variant more than once (e.g. two rsIDs at one position): sum the weights
                # (a flipped duplicate counts negatively: a constant shift that leaves percentiles unchanged)
                a, b = sorted((oa, ea)); w = float(r[ix['effect_weight']])
                k = (ch, pos, a, b)
                w_[k] = w_.get(k, 0.0) + (w if ea == b else -w)
        with open(out / f'{pid}.score.tmp', 'w') as o:
            for (ch, pos, oa, ea), w in w_.items():
                # both allele orders; only the one present in the genotype files matches
                o.write(f'{ch}:{pos}:{oa}:{ea}\t{ea}\t{w:.6g}\n{ch}:{pos}:{ea}:{oa}\t{ea}\t{w:.6g}\n')
        os.replace(out / f'{pid}.score.tmp', out / f'{pid}.score')
        meta[pid] = dict(trait=m.get('trait_reported'), n=len(w_), v=2)
        jdump(meta, out / 'meta.json')
    ids = out / 'all_ids.txt'
    newest = max((out / f'{s["id"]}.score').stat().st_mtime for s in SCORES)
    if not ids.exists() or ids.stat().st_mtime < newest:
        allids = set()
        for s in SCORES:
            for l in open(out / f'{s["id"]}.score'): allids.add(l.split('\t', 1)[0])
        ids.write_text('\n'.join(sorted(allids)) + '\n')
    return ids


def panel_chrom(data, c, ids, threads):
    """Shared, public: site list for building the target, score-variant subset and a thinned common-SNP set for PCA."""
    d = Path(data); p = d / 'panel'; p.mkdir(exist_ok=True)
    sites, pgs_, pca = p / f'sites.chr{c}.tsv.gz', p / f'pgs.chr{c}', p / f'pca.chr{c}'
    if sites.exists() and Path(f'{pgs_}.pgen').exists() and Path(f'{pca}.pgen').exists(): return
    tmp = p / f'tmp.chr{c}.vcf.gz'
    with open(tmp, 'wb') as o:
        un = subprocess.Popen([java(), '-Xmx2g', '-jar', str(d / 'tools' / UNBREF_JAR), str(d / 'ref1kg' / f'chr{c}.1kg.phase3.v5a.b37.bref3')], stdout=subprocess.PIPE)
        bg = subprocess.run(['bgzip', '-l', '1', '-@', '3'], stdin=un.stdout, stdout=o); un.wait()
        if un.returncode or bg.returncode: raise RuntimeError(f'unbref3 failed for chr{c}')
    # site list with the panel allele frequency (used for target building and to tell rare from common variants)
    ft = subprocess.Popen(['bcftools', '+fill-tags', str(tmp), '-Ou', '--', '-t', 'AF'], stdout=subprocess.PIPE)
    q = subprocess.run(['bcftools', 'query', '-i', 'TYPE="snp" && N_ALT=1', '-f', '%POS\t%REF\t%ALT\t%AF\n', '-'], stdin=ft.stdout, capture_output=True); ft.wait()
    if q.returncode or ft.returncode: raise RuntimeError(f'bcftools failed for chr{c}')
    with gzip.open(f'{sites}.tmp', 'wb') as g: g.write(q.stdout)
    common = ['--vcf', tmp, '--max-alleles', '2', '--set-all-var-ids', '@:#:$r:$a', '--new-id-max-allele-len', '100', 'truncate',
              '--threads', threads, '--memory', '3000', '--silent']
    sh(['plink2'] + common + ['--extract', ids, '--make-pgen', '--out', pgs_])
    sh(['plink2'] + common + ['--snps-only', 'just-acgt', '--maf', '0.05', '--thin', '0.04', '--seed', '1', '--make-pgen', '--out', pca])
    os.replace(f'{sites}.tmp', sites); tmp.unlink()


def impute_chrom(ctx, c, G):
    """Personal: target VCF at panel sites (alleles checked against the panel), then Beagle."""
    d = ctx.data; out = ctx.work / 'imputed'
    if (out / f'me.chr{c}.vcf.gz.csi').exists(): return
    tgt = out / f'target.chr{c}.vcf'
    with open(tgt, 'w') as o:
        o.write(f'##fileformat=VCFv4.2\n##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">\n##contig=<ID={c}>\n'
                '#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tME\n')
        last = 0
        for l in gzip.open(d / 'panel' / f'sites.chr{c}.tsv.gz', 'rt'):
            p, ref, alt = l.split()[:3]; p = int(p)
            if p not in G or p == last: continue
            rs, g = G[p]; al = [ref, alt]
            if any(a not in al for a in g): continue  # strand or allele mismatch: leave it to imputation
            gt = '/'.join(str(al.index(a)) for a in g) if len(g) == 2 else str(al.index(g))
            o.write(f'{c}\t{p}\t{rs}\t{ref}\t{alt}\t.\tPASS\t.\tGT\t{gt}\n'); last = p
    sh(['bgzip', '-f', tgt])
    xmx = getattr(ctx, 'beagle_gb', 4)
    sh([java(), f'-Xmx{xmx}g', '-jar', d / 'tools' / BEAGLE_JAR, f'gt={tgt}.gz', f'ref={d / "ref1kg" / f"chr{c}.1kg.phase3.v5a.b37.bref3"}',
        f'map={d / "maps" / f"plink.chr{c}.GRCh37.map"}', f'out={out / f"me.chr{c}"}', 'impute=true', 'gp=true', f'nthreads={max(1, ctx.threads // 2)}'])
    sh(['bcftools', 'index', '-f', out / f'me.chr{c}.vcf.gz'])
    os.unlink(f'{tgt}.gz')


def run(ctx):
    progress('preparing the polygenic score files')
    ids = prep_scores(ctx.data)
    (ctx.work / 'imputed').mkdir(exist_ok=True)
    G = {c: {} for c in CHROMS}
    for l in open(ctx.genome):
        if l[0] == '#': continue
        rs, c, p, g = l.rstrip('\n').split('\t')
        if c in G and g != '--' and all(a in 'ACGT' for a in g): G[c][int(p)] = (rs, g)
    par = max(1, min(4, int(mem_gb() // 5), ctx.threads))  # unbref3 is single-threaded and I/O-bound: run several chromosomes at once
    ctx.beagle_gb = max(3, min(8, int(mem_gb() * 0.7 / par)))

    state = {'done': 0, 'active': set()}

    def show():
        act = ', '.join(sorted(state['active'], key=int))
        progress(f'{state["done"]} of 22 chromosomes done' + (f'; working on chromosome {act}' if act else ''))

    def one(c):
        state['active'].add(c); show()
        panel_chrom(ctx.data, c, ids, max(1, ctx.threads // par))
        impute_chrom(ctx, c, G[c])
        state['active'].discard(c); state['done'] += 1; show()
        return c
    with ThreadPoolExecutor(par) as ex:
        list(ex.map(one, CHROMS))
    n = 0
    for c in CHROMS:
        out = subprocess.run(['bcftools', 'index', '-n', str(ctx.work / 'imputed' / f'me.chr{c}.vcf.gz')], capture_output=True, text=True).stdout.strip()
        n += int(out or 0)
    return f'{n / 1e6:.1f} million variants'
