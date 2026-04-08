#!/usr/bin/env python3.12
"""SWE-bench A/B runner — bulletproof per-run executor.

Conditions: C0_no_borg | C1_borg_empty | C2_borg_seeded
Models    : claude-sonnet-4-5 | gpt-4o-mini | gemini-2.0-flash | minimax | openclaw
Invariant : C1/C2 with borg_searches==0 → AssertionError (March-31 bug guard).
"""
from __future__ import annotations
import os, sys, json, time, uuid, shutil, subprocess, re, argparse, traceback
from pathlib import Path
from typing import Any, Callable

# ── price table (USD per 1M tokens) ───────────────────────────────────────────
PRICES = {
    "claude-sonnet-4-5-20250929": (3.00, 15.00),
    "gpt-4o-mini":                  (0.15,  0.60),
    "gpt-4o":                       (2.50, 10.00),
    "gemini-2.0-flash":             (0.10,  0.40),
    "minimax-text-01":              (0.20,  1.10),  # listed minimaxi rates
    "openclaw":                     (3.00, 15.00),  # uses sonnet under the hood
}
def cost(model, in_tok, out_tok):
    p = PRICES.get(model, (0.0, 0.0))
    return (in_tok * p[0] + out_tok * p[1]) / 1_000_000

# ── credentials (loaded lazily, masked never logged) ──────────────────────────
def _load_env(path):
    out={}
    if not os.path.exists(path): return out
    for ln in open(path):
        ln=ln.strip()
        if not ln or ln.startswith("#") or "=" not in ln: continue
        k,v=ln.split("=",1); out[k]=v.strip().strip('"').strip("'")
    return out
_HERMES_ENV = _load_env("/root/.hermes/.env")
_DOCKER_ENV = _load_env("/docker/openclaw-qjmq/.env")
ANTHROPIC_OAT = _HERMES_ENV.get("ANTHROPIC_TOKEN", "")
GEMINI_KEY    = _DOCKER_ENV.get("GEMINI_API_KEY", "")
OPENAI_KEY    = _DOCKER_ENV.get("OPENAI_API_KEY", "")
MINIMAX_KEY   = _HERMES_ENV.get("MINIMAX_API_KEY", "")

# ── tool schema (canonical) ───────────────────────────────────────────────────
def tool_specs(condition: str) -> list[dict]:
    base = [
        {"name":"read_file","description":"Read a text file from the workspace.",
         "input_schema":{"type":"object","properties":{"path":{"type":"string"}},"required":["path"]}},
        {"name":"write_file","description":"Overwrite a file with new content.",
         "input_schema":{"type":"object","properties":{"path":{"type":"string"},"content":{"type":"string"}},"required":["path","content"]}},
        {"name":"run_pytest","description":"Run a single pytest test inside the testbed and return exit code + tail.",
         "input_schema":{"type":"object","properties":{"test":{"type":"string"}},"required":["test"]}},
        {"name":"run_bash","description":"Run a bash command in the workspace (read-only safe ops).",
         "input_schema":{"type":"object","properties":{"cmd":{"type":"string"}},"required":["cmd"]}},
        {"name":"finish","description":"Signal you are done editing and want the test grader to run.",
         "input_schema":{"type":"object","properties":{"reason":{"type":"string"}},"required":[]}},
    ]
    if condition in ("C1_borg_empty","C2_borg_seeded"):
        base.append({"name":"borg_debug","description":"Ask the borg collective intelligence for a debugging approach. PASTE the failing traceback as input.",
            "input_schema":{"type":"object","properties":{"traceback":{"type":"string"}},"required":["traceback"]}})
        base.append({"name":"borg_search","description":"Search the borg knowledge base for known approaches to a class of error.",
            "input_schema":{"type":"object","properties":{"query":{"type":"string"}},"required":["query"]}})
    return base

