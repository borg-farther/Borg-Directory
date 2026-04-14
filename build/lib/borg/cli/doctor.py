"""
borg doctor  verify your Borg installation is working.
Run: python3 -m borg.cli.doctor
"""
import sys, os, sqlite3
from pathlib import Path

def run():
    borg_home = Path(os.environ.get('BORG_HOME', '~/.borg')).expanduser()
    ok = True
    print("\n")
    print("         BORG DOCTOR                  ")
    print("\n")

    # 1. DB  trigger seeding if empty/missing, then report
    db_path = borg_home / 'traces.db'
    if not db_path.exists() or sqlite3.connect(str(db_path)).execute("SELECT COUNT(*) FROM traces").fetchone()[0] == 0:
        # Seed by calling borg_observe
        try:
            from borg.integrations.mcp_server import borg_observe as _bo
            _bo(task='Docker apt-get install fails', context='')
        except Exception as _se:
            print(f"    Seeding failed: {_se}")
    if db_path.exists():
        db = sqlite3.connect(str(db_path))
        total = db.execute("SELECT COUNT(*) FROM traces").fetchone()[0]
        techs = db.execute("SELECT COUNT(DISTINCT technology) FROM traces").fetchone()[0]
        db.close()
        if total > 0:
            print(f"   DB: {total} traces across {techs} domains ({db_path})")
        else:
            print(f"   DB: empty  seeding failed")
            ok = False
    else:
        print(f"   DB: not found at {db_path}")
        ok = False

    # 2. borg_observe
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        from borg.integrations.mcp_server import borg_observe
        r = borg_observe(task='Docker apt-get package not found', context='')
        action = next((l for l in r.split('\n') if l.startswith('ACTION:')), None)
        conf   = next((l for l in r.split('\n') if 'BORG [' in l), '')
        ok_obs = bool(action and 'HIGH' in conf)
        print(f"  {'' if ok_obs else ''} borg_observe: {(action or 'NO ACTION')[:60]}")
        if not ok_obs: ok = False
    except Exception as e:
        print(f"   borg_observe: {e}")
        ok = False

    # 3. Short form
    try:
        short = borg_observe(task='Docker apt-get package not found', context='', short=True)
        short_ok = 'ACTION:' in short and len(short) < 300
        print(f"  {'' if short_ok else ''} short form: {len(short)} chars")
        if not short_ok: ok = False
    except Exception as e:
        print(f"   short form: {e}")
        ok = False

    # 4. borg_rate
    try:
        from borg.integrations.mcp_server import borg_rate
        borg_observe(task='Django migration error', context='')
        rate = borg_rate(helpful=True)
        rate_ok = 'recorded' in rate.lower()
        print(f"  {'' if rate_ok else ''} borg_rate: {rate[:55]}")
        if not rate_ok: ok = False
    except Exception as e:
        print(f"   borg_rate: {e}")
        ok = False

    # 5. MCP stdio
    try:
        import subprocess, json as _json
        msg = '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"doctor","version":"1.0"}}}'
        result = subprocess.run(
            [sys.executable, '-m', 'borg.integrations.mcp_server'],
            input=msg, capture_output=True, text=True, timeout=5,
            cwd=str(Path(__file__).parent.parent.parent)
        )
        mcp_ok = '"result"' in result.stdout
        print(f"  {'' if mcp_ok else ''} MCP stdio: {'responds to initialize' if mcp_ok else 'FAILED'}")
        if not mcp_ok: ok = False
    except Exception as e:
        print(f"   MCP stdio: {e}")
        ok = False

    print()
    if ok:
        print("   ALL CHECKS PASSED  Borg is ready")
    else:
        print("   SOME CHECKS FAILED  see above")
    print()
    return 0 if ok else 1

if __name__ == '__main__':
    sys.exit(run())
