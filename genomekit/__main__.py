# genome-kit: interactive wizard + step runner. Started by run.sh / run.bat.
import argparse, datetime, os, platform, re, shutil, subprocess, sys, time, traceback
from pathlib import Path
from . import util, rawfile, refs
from .util import say, jload, jdump, human

REPO = Path(__file__).resolve().parent.parent
B, D, R, G, Y, X = ('\033[1m', '\033[2m', '\033[31m', '\033[32m', '\033[33m', '\033[0m') if sys.stdout.isatty() else ('',) * 6


class Ctx:
    def __init__(self, out, data, threads):
        self.out = Path(out); self.work = self.out / 'work'; self.data = Path(data)
        self.genome = self.work / 'genome.txt'; self.threads = threads
        self.work.mkdir(parents=True, exist_ok=True); self.data.mkdir(parents=True, exist_ok=True)
        self.cfg = jload(self.work / 'config.json', {})


def steps():
    from .steps import core, markers, report
    from .steps import impute, hla, pgs, ancient, effects
    # (id, tier, function, description, always re-run)
    return [
        ('qc', 'core', core.qc, 'Quality check and parental-relatedness check', False),
        ('mtdna', 'core', core.mtdna, 'Mother-line (mitochondrial) haplogroup', False),
        ('ydna', 'core', core.ydna, 'Father-line (Y-chromosome) haplogroup', True),
        ('clinvar', 'core', core.clinvar, 'Known disease variants (ClinVar)', False),
        ('impute', 'impute', impute.run, 'Imputation with Beagle and 1000 Genomes (the long step)', False),
        ('hla', 'impute', hla.run, 'HLA immune-gene typing (HIBAG)', False),
        ('pgs', 'impute', pgs.run, 'Polygenic scores with ancestry-adjusted percentiles', False),
        ('markers', 'core', markers.run, 'Curated health and trait markers', True),
        ('pharmcat', 'core', core.pharmcat, 'Medicine genes (PharmCAT)', False),
        ('ancient', 'ancient', ancient.run, 'Ancient-DNA ancestry (AADR)', False),
        ('effects', 'effects', effects.run, 'Protein-variant effect predictions', False),
        ('report', 'core', report.build, 'Building the report pages', True),
    ]


def read(prompt):
    # no keyboard attached (piped, or started from a non-interactive shell): explain instead of a traceback
    try: return input(prompt)
    except EOFError:
        say(f'\n{R}No answer could be read: genome-kit needs to be started in a terminal window to ask its questions.{X}')
        say('To run without questions: ./run.sh --input <raw DNA file> --yes')
        sys.exit(1)


def ask(q, default=None):
    s = read(f'{q}{f" [{default}]" if default not in (None, "") else ""}: ').strip()
    return s if s else (default or '')


def yesno(q, default=True):
    while True:
        s = read(f'{q} [{"Y/n" if default else "y/N"}]: ').strip().lower()
        if not s: return default
        if s in ('y', 'yes'): return True
        if s in ('n', 'no'): return False


def find_inputs():
    c = [p for p in (REPO / 'input').glob('*') if p.is_file() and p.name != 'README.md' and not p.name.startswith('.')]
    return sorted(c, key=lambda p: -p.stat().st_mtime)


def slugify(s):
    s = re.sub(r'[^A-Za-z0-9]+', '_', s).strip('_')
    return s[:40] or 'genome'


def local_path(p):
    # a Windows path (dragged onto the window or passed to run.bat) means nothing inside WSL: D:\x\y.txt -> /mnt/d/x/y.txt
    p = p.strip().strip('"').strip("'")
    if re.match(r'^[A-Za-z]:[\\/]', p) and 'microsoft' in platform.release().lower():
        try: return subprocess.run(['wslpath', '-u', p], capture_output=True, text=True).stdout.strip() or p
        except Exception: pass
    return p


def shown_path(path):
    # under WSL, show the Windows path (D:\...) that people can paste into Explorer
    if 'microsoft' in platform.release().lower() and str(path).startswith('/mnt/'):
        try: return subprocess.run(['wslpath', '-w', str(path)], capture_output=True, text=True).stdout.strip() or str(path)
        except Exception: pass
    return str(path)


def open_in_browser(path):
    try:
        if platform.system() == 'Darwin': subprocess.run(['open', str(path)])
        elif 'microsoft' in platform.release().lower():
            win = subprocess.run(['wslpath', '-w', str(path)], capture_output=True, text=True).stdout.strip()
            subprocess.run(['explorer.exe', win])
        elif shutil.which('xdg-open'): subprocess.run(['xdg-open', str(path)], stderr=subprocess.DEVNULL)
    except Exception:
        pass