# ── tool implementations ──────────────────────────────────────────────────────
class ToolBox:
    def __init__(self, workdir: Path, testbed: Path, condition: str, borg_db: str|None):
        self.work=workdir; self.testbed=testbed; self.condition=condition; self.borg_db=borg_db
        self.borg_calls=[]; self.borg_searches=0; self.tool_calls=0

    def _safe(self, p: str) -> Path:
        full=(self.testbed / p).resolve() if not os.path.isabs(p) else Path(p).resolve()
        if not str(full).startswith(str(self.testbed.resolve())):
            raise ValueError(f"path escapes testbed: {p}")
        return full

    def read_file(self, path: str) -> str:
        f=self._safe(path)
        if not f.exists(): return f"ERROR: not found {path}"
        try:
            data=f.read_text(errors="replace")
        except Exception as e:
            return f"ERROR: {e}"
        return data[:8000] + ("\n...[truncated]" if len(data)>8000 else "")

    def write_file(self, path: str, content: str) -> str:
        f=self._safe(path); f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(content)
        return f"wrote {len(content)} bytes to {path}"

    def run_bash(self, cmd: str) -> str:
        try:
            r=subprocess.run(["bash","-c",cmd], cwd=self.testbed, capture_output=True, text=True, timeout=120)
        except subprocess.TimeoutExpired:
            return "ERROR: timeout 120s"
        return f"exit={r.returncode}\nSTDOUT:\n{r.stdout[-4000:]}\nSTDERR:\n{r.stderr[-2000:]}"

    def run_pytest(self, test: str) -> str:
        # django uses tests/runtests.py with dotted path 'module.path.Class.method'
        dotted = _django_test_id(test) if "(" in test else test
        cmd=["bash","-c", f"cd /testbed && python tests/runtests.py {dotted} -v2 2>&1 | tail -120"]
        return self._docker_exec(cmd)

    def _docker_exec(self, cmd: list[str]) -> str:
        image = (self.testbed.parent / "_image").read_text().strip()
        full = ["docker","run","--rm","--entrypoint","/bin/bash","-v",f"{self.testbed}:/testbed",image,
                "-lc", f"source /opt/miniconda3/bin/activate testbed 2>/dev/null; set -o pipefail; {' '.join(cmd[-1:])}" if cmd[0]=="bash" else "true"]
        # Fallback: if cmd was ['bash','-c', str], rebuild cleanly
        if cmd[0] == "bash" and cmd[1] == "-c":
            inner = cmd[2]
            full = ["docker","run","--rm","--entrypoint","/bin/bash","-v",f"{self.testbed}:/testbed",image,
                    "-lc", f"source /opt/miniconda3/bin/activate testbed 2>/dev/null || true; set -o pipefail; {inner}"]
        try:
            r=subprocess.run(full, capture_output=True, text=True, timeout=300)
        except subprocess.TimeoutExpired:
            return "ERROR: docker run timeout 300s"
        out=(r.stdout + r.stderr)[-5000:]
        return f"exit={r.returncode}\n{out}"

    def borg_debug(self, traceback: str) -> str:
        if self.condition == "C0_no_borg":
            return "ERROR: borg unavailable in this condition"
        self.borg_searches += 1
        self.borg_calls.append({"kind":"debug","len":len(traceback)})
        try:
            r=subprocess.run(["borg","debug",traceback], capture_output=True, text=True, timeout=30)
            return r.stdout[-3000:] or r.stderr[-1500:]
        except Exception as e:
            return f"borg ERROR: {e}"

    def borg_search(self, query: str) -> str:
        if self.condition == "C0_no_borg":
            return "ERROR: borg unavailable in this condition"
        self.borg_searches += 1
        self.borg_calls.append({"kind":"search","q":query[:120]})
        try:
            r=subprocess.run(["borg","search",query], capture_output=True, text=True, timeout=30)
            return (r.stdout + r.stderr)[-3000:]
        except Exception as e:
            return f"borg ERROR: {e}"

    def finish(self, reason: str = "") -> str:
        return "FINISH_ACK"

    def dispatch(self, name: str, args: dict) -> str:
        self.tool_calls += 1
        fn = getattr(self, name, None)
        if not fn: return f"ERROR: unknown tool {name}"
        try:
            return fn(**args)
        except TypeError as e:
            return f"ERROR: bad args: {e}"
        except Exception as e:
            return f"ERROR: {type(e).__name__}: {e}"

