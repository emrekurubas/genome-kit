# Build a synthetic 23andMe-style raw file for a PUBLIC 1000 Genomes person, for end-to-end testing of genome-kit
# without anyone's private data. Uses the 1000 Genomes files the imputation tier downloads (data/ref1kg/*.bref3).
# Sites: ~600k common SNPs (like a consumer chip) plus every curated marker and PharmCAT position present in 1000 Genomes.
# Only autosomes (1000 Genomes chrX is not part of the download), so genetic sex comes out as "unknown".
#
# Usage: .tools/envs/core/bin/python tools/make_test_genome.py --sample HG00096 --data data --out input/test_HG00096.txt
import argparse, random, subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from genomekit.refs import UNBREF_JAR, PHARMCAT_VER
from genomekit.kb.markers import MARKERS


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--sample', default='HG00096'); ap.add_argument('--data', default='data'); ap.add_argument('--out', required=True)
    ap.add_argument('--every', type=int, default=12, help='keep 1 in N common SNPs (about 600k at 12)')
    a = ap.parse_args()
    d = Path(a.data); rnd = random.Random(1)
    must = {(m['chrom'], m['pos']) for m in MARKERS} | {(x['chrom'], x['pos']) for m in MARKERS for x in m.get('alt', [])}
    pc_ids = set()
    pcf = d / 'tools' / f'pharmcat_positions_{PHARMCAT_VER}.vcf'
    if pcf.exists():
        for l in open(pcf):
            if l[0] != '#': pc_ids |= set(l.split('\t')[2].split(';'))
    n = 0
    with open(a.out, 'w') as o:
        o.write(f'# Synthetic test file made by genome-kit from public 1000 Genomes sample {a.sample}. Not a real 23andMe file.\n')
        o.write('# rsid\tchromosome\tposition\tgenotype\n')
        for c in range(1, 23):
            un = subprocess.Popen(['java', '-jar', str(d / 'tools' / UNBREF_JAR), str(d / 'ref1kg' / f'chr{c}.1kg.phase3.v5a.b37.bref3')], stdout=subprocess.PIPE)
            q = subprocess.Popen(['bcftools', 'query', '-s', a.sample, '-i', 'TYPE="snp" && N_ALT=1', '-f', '%ID\t%POS\t%REF\t%ALT\t[%GT]\n', '-'],
                                 stdin=un.stdout, stdout=subprocess.PIPE, text=True)
            k = 0
            for l in q.stdout:
                rs, p, ref, alt, gt = l.rstrip('\n').split('\t')
                k += 1
                if (str(c), int(p)) not in must and rs not in pc_ids and k % a.every: continue
                al = [ref, alt]
                g = ''.join(al[int(x)] for x in gt.replace('|', '/').split('/') if x in '01')
                if len(g) != 2: continue
                if rnd.random() < 0.015: g = '--'  # chips miss ~1-2% of calls
                o.write(f'{rs if rs.startswith("rs") else f"i{c}_{p}"}\t{c}\t{p}\t{g}\n'); n += 1
            q.wait(); un.wait()
            print(f'chr{c}: {n:,} markers so far', flush=True)
    print('wrote', a.out)


if __name__ == '__main__':
    main()
