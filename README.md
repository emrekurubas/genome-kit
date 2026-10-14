# genome-kit

A private, plain-language reading of your consumer DNA raw data (23andMe, AncestryDNA, MyHeritage, FamilyTreeDNA, LivingDNA), made with one command.

**Everything runs on your own computer.** Your DNA file and results are never uploaded. The kit only downloads public tools and public reference data (ClinVar, 1000 Genomes, PGS Catalog, the Allen Ancient DNA Resource and similar).

> [!IMPORTANT]
> **For information only. Not a medical diagnosis.**
> The results are not absolute findings. A consumer DNA chip read by research software can be wrong, especially about rare variants, and most genes only nudge chances up or down.
> **Talk to a doctor or other medical professional** before you act on anything in the report. Do not start, stop or change a medicine or treatment because of it. A doctor can order a clinical test to confirm a result.
> The software is provided as is, without any guarantee of accuracy. See [DISCLAIMER.md](DISCLAIMER.md).

**Contents:** [What you get](#what-you-get) · [Quick start](#quick-start) · [What happens on Windows](#what-happens-on-windows) · [Choose what to run](#choose-what-to-run) · [Your results](#your-results) · [Running again](#running-again-adding-parts-other-people) · [Troubleshooting](#troubleshooting) · [FAQ](#faq) · [Uninstalling](#uninstalling) · [How reliable is it?](#how-reliable-is-it) · [Privacy](#privacy) · [How it works](#how-it-works-for-the-curious) · [License](#license)

## What you get

A folder of web pages you open in your browser. They work offline, in light and dark mode, and on a phone.

| Page | What's in it |
|---|---|
| **Home** (`index.html`) | Links to every page, and how the analysis was made. |
| **Genome Report** | A short summary first, then:<br>• medicines that need a different choice or dose for you (PharmCAT, CPIC guidelines)<br>• health findings with absolute risks<br>• polygenic scores<br>• what was checked and came back fine<br>• fun traits<br>Written for non-specialists. |
| **Doctor checklist** | A printable list of the check-up tests worth doing, plus a medicine card for your doctor or pharmacist. |
| **Ancestry** | Your father-line and mother-line haplogroups, your closest present-day populations, and ancient-DNA mixture models. |
| **Variant effects** | Protein-changing variants scored with AlphaMissense and REVEL. Only with the optional "Variant effects" part. |

## Quick start

1. **Get your raw data file** from your DNA testing company (23andMe, AncestryDNA, MyHeritage, FamilyTreeDNA or LivingDNA). It's usually in your account or privacy settings, under a name like "Download raw data" or "Download DNA data". The company may email you a download link.

   You can use the `.txt`, `.csv` or `.zip` file as it comes; there's no need to unzip it.
2. **Put the file into the `input` folder** inside this folder.
3. **Start the kit:**
   - **Windows:** double-click `run.bat`. See [What happens on Windows](#what-happens-on-windows).
   - **macOS / Linux:** open a terminal in this folder and run `./run.sh`.
4. **Answer the questions:** which file, your first name (optional, used in the report), and which parts to run. Nothing starts until you confirm.
5. **Wait.** The first run sets up a toolbox (about 1 GB, 5–10 minutes). The core analysis then takes a few minutes. Each step shows what it's doing and how long it usually takes.
6. **Open the report.** At the end the kit asks whether to open it in your browser. You can also open `results/<name>/index.html` yourself at any time.

## What happens on Windows

The analysis tools only exist for Linux, so on Windows genome-kit runs them inside **WSL** (Windows Subsystem for Linux), a free part of Windows. You don't need to know anything about WSL or Linux: `run.bat` sets everything up and asks before every change. The launcher's steps are:

1. **[1/4] Is WSL installed?** If not, it asks "Install WSL now?".
   - Windows then asks for administrator approval once, and a second window shows the download.
   - If Windows needs a restart to finish, the launcher offers to restart. After you sign in again, `run.bat` starts again by itself. If you say no, it continues after your next restart.
2. **[2/4] Does WSL respond?** Every check has a time limit, so the window never hangs silently.
   - If WSL is stuck (this can happen after sleep, Windows updates or Docker changes), the launcher offers to restart WSL.
3. **[3/4] genome-kit's Linux system.** The first time, it asks "Set it up now?" and downloads a small Ubuntu named `genome-kit` (about 500 MB).
   - It is separate from any Linux you already use.
   - It never asks for a Linux user name or password.
4. **[4/4] genome-kit itself:** the toolbox install on the first run, then the questions and the analysis.

The window stays open at the end, so you can read everything. Press Enter to close it.

**Requirements on Windows:**
- Windows 10 (version 2004 or later) or Windows 11.
- Administrator rights once, to install WSL.
- Virtualization turned on in the computer's firmware. It is on by default on most computers from the last few years.

## Choose what to run

The first part always runs. The others are optional, and you can add them later without redoing anything.

| Part | Download (once) | Time | Adds |
|---|---|---|---|
| Health, medicines, traits, family lines | ~0.25 GB | a few minutes | • medicine genes<br>• known disease variants (ClinVar)<br>• ~45 curated markers<br>• haplogroups<br>• parental-relatedness check |
| Imputation, polygenic scores, HLA typing | ~8.5 GB | 2–6 h | • ~30 M imputed variants<br>• ~45 ancestry-adjusted polygenic scores<br>• HLA immune-gene typing (better carbamazepine, abacavir and allopurinol checks) |
| Ancient-DNA ancestry | ~1.9 GB | 20–60 min | • closest of 260 present-day populations<br>• deep-time and historic mixture models |
| Variant effects | ~1.6 GB | 15–30 min | AlphaMissense + REVEL scores for every missense variant you carry |

Downloads are kept and reused by later runs, including other people's runs on the same computer.

## Your results

Results go to `results/<name>/`, where `<name>` is the name you gave (or the file name):

| Path | What it is |
|---|---|
| `index.html` | Start here. It links to every other page. |
| `Genome_Report.html`, `Doctor_Checklist.html`, `Ancestry.html`, `Variant_Effects.html` | The report pages. Each is a single self-contained file. |
| `work/` | Intermediate files, plus `log.txt`, which has the details of every step. |

The pages are plain files: you can copy them to another computer or print them (the Doctor checklist has a Print button). Keep them private; they describe your health.

## Running again, adding parts, other people

- **Interrupted?** Run the kit again. It continues where it stopped. Finished steps and completed downloads are skipped.
- **Add a part later.** Run the kit again with the same file and name, and choose the extra part. Everything done before is kept.
- **Another person.** Put their file in `input/` and give a different name. Each person gets their own `results/<name>/` folder, and the kit refuses to mix two people's files into one folder.
- **Redo a step.** For example, after an update, run `./run.sh --redo pgs,report`. On Windows, add the same options after `run.bat` in a Command Prompt.

### Command-line options

```
./run.sh --input input/my_raw_data.txt --name Alex --tiers impute,ancient --yes   # no questions
./run.sh --prepare core,impute          # only download the reference data, for example overnight
./run.sh --data /big/disk/genome-kit-data   # keep the reference data on another drive (macOS/Linux)
./run.sh --redo pgs,report               # recompute selected steps
./run.sh --threads 4                     # use fewer CPU cores
```

On Windows, use the same options with `run.bat` (for example `run.bat --tiers core`).

## Troubleshooting

When something fails, the message on screen says why and what to do. The details are in `results/<name>/work/log.txt`. Most problems are fixed by running the kit again: it resumes where it stopped.

### Windows: starting `run.bat`

| What you see | What to do |
|---|---|
| "Windows protected your PC" (SmartScreen) | Click **More info → Run anyway**. Windows shows this for scripts downloaded from the internet. To stop it permanently, right-click the downloaded `.zip` **before** extracting it, choose **Properties**, tick **Unblock** and press OK. |
| The window opens and closes at once | Open a Command Prompt in the genome-kit folder and run `run.bat` there, so you can read the message. |
| "WSL is not installed on this computer yet" and you said no, or the administrator prompt was declined | Run `run.bat` again and answer yes. Or open PowerShell as Administrator, run `wsl --install --no-distribution`, then restart. |
| You can't get administrator rights (for example, a work computer) | WSL can't be installed without them. Ask your IT department to install WSL, or use another computer. |
| "Windows needs to restart once to finish turning on WSL" | Restart. `run.bat` starts again by itself after you sign in. If it doesn't, start it again yourself. |
| "WSL is not responding" | Let the launcher restart WSL. If that doesn't help, restart the computer. If it keeps happening, run `wsl --update` in PowerShell. |
| "Windows reports that virtualization is not available" | Turn on virtualization (Intel VT-x, AMD-V or SVM) in the computer's BIOS/UEFI settings. Then, in "Turn Windows features on or off", tick "Virtual Machine Platform" and "Windows Subsystem for Linux", and restart. |
| "The Linux system could not be set up" | Run `wsl --update` in PowerShell, then `run.bat` again. |
| "The Linux system did not start properly" | Restart the computer. If it keeps happening, run `wsl --update`. As a last resort, run `wsl --unregister genome-kit` to remove genome-kit's Linux system, then `run.bat` to set it up fresh. This deletes the downloads, not your results. |

### Your DNA file

| What you see | What to do |
|---|---|
| "Not found" | Check the file is in the `input` folder. Or drag the file onto the window and press Enter; Windows paths such as `D:\Downloads\genome.txt` work too. |
| "Could not read this file: unrecognised file format" | Use the raw data file exactly as downloaded from your testing company, not a report, PDF or converted file. |
| "the zip file contains no .txt/.csv file" | The zip holds something else. Download the raw data again, or unzip it and use the `.txt` or `.csv` inside. |
| "Only N markers were found" | The file isn't a complete raw data file, or it was cut short. Download it again. |
| "This file uses the newer GRCh38 genome coordinates" | genome-kit needs GRCh37 files, which all major consumer tests provide. Download the standard raw data file from your testing company. Files from whole-genome sequencing or conversion services are often GRCh38. |
| "… already holds results for a different raw file" | You gave a name that another person's results already use. Choose a different name. |

### During the run

| What you see | What to do |
|---|---|
| "Not enough free disk space" | Free some space, choose fewer parts, or (macOS/Linux) put the reference data on a bigger drive with `--data`. On Windows, the downloads live inside genome-kit's Linux system on drive C:. To move it, run `wsl --manage genome-kit --move D:\WSL` in PowerShell. |
| "download failed for …" | Check your internet connection and run the kit again. Downloads resume where they stopped. On networks that block large downloads or use a proxy, try another network. |
| A step shows ✗ and the run continues | The pages still show everything else. Look up the step in `results/<name>/work/log.txt`, fix the cause if the message names one, then run again. Only unfinished steps run. |
| "'curl' is needed" or "'tar' is needed" (Linux) | Install them with your package manager (for example `sudo apt install curl tar`), then run again. |
| `./run.sh: Permission denied` (macOS/Linux) | Run `bash run.sh` instead, or make it executable once with `chmod +x run.sh`. |
| The toolbox setup failed halfway | Delete the toolbox and run again. The toolbox is `.tools/` in this folder on macOS/Linux. On Windows, run `wsl --unregister genome-kit` (this deletes the toolbox and downloads, not your results). |

### After the run

| What you see | What to do |
|---|---|
| The browser didn't open | Open `results/<name>/index.html` yourself. The kit prints its full path at the end. |
| Genetic sex shows "unknown" | Your file has too few X/Y chromosome markers to tell. This doesn't affect the other results. |
| Polygenic scores, HLA or ancient ancestry are missing | They come from the optional parts. Run again and choose them. |
| A finding worries you | Talk to a doctor or genetic counsellor. Consumer chips often get rare variants wrong, so a clinical test is needed to confirm it. |

If you're still stuck, open an issue and include the last lines of `results/<name>/work/log.txt`. Do **not** attach your DNA file or results.

## FAQ

**Is my DNA uploaded anywhere?**
No. Everything runs on your computer. The kit only downloads public tools and reference data, and sends nothing about you.

**Does it cost anything?**
No, it's free for personal and other non-commercial use. See [License](#license).

**Which tests are supported?**
23andMe, AncestryDNA, MyHeritage, FamilyTreeDNA and LivingDNA raw data in GRCh37 coordinates. Whole-genome or exome files (VCF, BAM) are not supported.

**Can I analyse my family's DNA?**
Yes. Each person gets a separate results folder. Only analyse someone's DNA with their clear permission. DNA can also reveal unexpected family relationships.

**Why does Windows need WSL?**
Several of the analysis tools only exist for Linux. WSL runs them inside Windows, without a separate computer or virtual machine to manage.

**How much disk space do I need?**
About 2 GB for the core part. With every part, allow about 25 GB.

**Can I share the pages?**
They are self-contained files, so you can send them to your doctor. Remember they contain sensitive health information.

## Uninstalling

- **Windows:**
  1. Run `wsl --unregister genome-kit` in PowerShell. This removes genome-kit's Linux system, with the toolbox and downloads.
  2. Delete the genome-kit folder. This deletes your results too, so move them first if you want to keep them.
  3. If you installed WSL only for genome-kit and want it gone too, run `wsl --uninstall` in PowerShell as Administrator.
- **macOS / Linux:** delete the genome-kit folder. It contains the toolbox (`.tools/`), the downloads (`data/`) and your results. Nothing is installed anywhere else.

## Requirements

- **Operating system:**
  - Windows 10 (2004 or later) or 11, with WSL (installed by `run.bat`);
  - macOS (Apple Silicon or Intel);
  - Linux (x86-64 or ARM64).
- **Disk:** about 2 GB of free space for the core part. With every part, allow about 25 GB.
- **Memory:** 8 GB of RAM. 16 GB makes imputation faster.
- **Network:** an internet connection for the first run and whenever you add a part. Downloads are kept, so later runs download little or nothing.

## How reliable is it?

The results are for information only and are not absolute findings. Discuss anything that concerns you with a doctor or other medical professional. The full terms are in [DISCLAIMER.md](DISCLAIMER.md).

- **Consumer chips are not clinical tests.** They are very accurate for common variants, but they often get rare variants wrong. In one study, about 40% of rare "disease-causing" calls from raw data were false. The report says so whenever it shows such a variant. Confirm anything you would act on with a clinical test.
- **Medicine results follow CPIC guidelines.** CYP2D6 cannot be read from consumer chips.
- **Polygenic scores shift chances a little; they do not diagnose.** Percentiles are adjusted for ancestry against 1000 Genomes. That reference has no Middle Eastern, Caucasus or North African groups, so percentiles are less certain for people from there.
- **HLA typing uses the published HIBAG European model.** For other ancestries, results with low confidence are ignored, and the medicine check falls back on tag markers.
- **Ancient-DNA models are best fits, not family trees.**

## Privacy

- Your raw file, results and intermediate files stay in `input/` and `results/`. Both folders are excluded from git.
- `data/` holds only public reference data. It is the same for everyone.
- Nothing is sent anywhere. The kit makes no network requests except downloading the public files listed in `genomekit/refs.py`.
- The pages are self-contained files with no trackers and no external scripts.

## How it works (for the curious)

| Step | Tools |
|---|---|
| QC and runs of homozygosity | plink 1.9 |
| Medicine genes | PharmCAT 3.4, with HLA calls passed in as outside calls |
| Known disease variants | ClinVar (GRCh37), filtered by review stars and population frequency |
| Mother-line | Haplogrep 3 (PhyloTree 17) |
| Father-line | yhaplo |
| Imputation | Beagle 5.5 against 1000 Genomes phase 3 |
| Polygenic scores | PGS Catalog harmonised files, scored with plink2; ancestry-adjusted percentiles with the pgsc_calc "Z_norm2" method on 1000 Genomes PCs |
| HLA | HIBAG |
| Ancestry | Allen Ancient DNA Resource v66, PCA + non-negative mixture models |
| Variant effects | AlphaMissense (hg19) + REVEL v1.3, restricted to genes with well-reviewed disease variants in ClinVar |

The knowledge base that turns genotypes into plain language is in `genomekit/kb/`:

- `markers.py`: curated health and trait markers. Every allele was checked against 1000 Genomes frequencies.
- `pgx.py`: medicine-gene text.
- `pgs.py`: the curated polygenic scores.

## License

genome-kit is licensed under the **[PolyForm Noncommercial License 1.0.0](LICENSE)**. In plain words:

- **Allowed:**
  - personal use, such as analysing your own or your family's DNA;
  - hobby projects, study and non-commercial research;
  - use by charities, schools, universities, public research and health organisations and government bodies;
  - sharing and modifying it for these purposes, as long as you pass on the license and its notices.
- **Not allowed:** any commercial use. That includes selling it or its results, offering it as a paid service, or using it in a business.

For commercial use, contact the copyright holder. This summary is for convenience; the [LICENSE](LICENSE) text is what counts. Use of the software is also subject to [DISCLAIMER.md](DISCLAIMER.md).

The tools and data the kit downloads keep their own licenses:

- PharmCAT: MPL 2.0
- Beagle: GPL 3
- HIBAG: GPL 3
- Haplogrep: MIT
- ClinVar, 1000 Genomes and AADR: public data
- AlphaMissense: CC BY-NC-SA 4.0
- REVEL: free for non-commercial use
- PGS Catalog scores: per-score licenses

genome-kit is research and education software. It is not a medical device, and its results are not a medical diagnosis. Always talk to a doctor or other medical professional about your health.