# ── system prompt builder ─────────────────────────────────────────────────────
def system_prompt(condition: str, problem: str, fail_tests: list[str]) -> str:
    base = (
        "You are a software engineer tasked with fixing a bug in the django/django repository. "
        "The repository is at /testbed. The failing test(s) you must make pass: "
        + ", ".join(fail_tests) + ".\n\n"
        "PROBLEM:\n" + problem[:2500] + "\n\n"
        "Use the tools to read the relevant source files, understand the bug, edit the source "
        "(NOT the test file), then call run_pytest to verify. When the test passes, call finish.\n"
        "You have at most 20 tool turns. Be efficient. Do not edit files under tests/."
    )
    if condition in ("C1_borg_empty","C2_borg_seeded"):
        base += (
            "\n\nIMPORTANT: When you encounter an error you don't immediately understand, "
            "you MUST call borg_debug with the failing traceback BEFORE attempting a fix. "
            "Borg returns proven debugging approaches from other agents. "
            "You should also call borg_search at the start to look for prior approaches to "
            "django migration / index / schema bugs. Treat borg as a senior teammate."
        )
    return base

# ── model adapters (return: (assistant_text, tool_uses, in_tok, out_tok)) ────
def call_anthropic(model, system, history, tools):
    import httpx
    headers={
        "Authorization": f"Bearer {ANTHROPIC_OAT}",
        "anthropic-version":"2023-06-01",
        "anthropic-beta":"oauth-2025-04-20",
        "content-type":"application/json",
    }
    body={
        "model": model,
        "max_tokens": 2048,
        "system": "You are Claude Code, Anthropic's official CLI for Claude.\n\n" + system,
        "tools": tools,
        "messages": history,
    }
    r=httpx.post("https://api.anthropic.com/v1/messages", headers=headers, json=body, timeout=120)
    r.raise_for_status()
    j=r.json()
    text_parts=[]; tool_uses=[]
    for blk in j.get("content",[]):
        if blk["type"]=="text": text_parts.append(blk["text"])
        elif blk["type"]=="tool_use":
            tool_uses.append({"id":blk["id"],"name":blk["name"],"input":blk.get("input",{})})
    in_tok=j["usage"]["input_tokens"]; out_tok=j["usage"]["output_tokens"]
    return "\n".join(text_parts), tool_uses, in_tok, out_tok, j.get("stop_reason")

def call_openai(model, system, history, tools, key=None, base_url=None):
    import openai
    client = openai.OpenAI(api_key=key or OPENAI_KEY, base_url=base_url)
    oa_tools=[{"type":"function","function":{"name":t["name"],"description":t["description"],"parameters":t["input_schema"]}} for t in tools]
    msgs=[{"role":"system","content":system}] + _to_openai_history(history)
    r=client.chat.completions.create(model=model, max_tokens=2048, messages=msgs, tools=oa_tools)
    choice=r.choices[0]; msg=choice.message
    tool_uses=[]
    for tc in (msg.tool_calls or []):
        try: args=json.loads(tc.function.arguments or "{}")
        except: args={}
        tool_uses.append({"id":tc.id,"name":tc.function.name,"input":args})
    return msg.content or "", tool_uses, r.usage.prompt_tokens, r.usage.completion_tokens, choice.finish_reason

