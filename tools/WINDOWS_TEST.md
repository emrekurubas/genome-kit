# Test run on the Windows PC (instructions for a Claude agent there)

Goal: check that a stranger can clone genome-kit and run it on Windows, and validate the ancestry step. **Use public data only.**
No personal genome file is in this repo, and none must be copied to this machine. The test "user" is a synthetic file made
from a public 1000 Genomes person.

## 1. Fresh-clone install via run.bat (the user-facing path)
1. Clone this repo into a normal Windows folder, e.g. `C:\genome-kit-test`.
2. If WSL has no Linux distribution yet, follow what `run.bat` prints (`wsl --install -d Ubuntu`) and note every manual step needed. That list goes into the report.
3. Double-click or run `run.bat --prepare core,impute,ancient,effects` from `cmd`.
   - The first run builds the toolbox in WSL under `~/.genome-kit/tools`. The reference data (~12 GB) goes to `~/.genome-kit/data`.
   - Record how long the setup and the downloads take, and any errors.

## 2. End-to-end pipeline test with a synthetic genome
Inside WSL, from the repo folder (`/mnt/c/genome-kit-test`):
```
T=~/.genome-kit/tools/envs/core/bin
PATH=$T:$T/../lib/jvm/bin:$PATH $T/python tools/make_test_genome.py --sample HG00096 --data ~/.genome-kit/data --out input/test_HG00096.txt
```
Then from Windows, run `run.bat` with no arguments and walk through the wizard as a new user would:
- pick `test_HG00096.txt`;
- name it `Test`;
- answer yes to all three optional parts.

Record:
- every question and message that was unclear;
- the time per step (shown at the end, also in `results/Test/work/status.json`);
- any failed step, with the matching part of `results/Test/work/log.txt`.

Open `results/Test/index.html` in a Windows browser and check:
- every page opens;
- the pages work in dark mode;
- the pages work at phone width (browser dev tools).

Expected for HG00096 (a British man in 1000 Genomes):
- closest populations are British/NW-European;
- genetic sex is "unknown" (the synthetic file has no X/Y).

## 3. Ancestry validation (public reference genomes)
In WSL, from the repo folder:
```
PATH=$T:$PATH $T/python tools/validate_ancestry.py --data ~/.genome-kit/data --out validation
```
This holds out about 40 reference people from every world region and runs each through the ancestry step with 18 different settings. It takes a while; run it in the background and check the log. Do not change any settings or code to make results look better. Just report.

## 4. Report back
Commit and push only these files:
- `validation/ancestry_summary.md`
- `validation/ancestry_holdout.tsv`
- a short `validation/windows_test_report.md` covering:
  - the install experience: manual steps, problems and timings;
  - the step timings and any failures, with log excerpts;
  - the page check results.

Do **not** commit anything from `results/`, `input/` or `data/`. The `.gitignore` already excludes them; check with `git status` before committing.
