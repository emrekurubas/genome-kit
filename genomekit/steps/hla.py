# HLA typing (HIBAG) from the imputed MHC region -> work/hla.json.
# R and HIBAG live in their own small environment (.tools/envs/r), created on first use.
import csv, os, platform, subprocess
from pathlib import Path
from ..util import run as sh, jdump, say, progress

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent


TOOLS = Path(os.environ.get('GENOMEKIT_TOOLS') or REPO / '.tools')


def r_env():
    env = TOOLS / 'envs' / 'r'
    rs = env / 'bin' / 'Rscript'
    if rs.exists(): return rs
    mm = os.environ.get('GENOMEKIT_MAMBA') or str(TOOLS / 'bin' / 'micromamba')
    cmd = [mm, 'create', '-y', '-q', '-p', env, '-c', 'conda-forge', '-c', 'bioconda', 'r-base=4.5', 'bioconductor-hibag']
    # bioconda has no Apple-Silicon build of HIBAG; the Intel build runs fine under Rosetta 2
    if platform.system() == 'Darwin' and platform.machine() == 'arm64': cmd += ['--platform', 'osx-64']
    progress('one-time setup of R and HIBAG (about 300 MB)')
    sh(cmd, env=dict(os.environ, MAMBA_ROOT_PREFIX=str(TOOLS / 'mamba')))
    sh([mm, 'clean', '-a', '-y', '-q'], env=dict(os.environ, MAMBA_ROOT_PREFIX=str(TOOLS / 'mamba')), check=False)
    return rs


def run(ctx):
    w = ctx.work / 'hla'; w.mkdir(exist_ok=True)
    rs = r_env()
    progress('extracting the HLA region')
    sh(['bcftools', 'view', '-M2', '-r', '6:28000000-34500000', '-Ov', '-o', w / 'mhc.vcf', ctx.work / 'imputed' / 'me.chr6.vcf.gz'])
    sh(['plink2', '--vcf', w / 'mhc.vcf', '--make-bed', '--set-all-var-ids', '@:#:$r:$a', '--new-id-max-allele-len', '50', 'truncate',
        '--out', w / 'mhc', '--silent'])
    (w / 'mhc.vcf').unlink()
    progress('predicting HLA-A, -B, -C, -DRB1, -DQA1, -DQB1, -DPB1')
    sh([rs, HERE / 'hla.R', w / 'mhc', ctx.data / 'hla' / 'European-HLA4-hg19.RData', w / 'hla_results.tsv'])
    out = {}
    for r in csv.DictReader(open(w / 'hla_results.tsv'), delimiter='\t'):
        p = float(r['prob'])
        out[r['locus']] = dict(allele1=r['allele1'], allele2=r['allele2'], prob=p, confident=p >= 0.5, alternatives=r['alternatives'])
    jdump(out, ctx.work / 'hla.json')
    return ', '.join(f'{k}*{v["allele1"]}/*{v["allele2"]}' for k, v in out.items() if k in ('A', 'B', 'DQB1'))
