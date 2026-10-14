# Read consumer DNA raw files (23andMe, AncestryDNA, MyHeritage, FamilyTreeDNA, LivingDNA) and write one
# normalised table: rsid <tab> chrom <tab> pos <tab> genotype, GRCh37, plus strand, '--' = no call.
import csv, gzip, io, re, zipfile
from pathlib import Path

CHROM = {str(i): str(i) for i in range(1, 23)}
CHROM.update({'X': 'X', 'Y': 'Y', 'MT': 'MT', 'M': 'MT', '23': 'X', '24': 'Y', '25': 'X', '26': 'MT', 'XY': 'X'})
# GRCh37 positions of a few common SNPs, used to confirm the genome build
BUILD_CHECK = {'rs4988235': ('2', 136608646, 135851076), 'rs1801133': ('1', 11856378, 11796321),
               'rs429358': ('19', 45411941, 44908684), 'rs12913832': ('15', 28365618, 28120472),
               'rs9939609': ('16', 53820527, 53786615), 'rs762551': ('15', 75041917, 74749576)}


def _open_text(path):
    path = Path(path)
    if path.suffix.lower() == '.zip':
        z = zipfile.ZipFile(path)
        names = [n for n in z.namelist() if not n.endswith('/') and not n.startswith('__MACOSX') and n.lower().endswith(('.txt', '.csv', '.tsv'))]
        if not names: raise ValueError('the zip file contains no .txt/.csv file')
        return io.TextIOWrapper(z.open(max(names, key=lambda n: z.getinfo(n).file_size)), encoding='utf-8', errors='replace')
    if path.suffix.lower() == '.gz':
        return gzip.open(path, 'rt', encoding='utf-8', errors='replace')
    return open(path, encoding='utf-8', errors='replace')


def detect(path):
    with _open_text(path) as f:
        head = [next(f, '') for _ in range(60)]
    text = ''.join(head).lower()
    if '23andme' in text: return '23andme'
    if 'ancestrydna' in text or re.search(r'^rsid\tchromosome\tposition\tallele1\tallele2', text, re.M): return 'ancestry'
    if 'livingdna' in text or 'living dna' in text: return '23andme'
    if re.search(r'^"?rsid"?,"?chromosome"?,"?position"?,"?result"?', text, re.M): return 'csv'
    if 'myheritage' in text or 'familytreedna' in text: return 'csv'
    # fall back on the shape of the first data line
    for l in head:
        if l.startswith('#') or not l.strip(): continue
        n_tab, n_comma = l.count('\t'), l.count(',')
        if n_tab == 3: return '23andme'
        if n_tab == 4: return 'ancestry'
        if n_comma == 3: return 'csv'
    raise ValueError('unrecognised file format')


def parse(path):
    """Yield (rsid, chrom, pos, genotype) in the normalised form."""
    fmt = detect(path)
    with _open_text(path) as f:
        rows = csv.reader(f) if fmt == 'csv' else (l.rstrip('\r\n').split('\t') for l in f)
        for r in rows:
            if not r or not r[0] or r[0].startswith('#'): continue
            r = [x.strip().strip('"') for x in r]
            if r[0].lower() in ('rsid', 'snp'): continue
            try:
                if fmt == 'ancestry': rs, c, p, g = r[0], r[1], r[2], r[3] + r[4]
                else: rs, c, p, g = r[0], r[1], r[2], r[3]
            except IndexError:
                continue
            c = CHROM.get(c.upper().replace('CHR', ''))
            if c is None or not p.isdigit(): continue
            g = g.upper().replace('0', '-')
            if not g or '-' in g or g in ('NC', '??'): g = '--'
            elif not all(a in 'ACGTDI' for a in g): g = '--'
            yield rs, c, int(p), g


def normalise(src, dest):
    """Write the normalised table; return summary stats (format, counts, build check)."""
    fmt = detect(src)
    seen, n, called, by_chr = set(), 0, 0, {}
    pos = {}
    with open(dest, 'w') as o:
        o.write('# rsid\tchromosome\tposition\tgenotype  (normalised by genome-kit; GRCh37, plus strand)\n')
        for rs, c, p, g in parse(src):
            if (c, p, rs) in seen: continue
            seen.add((c, p, rs))
            # haploid calls on X/Y/MT are written as one letter, like 23andMe
            if c in ('Y', 'MT') and len(g) == 2 and g[0] == g[1] and g != '--': g = g[0]
            o.write(f'{rs}\t{c}\t{p}\t{g}\n'); n += 1
            if g != '--': called += 1; by_chr[c] = by_chr.get(c, 0) + 1
            if rs in BUILD_CHECK: pos[rs] = (c, p)
    hits37 = sum(1 for k, (c, p) in pos.items() if BUILD_CHECK[k][0] == c and BUILD_CHECK[k][1] == p)
    hits38 = sum(1 for k, (c, p) in pos.items() if BUILD_CHECK[k][0] == c and BUILD_CHECK[k][2] == p)
    build = 'GRCh37' if hits37 >= hits38 and hits37 > 0 else ('GRCh38' if hits38 > hits37 else 'unknown')
    return dict(format=fmt, markers=n, called=called, call_rate=called / max(n, 1), by_chrom=by_chr, build=build)


def guess_name(path):
    """23andMe-style file names carry the person's name, e.g. genome_Jane_Doe_v5_Full_2024....txt."""
    m = re.match(r'genome_(.+?)_v\d+_Full', Path(path).name)
    return m.group(1).replace('_', ' ') if m else ''


def infer_sex(genome_txt):
    """Male if most chrY markers are called and chrX is (nearly) never heterozygous."""
    y_tot = y_call = x_tot = x_het = 0
    for l in open(genome_txt):
        if l[0] == '#': continue
        _, c, _, g = l.rstrip('\n').split('\t')
        if c == 'Y':
            y_tot += 1; y_call += g != '--'
        elif c == 'X' and g != '--' and 'D' not in g and 'I' not in g:
            p = int(l.split('\t')[2])
            if p <= 2699520 or p >= 154931044: continue  # pseudo-autosomal regions are diploid in men too
            x_tot += 1; x_het += len(g) == 2 and g[0] != g[1]
    y_rate = y_call / y_tot if y_tot else None
    x_het_rate = x_het / x_tot if x_tot else None
    if y_rate is not None and y_rate > 0.5 and (x_het_rate is None or x_het_rate < 0.02): sex = 'male'
    elif (y_rate is None or y_rate < 0.1) and (x_het_rate or 0) > 0.05: sex = 'female'
    elif y_rate is None and x_het_rate is not None: sex = 'male' if x_het_rate < 0.02 else 'female'
    else: sex = 'unknown'
    return sex, dict(y_call_rate=y_rate, x_het_rate=x_het_rate)
