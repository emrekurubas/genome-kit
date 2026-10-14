#!/usr/bin/env bash
# genome-kit launcher: sets up a private, self-contained toolbox (first run only), then starts the interactive
# wizard. Nothing is installed system-wide and no admin rights are needed.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"

case "$(uname -s)-$(uname -m)" in
  Darwin-arm64)  PLAT=osx-arm64 ;;
  Darwin-x86_64) PLAT=osx-64 ;;
  Linux-x86_64)  PLAT=linux-64 ;;
  Linux-aarch64|Linux-arm64) PLAT=linux-aarch64 ;;
  *) echo "Unsupported system: $(uname -s) $(uname -m). On Windows, use run.bat (it runs this script inside WSL)."; exit 1 ;;
esac

# Under WSL with the folder on a Windows drive (/mnt/c/...), keep the toolbox and reference data on the Linux side:
# the Windows file system is slow and does not support everything the tools need. Results still go to this folder.
TOOLS="$HERE/.tools"
if grep -qi microsoft /proc/version 2>/dev/null && [[ "$HERE" == /mnt/* ]]; then
  TOOLS="$HOME/.genome-kit/tools"
  export GENOMEKIT_DATA="${GENOMEKIT_DATA:-$HOME/.genome-kit/data}"
fi
export GENOMEKIT_TOOLS="$TOOLS"

export MAMBA_ROOT_PREFIX="$TOOLS/mamba"
export PIP_ROOT_USER_ACTION=ignore   # under WSL genome-kit runs as root in its own Linux; pip need not warn about that
MM="$TOOLS/bin/micromamba"
ENV="$TOOLS/envs/core"

if [ ! -x "$MM" ]; then
  echo
  echo "First run: setting up the toolbox. This happens once and takes about 5-10 minutes."
  echo "[1/2] Downloading the package manager (about 15 MB)..."
  for t in curl tar; do
    command -v $t >/dev/null || { echo "'$t' is needed. Install it (for example: sudo apt install $t) and run this again."; exit 1; }
  done
  # The download is .tar.bz2. Fresh Ubuntu (26.04) has no bzip2, but it has python3, which can unpack it too.
  if command -v bzip2 >/dev/null; then UNBZ=(bzip2 -dc)
  elif command -v python3 >/dev/null; then UNBZ=(python3 -c 'import bz2, shutil, sys; shutil.copyfileobj(bz2.BZ2File(sys.stdin.buffer), sys.stdout.buffer)')
  else echo "'bzip2' is needed. Install it (for example: sudo apt install bzip2) and run this again."; exit 1; fi
  mkdir -p "$TOOLS"
  curl -fsSL "https://micro.mamba.pm/api/micromamba/$PLAT/latest" | "${UNBZ[@]}" | tar -x -C "$TOOLS" bin/micromamba
fi

# (Re)build the environment when it is missing or environment.yml changed.
STAMP="$ENV/.genomekit-env-stamp"
WANT="$(cksum < environment.yml)"
if [ ! -f "$STAMP" ] || [ "$(cat "$STAMP")" != "$WANT" ]; then
  echo "[2/2] Installing the analysis tools (Python, Java, plink, bcftools; about 1 GB)."
  echo "      You will see download progress below. The questions start right after."
  "$MM" create -y -p "$ENV" -f environment.yml
  echo "Toolbox ready."
  "$MM" clean -a -y -q >/dev/null 2>&1 || true   # drop downloaded package archives
  echo "$WANT" > "$STAMP"
fi

export GENOMEKIT_MAMBA="$MM"
export PATH="$ENV/bin:$ENV/lib/jvm/bin:$PATH"
[ -d "$ENV/lib/jvm" ] && export JAVA_HOME="$ENV/lib/jvm"
exec "$ENV/bin/python" -m genomekit "$@"