def wizard(args):
    say(f'\n{B}genome-kit{X}: a private reading of your consumer DNA file')
    say(f'{D}Everything runs on this computer. Your DNA file and results are never uploaded; only public tools and')
    say(f'reference data are downloaded.{X}\n')
    # 1. raw file
    src = args.input
    if not src:
        cands = find_inputs()
        if len(cands) == 1 and yesno(f'Use {B}{cands[0].name}{X} from the input folder?'):
            src = str(cands[0])
        elif len(cands) > 1:
            for i, p in enumerate(cands, 1): say(f'  {i}. {p.name}')
            k = ask('Which file? (number)', '1')
            src = str(cands[int(k) - 1]) if k.isdigit() and 0 < int(k) <= len(cands) else local_path(k)
        while not src or not Path(src).expanduser().is_file():
            if src: say(f'{R}Not found: {src}{X}')
            say('Put your raw DNA file (23andMe, AncestryDNA, MyHeritage, FamilyTreeDNA or LivingDNA; .txt, .csv or .zip)')
            say('into the "input" folder, or drag the file onto this window, then press Enter.')
            src = local_path(ask('Path to the raw DNA file').replace('\\ ', ' '))
    src = Path(local_path(str(src))).expanduser().resolve()
    # 2. name
    name = args.name if args.name is not None else ask('First name to use in the report (optional, press Enter to skip)',
                                                        rawfile.guess_name(src).split(' ')[0] if rawfile.guess_name(src) else '')
    out = Path(args.out) if args.out else REPO / 'results' / slugify(name or src.stem)
    # 3. tiers
    say(f'\n{B}What should be analysed?{X}  (downloads happen once and are reused for later runs)\n')
    data = Path(args.data) if args.data else Path(os.environ.get('GENOMEKIT_DATA') or REPO / 'data')
    chosen = ['core']
    for k in refs.TIER_ORDER:
        t = refs.TIERS[k]
        say(f'  {B}{t["title"]}{X}  {D}(~{t["gb"]:g} GB download, {t["time"]}){X}')
        say(f'  {D}{t["desc"]}{X}')
        if k == 'core': say(f'  {G}always included{X}\n'); continue
        if yesno('  Include this?', default=False): chosen.append(k)
        say('')
    return src, name, out, data, chosen


