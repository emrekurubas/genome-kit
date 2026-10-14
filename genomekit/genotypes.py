# Genotype access for one person: chip calls (by position or rsID), with imputed dosages as a fallback.
import gzip, os, subprocess
from pathlib import Path


class Genome:
    def __init__(self, genome_txt, imputed_dir=None, sex='unknown'):
        self.by_pos, self.by_rs = {}, {}
        for l in open(genome_txt):
            if l[0] == '#': continue
            rs, c, p, g = l.rstrip('\n').split('\t')
            self.by_pos[(c, int(p))] = (rs, g)
            self.by_rs[rs] = (c, int(p), g)
        self.imputed_dir = Path(imputed_dir) if imputed_dir else None
        self.sex = sex

    def chip(self, chrom=None, pos=None, rsid=None):
        if chrom and pos and (chrom, pos) in self.by_pos:
            g = self.by_pos[(chrom, pos)][1]
            if g != '--': return g
        if rsid and rsid in self.by_rs:
            g = self.by_rs[rsid][2]
            if g != '--': return g
        return None

    def imputed(self, chrom, pos, effect):
        """Effect-allele dosage from the imputed VCF (autosomes only), or None."""
        if not self.imputed_dir or chrom not in [str(i) for i in range(1, 23)]: return None
        f = self.imputed_dir / f'me.chr{chrom}.vcf.gz'
        if not f.exists(): return None
        out = subprocess.run(['bcftools', 'query', '-r', f'{chrom}:{pos}', '-f', '%POS\t%REF\t%ALT\t[%DS]\n', str(f)],
                             capture_output=True, text=True).stdout
        for l in out.splitlines():
            p, ref, alt, ds = l.split('\t')
            if int(p) != pos or ',' in alt or len(ref) != 1 or len(alt) != 1: continue
            ds = float(ds)
            if alt in effect: return ds
            if ref in effect: return 2 - ds
        return None

    def count(self, m):
        """Copies of the effect allele: dict(n, source, genotype, certain) or None if unknown.
        Chip calls win; imputed dosages are used only when confidently near 0, 1 or 2."""
        eff = m['effect']
        for site in [m] + m.get('alt', []):
            g = self.chip(site['chrom'], site['pos'], site['rsid'])
            if g is None: continue
            e = site.get('effect', eff)
            if set(g) <= set('DI'):
                if e not in 'DI': continue
                n = g.count(e)
            else:
                n = sum(a in e for a in g)
                if len(g) == 1 and site['chrom'] == 'X' and self.sex == 'male': pass  # hemizygous: 0 or 1
            return dict(n=n, source='chip', genotype=g, certain=True, rsid=site['rsid'])
        for site in [m] + m.get('alt', []):
            ds = self.imputed(site['chrom'], site['pos'], site.get('effect', eff))
            if ds is None: continue
            n = round(ds)
            return dict(n=n, source='imputed', genotype=f'dosage {ds:.2f}', certain=abs(ds - n) < 0.1, rsid=site['rsid'])
        return None
