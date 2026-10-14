# Small shared helpers: logging, running tools, resumable downloads, JSON I/O.
import hashlib, json, os, shutil, subprocess, sys, time, urllib.request, zipfile, tarfile
from pathlib import Path

LOG = None  # set by the runner to an open log file
STATUS = {'step': '', 'detail': '', 'start': 0.0, 'expect': ''}  # live status line (see Heartbeat)


def progress(detail):
    """Steps call this to say what they are doing right now; the heartbeat shows it with the elapsed time."""
    STATUS['detail'] = detail
    if LOG: LOG.write(f'[progress] {detail}\n'); LOG.flush()


class Heartbeat:
    """Redraws '  … Step: detail (12 min so far, usually 2-6 h)' every few seconds, so long steps never look frozen."""
    def __init__(self):
        import threading
        self.stop = threading.Event(); self.t = threading.Thread(target=self.loop, daemon=True); self.t.start()

    def loop(self):
        tty = sys.stdout.isatty(); last = 0
        while not self.stop.wait(2 if tty else 5):
            if not STATUS['step']: continue
            el = time.time() - STATUS['start']
            line = f"  … {STATUS['step']}{': ' + STATUS['detail'] if STATUS['detail'] else ''} ({fmt_time(el)} so far{', usually ' + STATUS['expect'] if STATUS['expect'] else ''})"
            if tty:
                w = shutil.get_terminal_size((100, 20)).columns - 1
                print('\r' + line[:w].ljust(w), end='', flush=True)
            elif time.time() - last > 60:  # logs / non-interactive: one line a minute
                print(line, flush=True); last = time.time()

    def clear(self):
        if sys.stdout.isatty(): print('\r' + ' ' * (shutil.get_terminal_size((100, 20)).columns - 1) + '\r', end='', flush=True)


def fmt_time(s):
    s = int(s)
    return f'{s} s' if s < 60 else f'{s // 60} min' if s < 3600 else f'{s // 3600} h {s % 3600 // 60:02d} min'


def say(msg='', end='\n'):
    print(msg, end=end, flush=True)
    if LOG: LOG.write(msg + end); LOG.flush()


def run(cmd, cwd=None, log=None, env=None, check=True, quiet=True, stdout=None):
    """Run a command (list). Output goes to the step log; raise with the log tail on failure."""
    cmd = [str(c) for c in cmd]
    if LOG: LOG.write('$ ' + ' '.join(cmd) + '\n'); LOG.flush()
    out = stdout if stdout is not None else (LOG if (quiet and LOG) else None)
    p = subprocess.run(cmd, cwd=cwd, env=env, stdout=out, stderr=subprocess.STDOUT if out is LOG else None)
    if check and p.returncode != 0:
        raise RuntimeError(f'command failed ({p.returncode}): {" ".join(cmd[:4])} ... (see the log)')
    return p.returncode


def capture(cmd, cwd=None, input=None):
    p = subprocess.run([str(c) for c in cmd], cwd=cwd, capture_output=True, text=input is None or isinstance(input, str), input=input)
    if p.returncode != 0:
        raise RuntimeError(f'command failed: {" ".join(map(str, cmd[:4]))}: {str(p.stderr)[-800:]}')
    return p.stdout


def human(n):
    for u in ('B', 'KB', 'MB', 'GB', 'TB'):
        if abs(n) < 1024 or u == 'TB': return f'{n:.0f} {u}' if u in ('B', 'KB') else f'{n:.1f} {u}'
        n /= 1024


def download(url, dest, desc=None, min_bytes=1):
    """Resumable HTTP download with a progress line. Skips files that are already complete."""
    dest = Path(dest); dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size >= min_bytes: return dest
    part = dest.with_name(dest.name + '.part')
    desc = desc or dest.name
    for attempt in range(6):
        have = part.stat().st_size if part.exists() else 0
        req = urllib.request.Request(url, headers={'User-Agent': 'genome-kit/1.0', **({'Range': f'bytes={have}-'} if have else {})})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                if have and r.status != 206: have = 0  # server ignored the range: start over
                total = r.headers.get('Content-Length'); total = int(total) + have if total else None
                with open(part, 'ab' if have else 'wb') as f:
                    got, t0, last = have, time.time(), 0
                    while True:
                        b = r.read(1 << 20)
                        if not b: break
                        f.write(b); got += len(b)
                        if time.time() - last > 0.5:
                            last = time.time(); rate = (got - have) / max(last - t0, 1e-3)
                            pct = f'{got / total * 100:5.1f}% of {human(total)}' if total else human(got)
                            print(f'\r    {desc}: {pct}  {human(rate)}/s   ', end='', flush=True)
            print(f'\r    {desc}: done ({human(got)}){" " * 30}', flush=True)
            if total and got < total: raise IOError('incomplete download')
            part.rename(dest); return dest
        except Exception as e:
            if attempt == 5: raise RuntimeError(f'download failed for {url}: {e}')
            print(f'\n    {desc}: {e}; retrying in {5 * (attempt + 1)} s', flush=True); time.sleep(5 * (attempt + 1))


def unpack(archive, dest):
    archive, dest = Path(archive), Path(dest); dest.mkdir(parents=True, exist_ok=True)
    if archive.suffix == '.zip':
        with zipfile.ZipFile(archive) as z: z.extractall(dest)
    else:
        with tarfile.open(archive) as t: t.extractall(dest, filter='data')


def jload(p, default=None):
    try: return json.load(open(p))
    except (FileNotFoundError, json.JSONDecodeError): return default


def jdump(obj, p):
    p = Path(p); p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + '.tmp'); json.dump(obj, open(tmp, 'w'), indent=1, default=str); tmp.replace(p)


def free_bytes(path):
    path = Path(path)
    while not path.exists(): path = path.parent
    return shutil.disk_usage(path).free


def sha1_of(text):
    return hashlib.sha1(text.encode()).hexdigest()[:12]


def which(name):
    return shutil.which(name)


def java():
    j = which('java')
    if not j: raise RuntimeError('Java not found in the tool environment')
    return j


def cpu_threads():
    return max(1, min(8, (os.cpu_count() or 2) - 1))