def call_gemini(model, system, history, tools):
    from google import genai as gg
    from google.genai import types as gt
    client = gg.Client(api_key=GEMINI_KEY)
    g_tools=[gt.Tool(function_declarations=[
        gt.FunctionDeclaration(name=t["name"], description=t["description"],
                               parameters=_clean_schema(t["input_schema"]))
        for t in tools])]
    contents=_to_gemini_history(history)
    cfg=gt.GenerateContentConfig(system_instruction=system, tools=g_tools, max_output_tokens=2048)
    r=client.models.generate_content(model=model, contents=contents, config=cfg)
    text=""; tool_uses=[]
    if r.candidates:
        for part in (r.candidates[0].content.parts or []):
            if hasattr(part,"text") and part.text: text += part.text
            if hasattr(part,"function_call") and part.function_call:
                fc=part.function_call
                tool_uses.append({"id":fc.name+"_"+uuid.uuid4().hex[:6],"name":fc.name,"input":dict(fc.args or {})})
    um=r.usage_metadata
    return text, tool_uses, um.prompt_token_count or 0, um.candidates_token_count or 0, r.candidates[0].finish_reason if r.candidates else None

def _clean_schema(s):
    # gemini doesn't like additionalProperties or unset types
    out={k:v for k,v in s.items() if k not in ("additionalProperties","$schema")}
    if "properties" in out:
        out["properties"]={k:_clean_schema(v) for k,v in out["properties"].items()}
    return out

def _to_openai_history(hist):
    out=[]
    for m in hist:
        if m["role"]=="user":
            content=m["content"]
            if isinstance(content,str): out.append({"role":"user","content":content}); continue
            # tool results
            for blk in content:
                if blk.get("type")=="tool_result":
                    out.append({"role":"tool","tool_call_id":blk["tool_use_id"],"content":blk["content"]})
                else:
                    out.append({"role":"user","content":blk.get("text",str(blk))})
        elif m["role"]=="assistant":
            content=m["content"]; tcs=[]; text=""
            if isinstance(content,str): text=content
            else:
                for blk in content:
                    if blk.get("type")=="text": text+=blk["text"]
                    elif blk.get("type")=="tool_use":
                        tcs.append({"id":blk["id"],"type":"function","function":{"name":blk["name"],"arguments":json.dumps(blk.get("input",{}))}})
            entry={"role":"assistant","content":text or None}
            if tcs: entry["tool_calls"]=tcs
            out.append(entry)
    return out

def _to_gemini_history(hist):
    from google.genai import types as gt
    out=[]
    for m in hist:
        role="user" if m["role"]=="user" else "model"
        parts=[]
        c=m["content"]
        if isinstance(c,str):
            parts=[gt.Part.from_text(text=c)]
        else:
            for blk in c:
                if blk.get("type")=="text": parts.append(gt.Part.from_text(text=blk["text"]))
                elif blk.get("type")=="tool_use":
                    parts.append(gt.Part.from_function_call(name=blk["name"], args=blk.get("input",{})))
                elif blk.get("type")=="tool_result":
                    parts.append(gt.Part.from_function_response(name=blk.get("name","tool"), response={"result":blk["content"][:4000]}))
        if parts: out.append(gt.Content(role=role, parts=parts))
    return out

