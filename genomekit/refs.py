# Public reference data and tools: what each tier needs, where it comes from, and how to fetch it.
# Everything here is public and identical for every user; nothing personal is ever stored under data/.
import gzip, os, shutil, subprocess
from pathlib import Path
from .util import download, unpack, say, run, java

PHARMCAT_VER = '3.4.0'
HAPLOGREP_VER = '3.3.2'
BEAGLE_JAR = 'beagle.03Oct25.f35702.jar'
UNBREF_JAR = 'unbref3.27Feb25.75f.jar'

URL = dict(
    clinvar='https://ftp.ncbi.nlm.nih.gov/pub/clinvar/vcf_GRCh37/clinvar.vcf.gz',
    pharmcat=f'https://github.com/PharmGKB/PharmCAT/releases/download/v{PHARMCAT_VER}/pharmcat-{PHARMCAT_VER}-all.jar',
    pharmcat_pos=f'https://github.com/PharmGKB/PharmCAT/releases/download/v{PHARMCAT_VER}/pharmcat_positions_{PHARMCAT_VER}.vcf',
    haplogrep=f'https://github.com/genepi/haplogrep3/releases/download/v{HAPLOGREP_VER}/haplogrep3-{HAPLOGREP_VER}-linux.tar.gz',
    beagle=f'https://faculty.washington.edu/browning/beagle/{BEAGLE_JAR}',
    unbref=f'https://faculty.washington.edu/browning/beagle/{UNBREF_JAR}',
    bref3='https://bochet.gcc.biostat.washington.edu/beagle/1000_Genomes_phase3_v5a/b37.bref3/chr{c}.1kg.phase3.v5a.b37.bref3',
    maps='https://bochet.gcc.biostat.washington.edu/beagle/genetic_maps/plink.GRCh37.map.zip',
    kg_panel='https://bochet.gcc.biostat.washington.edu/beagle/1000_Genomes_phase3_v5a/sample_info/integrated_call_samples_v3.20130502.ALL.panel',
    pgs='https://ftp.ebi.ac.uk/pub/databases/spot/pgs/scores/{id}/ScoringFiles/Harmonized/{id}_hmPOS_GRCh37.txt.gz',
    hibag_eur='https://hibag.s3.amazonaws.com/download/hlares_param/European-HLA4-hg19.RData',
    aadr='https://dataverse.harvard.edu/api/access/datafile/{fid}',
    alphamissense='https://storage.googleapis.com/dm_alphamissense/AlphaMissense_hg19.tsv.gz',
    revel='https://zenodo.org/records/7072866/files/revel-v1.3_all_chromosomes.zip',
    hgnc='https://storage.googleapis.com/public-download-files/hgnc/tsv/tsv/hgnc_complete_set.txt',
)
AADR_FILES = {'geno': 13994522, 'ind': 13994523, 'snp': 13994524, 'anno': 13994525}  # AADR v66 compatibility_HO

# Approximate download sizes (GB) and run times, shown in the wizard before anything starts.
TIERS = {
    'core': dict(title='Health, medicines, traits and family lines', gb=0.25, time='10–20 minutes',
                 desc='Medicine-gene check (PharmCAT), known disease variants (ClinVar), curated health and trait markers, '
                      'mother-line and father-line haplogroups, parental-relatedness check.'),
    'impute': dict(title='Imputation, polygenic scores and HLA typing', gb=8.5, time='2–6 hours',
                   desc='Fills in ~30 million untested DNA positions from 1000 Genomes, then computes ~45 polygenic risk scores '
                        '(ancestry-adjusted percentiles) and types the immune HLA genes (better medicine checks for carbamazepine, abacavir, allopurinol).'),
    'ancient': dict(title='Ancient-DNA ancestry', gb=1.9, time='20–60 minutes',
                    desc='Places you among ~2,000 modern and ~400 ancient genomes (Allen Ancient DNA Resource): closest populations, '
                         'deep-time and historic-era mixture models. Uses the imputation tier when it is also selected.'),
    'effects': dict(title='Variant effect predictions', gb=1.6, time='15–30 minutes',
                    desc='Scores every protein-changing variant you carry with AlphaMissense and REVEL and lists any likely-damaging ones '
                         'in genes with known disease links.'),
}
TIER_ORDER = ['core', 'impute', 'ancient', 'effects']
ENV_GB = 1.2  # the tool environment itself (first run)


def ensure_core(data):
    d = Path(data)
    download(URL['clinvar'], d / 'clinvar' / 'clinvar.vcf.gz', 'ClinVar (GRCh37)', min_bytes=50_000_000)
    download(URL['pharmcat'], d / 'tools' / f'pharmcat-{PHARMCAT_VER}-all.jar', 'PharmCAT')
    download(URL['pharmcat_pos'], d / 'tools' / f'pharmcat_positions_{PHARMCAT_VER}.vcf', 'PharmCAT positions')
    hg = d / 'tools' / 'haplogrep3'
    if not (hg / 'haplogrep3.jar').exists():
        tgz = download(URL['haplogrep'], d / 'tools' / f'haplogrep3-{HAPLOGREP_VER}-linux.tar.gz', 'Haplogrep 3')
        unpack(tgz, hg); tgz.unlink()


def ensure_impute(data, threads):
    d = Path(data)
    t = d / 'tools'
    download(URL['beagle'], t / BEAGLE_JAR, 'Beagle 5.5')
    download(URL['unbref'], t / UNBREF_JAR, 'unbref3')
    m = d / 'maps'
    if not (m / 'plink.chr22.GRCh37.map').exists():
        z = download(URL['maps'], d / 'maps.zip', 'genetic maps'); unpack(z, m); z.unlink()
    download(URL['kg_panel'], d / 'ref1kg' / 'integrated_call_samples_v3.20130502.ALL.panel', '1000 Genomes sample list')
    for c in range(1, 23):
        download(URL['bref3'].format(c=c), d / 'ref1kg' / f'chr{c}.1kg.phase3.v5a.b37.bref3', f'1000 Genomes chr{c}', min_bytes=10_000_000)
    download(URL['hibag_eur'], d / 'hla' / 'European-HLA4-hg19.RData', 'HIBAG HLA model')
    from .kb.pgs import SCORES
    for s in SCORES:
        download(URL['pgs'].format(id=s['id']), d / 'pgs' / f'{s["id"]}_hmPOS_GRCh37.txt.gz', f'score {s["id"]}')


def ensure_ancient(data):
    d = Path(data) / 'aadr'
    for k, fid in AADR_FILES.items():
        download(URL['aadr'].format(fid=fid), d / f'v66_HO.{k}', f'AADR v66 .{k}', min_bytes=10_000)


def ensure_effects(data):
    d = Path(data) / 'vep'
    download(URL['alphamissense'], d / 'AlphaMissense_hg19.tsv.gz', 'AlphaMissense', min_bytes=100_000_000)
    download(URL['revel'], d / 'revel-v1.3_all_chromosomes.zip', 'REVEL', min_bytes=100_000_000)
    download(URL['hgnc'], d / 'hgnc_complete_set.txt', 'HGNC gene table')