def main():
    ap = argparse.ArgumentParser(prog='genome-kit', description='Private analysis of a consumer DNA raw file.')
    ap.add_argument('--input', help='raw DNA file (23andMe, AncestryDNA, MyHeritage, FTDNA, LivingDNA)')
    ap.add_argument('--name', help='first name used in the report (default: from the file name)')
    ap.add_argument('--tiers', help='comma list: core,impute,ancient,effects (default: ask)')
    ap.add_argument('--out', help='results folder (default: results/<name>)')
    ap.add_argument('--data', help='folder for shared public reference data (default: data/)')
    ap.add_argument('--threads', type=int, default=util.cpu_threads())
    ap.add_argument('--redo', help='comma list of steps to run again (e.g. pgs,report)')
    ap.add_argument('-y', '--yes', action='store_true', help='do not ask questions (needs --input)')
    ap.add_argument('--prepare', metavar='TIERS', help='only download the public reference data for these tiers (e.g. core,impute) and exit')
    args = ap.parse_args()

    if args.prepare:
        data = Path(args.data) if args.data else Path(os.environ.get('GENOMEKIT_DATA') or REPO / 'data')
        tiers = set(args.prepare.split(',')) | {'core'}
        refs.ensure_core(data)
        if 'impute' in tiers: refs.ensure_impute(data, args.threads)
        if 'ancient' in tiers: refs.ensure_ancient(data)
        if 'effects' in tiers: refs.ensure_effects(data)
        say(f'Reference data ready in {data}'); return

    if args.yes or args.tiers:
        if not args.input: ap.error('--input is needed with --yes/--tiers')
        src = Path(local_path(args.input)).expanduser().resolve(); name = args.name or ''
        out = Path(args.out) if args.out else REPO / 'results' / slugify(name or src.stem)
        data = Path(args.data) if args.data else Path(os.environ.get('GENOMEKIT_DATA') or REPO / 'data')
        chosen = ['core'] + [t for t in (args.tiers or '').split(',') if t in refs.TIERS and t != 'core']
    else:
        src, name, out, data, chosen = wizard(args)

    # one results folder per person: refuse to mix a different raw file into an existing folder
    import hashlib
    digest = hashlib.sha1(src.read_bytes()).hexdigest()
    prev = jload(Path(out) / 'work' / 'sample.json', {})
    if prev.get('source_sha1') and prev['source_sha1'] != digest:
        say(f'{R}{out} already holds results for a different raw file ({prev.get("source_file")}).{X}')
        say('Choose another name or --out folder so the two people\'s results never mix.'); sys.exit(1)
    ctx = Ctx(out, data, args.threads)
    util.LOG = open(ctx.work / 'log.txt', 'a')
    util.LOG.write(f'\n===== {datetime.datetime.now():%Y-%m-%d %H:%M} genome-kit run, tiers {chosen}\n')

    # normalise the raw file
    say(f'\nReading {src.name} ...')
    try:
        st = rawfile.normalise(src, ctx.genome)
    except Exception as e:
        say(f'{R}Could not read this file: {e}{X}'); sys.exit(1)
    if st['build'] == 'GRCh38':
        say(f'{R}This file uses the newer GRCh38 genome coordinates. genome-kit currently needs GRCh37 files (all major consumer tests export GRCh37).{X}'); sys.exit(1)
    if st['markers'] < 100_000:
        say(f'{R}Only {st["markers"]:,} markers were found. This does not look like a full raw-data file.{X}'); sys.exit(1)
    sex, sexinfo = rawfile.infer_sex(ctx.genome)
    fmtname = {'23andme': '23andMe-style', 'ancestry': 'AncestryDNA', 'csv': 'MyHeritage/FTDNA-style'}.get(st['format'], st['format'])
    say(f'  {fmtname} file, {st["markers"]:,} markers, {st["call_rate"] * 100:.1f}% called, build {st["build"]}, genetic sex: {sex}')
    prev = jload(ctx.work / 'sample.json', {})
    sample = dict(prev, source_file=src.name, source_sha1=digest, name=name, sex=sex, sex_info=sexinfo, **{k: st[k] for k in ('format', 'markers', 'called', 'call_rate', 'build')})
    jdump(sample, ctx.work / 'sample.json')

    # disk space and confirmation
    need = sum(refs.TIERS[t]['gb'] for t in chosen) * 1.6 + (6 if 'impute' in chosen else 0)  # unpacking + temporary files
    free = util.free_bytes(data) / 1e9
    say(f'\n{B}Plan{X}: {", ".join(refs.TIERS[t]["title"] for t in chosen)}')
    say(f'  Results: {out}')
    say(f'  Reference data: {data}  (needs about {max(need, 1):.0f} GB free in total; {free:.0f} GB free now)')
    if free < need:
        say(f'{Y}  Not enough free disk space. Free some space, choose fewer parts, or point --data to a bigger drive.{X}')
        if args.yes or not yesno('  Continue anyway?', default=False): sys.exit(1)
    if not args.yes and not yesno('\nStart now?'): sys.exit(0)
    ctx.cfg.update(tiers=chosen, name=name); jdump(ctx.cfg, ctx.work / 'config.json')

    # downloads
    say(f'\n{B}Downloading public reference data{X}  {D}(only public files; anything already downloaded is skipped){X}')
    t0 = time.time()
    refs.ensure_core(data)
    if 'impute' in chosen: refs.ensure_impute(data, ctx.threads)
    if 'ancient' in chosen: refs.ensure_ancient(data)
    if 'effects' in chosen: refs.ensure_effects(data)

    # steps
    status = jload(ctx.work / 'status.json', {})
    redo = set((args.redo or '').split(','))
    say(f'\n{B}Analysing{X}  {D}(each step shows what it is doing; you can leave this window open and come back){X}')
    EXPECT = dict(qc='under a minute', mtdna='under a minute', ydna='under a minute', clinvar='1-2 min', impute='2-6 h (the longest step)',
                  hla='5-15 min (first time also sets up R)', pgs='20-60 min', markers='under a minute', pharmcat='under a minute',
                  ancient='10-30 min', effects='15-30 min', report='under a minute')
    hb = util.Heartbeat()
    for sid, tier, fn, desc, always in steps():
        if tier not in chosen: continue
        if status.get(sid, {}).get('state') == 'done' and not always and sid not in redo:
            say(f'  {G}✓{X} {desc} {D}(already done){X}'); continue
        util.LOG.write(f'\n--- step {sid}\n'); s0 = time.time()
        util.STATUS.update(step=desc, detail='', start=s0, expect=EXPECT.get(sid, ''))
        try:
            msg = fn(ctx) or ''
            util.STATUS['step'] = ''; hb.clear()
            status[sid] = dict(state='done', msg=msg, when=datetime.datetime.now().isoformat(timespec='seconds'), seconds=round(time.time() - s0))
            say(f'  {G}✓{X} {desc} {D}{msg} ({util.fmt_time(time.time() - s0)}){X}')
        except Exception as e:
            util.STATUS['step'] = ''; hb.clear()
            util.LOG.write(traceback.format_exc())
            status[sid] = dict(state='failed', msg=str(e), when=datetime.datetime.now().isoformat(timespec='seconds'))
            say(f'  {R}✗ {desc}: {e}{X}')
        jdump(status, ctx.work / 'status.json')
    failed = [k for k, v in status.items() if v['state'] == 'failed']
    idx = ctx.out / 'index.html'
    say(f'\n{B}Done{X} in {(time.time() - t0) / 60:.0f} min. Open {B}{shown_path(idx)}{X}')
    say(f'{Y}For information only, not a medical diagnosis. Talk to a doctor or other medical professional before acting on anything in the report.{X}')
    if failed: say(f'{Y}Some steps failed: {", ".join(failed)}. Details are in {ctx.work / "log.txt"}. The pages show everything else.{X}')
    if idx.exists() and not args.yes and yesno(f'\nOpen the report (home page) in your browser now?'): open_in_browser(idx)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        say('\nStopped. Run again to continue where it left off.'); sys.exit(130)
