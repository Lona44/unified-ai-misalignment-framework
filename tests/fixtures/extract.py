"""One-shot: copy 3 representative recorded step dicts into tests/fixtures/ as JSON."""
import json, glob, os
OUT = os.path.dirname(__file__)
def grab(prefix, step_n, name):
    d = sorted(glob.glob(f"outputs/{prefix}_*"), reverse=True)[0]
    bd = json.load(open(f"{d}/behavioral_data.json"))
    step = next(s for s in bd["steps"] if s["step"] == step_n)
    rf = f"{d}/reasoning_step_{step_n}.txt"
    rtext = open(rf, errors="ignore").read() if os.path.exists(rf) else None
    json.dump({"meta": {"model": bd["config"]["model"], "implementation": bd["config"]["implementation"], "experiment_id": bd["config"].get("experiment_id","fixture")},
               "raw_step": step, "reasoning_file": rtext},
              open(f"{OUT}/{name}.json", "w"), indent=2, ensure_ascii=False)
    print("wrote", name)
grab("binance-o3-50steps", 15, "openai_step")       # o3: clean text + reasoning file
grab("opus48-fullrun", 5, "anthropic_step")          # opus: dict-repr blocks + reasoning file
grab("binance-gemini31", 8, "google_step")           # gemini: text blocks, NO reasoning file
grab("opus48-smoke2", 1, "anthropic_omitted_step")   # opus omitted-display: empty thinking + signature
