# Install Borg without installing the wrong Borg

Borg is the product name. The package you install is **`agent-borg`**.

- Install package: `agent-borg`
- CLI command after install: `borg`
- MCP server command after install: `borg-mcp`
- Doctor command after install: `borg-doctor`

Do **not** install these for Borg:

- `pip install borg` — wrong PyPI package.
- `brew install borgbackup` — BorgBackup, unrelated backup software.
- `apt install borgbackup` / `apt-get install borgbackup` — BorgBackup, unrelated backup software.
- `dnf install borgbackup` — BorgBackup, unrelated backup software.
- `pacman -S borg` — Arch BorgBackup package, unrelated to this project.

Requires Python 3.10+.

---

## macOS

Recommended Homebrew path:

```bash
python3 --version  # must be 3.10+
brew install pipx
pipx ensurepath
pipx install agent-borg
exec "$SHELL" -l

command -v borg
command -v borg-mcp
borg version
borg-doctor --json
```

If you do not use Homebrew:

```bash
python3 -m pip install --user pipx
python3 -m pipx ensurepath
python3 -m pipx install agent-borg
exec "$SHELL" -l

command -v borg
command -v borg-mcp
borg version
borg-doctor --json
```

If `borg` is still not found, open a brand-new terminal window and run:

```bash
command -v borg
command -v borg-mcp
```

Do **not** run `brew install borgbackup`; that installs unrelated backup software.

---

## Linux

### Debian / Ubuntu

```bash
python3 --version  # must be 3.10+
sudo apt update
sudo apt install -y pipx
pipx ensurepath
pipx install agent-borg
exec "$SHELL" -l

command -v borg
command -v borg-mcp
borg version
borg-doctor --json
```

Do **not** run `apt install borgbackup` or `apt-get install borgbackup`; those install unrelated backup software.

### Fedora / RHEL

```bash
python3 --version  # must be 3.10+
sudo dnf install -y pipx
pipx ensurepath
pipx install agent-borg
exec "$SHELL" -l

command -v borg
command -v borg-mcp
borg version
borg-doctor --json
```

Do **not** run `dnf install borgbackup`; that installs unrelated backup software.

### Arch

```bash
python --version  # must be 3.10+
sudo pacman -Syu --needed python-pipx
pipx ensurepath
pipx install agent-borg
exec "$SHELL" -l

command -v borg
command -v borg-mcp
borg version
borg-doctor --json
```

Do **not** run `pacman -S borg`; that installs BorgBackup, not this project.

### Generic Linux fallback

Use this only if your distro does not package `pipx`:

```bash
python3 -m pip install --user pipx
python3 -m pipx ensurepath
python3 -m pipx install agent-borg
exec "$SHELL" -l

command -v borg
command -v borg-mcp
borg version
borg-doctor --json
```

If this fails with an “externally managed environment” error, install `pipx` through your OS package manager instead.

---

## Windows PowerShell

```powershell
py -3 --version  # must be 3.10+
py -m pip install --user pipx
py -m pipx ensurepath
py -m pipx install agent-borg
```

Close and reopen PowerShell, then verify:

```powershell
where.exe borg
where.exe borg-mcp
borg version
borg-doctor --json
```

If `py` is not available, replace `py` with `python`:

```powershell
python -m pip install --user pipx
python -m pipx ensurepath
python -m pipx install agent-borg
```

Use `where.exe`, not PowerShell's `where` alias.

---

## After install: first value check

```bash
borg rescue "ModuleNotFoundError: No module named flask"
```

Expected output shape:

```text
ACTION: what to try next
STOP: what dead-end to avoid
VERIFY: exact check to rerun
CONFIDENCE: tested / observed / inferred / NO_CONFIDENT_MATCH
```

---

## Connect Claude Code

Run this only after `borg version` and `borg-doctor --json` pass:

```bash
borg setup-claude --scope user --verify --fix
```

Expected output includes:

```text
Verify: PASS (initialize handshake ok)
```

Then fully quit and restart Claude Code. In the new session, ask:

```text
what MCP tools do you have from Borg?
```

Expected: Claude lists Borg tools such as `borg_rescue`, `borg_observe`, and `borg_search`, or `/mcp list` shows a `borg` server.

---

## If something went wrong

### `borg` not found

1. Open a brand-new terminal / PowerShell window.
2. Run the PATH check for your OS:
   - macOS/Linux: `command -v borg && command -v borg-mcp`
   - Windows: `where.exe borg` and `where.exe borg-mcp`
3. Rerun `pipx ensurepath` or `python3 -m pipx ensurepath` / `py -m pipx ensurepath`.
4. Reinstall with `pipx install --force agent-borg` if the install was interrupted.

### The wrong `borg` is on PATH

If `borg version` mentions BorgBackup or anything other than `borg 3.x.x`, remove the unrelated package and reinstall `agent-borg` with pipx.

### Claude Code says `borg not found`

1. Confirm `borg version` works in a normal terminal.
2. Rerun `borg setup-claude --scope user --verify --fix`.
3. Fully quit and restart Claude Code so it reloads PATH and MCP config.
4. Ask Claude Code: `what MCP tools do you have from Borg?`