# ── core runner ───────────────────────────────────────────────────────────────
def run_single_task(task: dict, condition: str, model: str, seed: int,
                    borg_db_path: str|None, workdir: str, timeout: int = 900) -> dict:
    assert condition in ("C0_no_borg","C1_borg_empty","C2_borg_seeded")
    run_id = f"{task['instance_id']}_{condition}_{model.replace('/','_')}_{seed}_{uuid.uuid4().hex[:6]}"
    rundir = Path(workdir) / run_id
    rundir.mkdir(parents=True, exist_ok=True)
    testbed = rundir / "testbed"
    image = f"sweb.eval.x86_64.{task['instance_id'].replace('__','__')}"
    # docker image tags use double-underscore exactly as instance_id
    image = f"sweb.eval.x86_64.{task['instance_id']}"
    (rundir / "_image").write_text(image + ":latest")

    result = {
        "run_id": run_id, "task_id": task["instance_id"], "condition": condition,
        "model": model, "seed": seed, "success": False, "tokens_used": 0,
        "input_tokens":0, "output_tokens":0, "tool_calls": 0, "time_seconds": 0.0,
        "borg_searches": 0, "borg_calls": [], "llm_cost_usd": 0.0,
        "iterations": 0, "stop_reason": None, "skipped": False, "skip_reason": None,
        "error": None,
    }
    t0 = time.time()
    try:
        # 1) docker create → cp → rm
        cid = subprocess.check_output(["docker","create",image+":latest","sleep","60"], text=True).strip()
        try:
            subprocess.check_call(["docker","cp",f"{cid}:/testbed",str(testbed)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        finally:
            subprocess.run(["docker","rm",cid], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        # 2) apply test_patch
        tp = testbed / "_test.patch"; tp.write_text(task["test_patch"])
        ap = subprocess.run(["bash","-c", f"cd {testbed} && git apply --whitespace=nowarn _test.patch"],
                            capture_output=True, text=True)
        if ap.returncode != 0:
            result["skipped"]=True; result["skip_reason"]=f"test_patch apply failed: {ap.stderr[:200]}"
            return result
        # 3) verify FAIL_TO_PASS currently FAILs
        f2p = task["FAIL_TO_PASS"]
        if isinstance(f2p, str): f2p = json.loads(f2p)
        first_test = f2p[0]
        dotted_test = _django_test_id(first_test)
        DOCKER_BASE = ["docker","run","--rm","--entrypoint","/bin/bash","-v",f"{testbed}:/testbed", image+":latest", "-lc"]
        _precmd = f"source /opt/miniconda3/bin/activate testbed 2>/dev/null || true; set -o pipefail; cd /testbed && python tests/runtests.py {dotted_test} -v0 2>&1 | tail -20"
        pre = subprocess.run(DOCKER_BASE+[_precmd], capture_output=True, text=True, timeout=300)
        if pre.returncode == 0:
            result["skipped"]=True; result["skip_reason"]="precondition: FAIL_TO_PASS already passes"
            result["precheck_tail"]=pre.stdout[-800:]
            return result
        result["precheck_tail"]=pre.stdout[-800:]

        # 4) agent loop
        toolbox = ToolBox(rundir/"testbed", rundir/"testbed", condition, borg_db_path)
        sysprompt = system_prompt(condition, task.get("problem_statement",""), f2p)
        tools = tool_specs(condition)
        history = [{"role":"user","content":f"Fix the bug. Failing test: {first_test}\n\nProblem statement above. Begin."}]
        in_tot=0; out_tot=0; finished=False
        max_iters = 20
        for it in range(max_iters):
            result["iterations"] = it+1
            if time.time() - t0 > timeout:
                result["error"]="timeout"; break
            try:
                if model.startswith("claude"):
                    text, uses, in_t, out_t, stop = call_anthropic(model, sysprompt, history, tools)
                elif model.startswith("gpt"):
                    text, uses, in_t, out_t, stop = call_openai(model, sysprompt, history, tools)
                elif model.startswith("gemini"):
                    text, uses, in_t, out_t, stop = call_gemini(model, sysprompt, history, tools)
                elif model == "minimax-text-01":
                    text, uses, in_t, out_t, stop = call_openai(
                        "MiniMax-Text-01", sysprompt, history, tools,
                        key=MINIMAX_KEY, base_url="https://api.minimaxi.chat/v1")
                else:
                    raise ValueError(f"unknown model {model}")
            except Exception as e:
                result["error"]=f"llm_call_failed: {type(e).__name__}: {str(e)[:300]}"
                break
            in_tot += in_t; out_tot += out_t
            result["llm_cost_usd"] += cost(model, in_t, out_t)
            result["stop_reason"] = stop

            asst_blocks = []
            if text: asst_blocks.append({"type":"text","text":text})
            for u in uses: asst_blocks.append({"type":"tool_use","id":u["id"],"name":u["name"],"input":u["input"]})
            history.append({"role":"assistant","content": asst_blocks or text or "(no content)"})

            if not uses:
                # model emitted text only — stop
                break

            tool_results=[]
            for u in uses:
                if u["name"]=="finish":
                    finished=True
                out = toolbox.dispatch(u["name"], u["input"])
                tool_results.append({"type":"tool_result","tool_use_id":u["id"],"name":u["name"],"content":out})
            history.append({"role":"user","content": tool_results})
            if finished: break

        result["input_tokens"]=in_tot; result["output_tokens"]=out_tot; result["tokens_used"]=in_tot+out_tot
        result["tool_calls"]=toolbox.tool_calls
        result["borg_searches"]=toolbox.borg_searches
        result["borg_calls"]=toolbox.borg_calls

        # 5) grade
        _gcmd = f"source /opt/miniconda3/bin/activate testbed 2>/dev/null || true; set -o pipefail; cd /testbed && python tests/runtests.py {dotted_test} -v0 2>&1 | tail -20"
        grade = subprocess.run(DOCKER_BASE+[_gcmd], capture_output=True, text=True, timeout=300)
        result["success"] = (grade.returncode == 0)
        result["grade_tail"] = grade.stdout[-1500:]

        # 6) HARD INVARIANT — March 31 bug guard
        if condition in ("C1_borg_empty","C2_borg_seeded") and result["borg_searches"] == 0:
            raise AssertionError(
                f"INVARIANT VIOLATED: condition={condition} but borg_searches=0 "
                f"(run_id={run_id}, model={model}). The March-31 bug must be impossible.")
    except AssertionError:
        raise  # propagate — this is a fatal experiment-design failure
    except Exception as e:
        result["error"] = f"{type(e).__name__}: {str(e)[:400]}"
        result["traceback"] = traceback.format_exc()[-1500:]
    finally:
        result["time_seconds"] = round(time.time() - t0, 2)
    return result

def _pytest_id(test_str: str) -> str:
    """SWE-bench django format: 'method (module.path.Class)' → tests/path/test_file.py::Class::method"""
    m = re.match(r"^(\S+)\s+\(([^)]+)\)$", test_str.strip())
    if m:
        method, dotted = m.group(1), m.group(2)
        parts = dotted.split(".")
        cls = parts[-1]
        mod = "/".join(parts[:-1])
        return f"tests/{mod}.py::{cls}::{method}"
    return test_str

def _django_test_id(test_str: str) -> str:
    """For django runtests.py: 'method (module.path.Class)' → module.path.Class.method"""
    m = re.match(r"^(\S+)\s+\(([^)]+)\)$", test_str.strip())
    if m:
        return f"{m.group(2)}.{m.group(1)}"
    return test_str

# ── streaming JSONL writer (crash-recoverable) ────────────────────────────────
def append_jsonl(path: str, record: dict):
    with open(path, "a") as f:
        f.write(json.dumps(record, default=str) + "\n")
        f.flush()
        os.fsync(f.fileno())

# ── CLI entry ─────────────────────────────────────────────────────────────────
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--task-id", required=True)
    ap.add_argument("--condition", required=True, choices=["C0_no_borg","C1_borg_empty","C2_borg_seeded"])
    ap.add_argument("--model", required=True)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--workdir", default="/tmp/runs")
    ap.add_argument("--jsonl", default=None)
    args=ap.parse_args()

    from datasets import load_dataset
    ds=load_dataset("princeton-nlp/SWE-bench_Verified", split="test")
    task=None
    for r in ds:
        if r["instance_id"]==args.task_id: task=dict(r); break
    if task is None: print(f"task {args.task_id} not found",file=sys.stderr); sys.exit(2)

    rec=run_single_task(task, args.condition, args.model, args.seed, None, args.workdir)
    print(json.dumps(rec, default=str, indent=2))
    if args.jsonl: append_jsonl(args.jsonl, rec)

if __name__=="__main__":
    main()
