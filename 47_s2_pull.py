# -*- coding: utf-8 -*-
"""
Semantic Scholar bulk search 全量拉取（等效替代 OpenAlex 配额阻塞）
查询与论文英文检索式等效：+laboratory +(university|college|"higher education") +(safety|accident|risk|hazard|management)
输出 outputs/bibliometric_openalex/records/s2_records.jsonl
"""
import json
import os
import subprocess
import time

OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "outputs", "bibliometric_openalex", "records"))
os.makedirs(OUT, exist_ok=True)
PROG = os.path.join(OUT, "s2_progress.json")
QUERY = '+laboratory +(university | college | "higher education") +(safety | accident | risk | hazard | management)'
BASE = "https://api.semanticscholar.org/graph/v1/paper/search/bulk"
FIELDS = "title,year,abstract,venue,authors,externalIds,publicationTypes,publicationDate"


def fetch(token, retries=8):
    q = f"query={QUERY}&fields={FIELDS}&limit=1000&year=2000-2026"
    if token:
        q += f"&token={token}"
    url = BASE + "?" + q.replace(" ", "%20").replace("|", "%7C").replace("+", "%2B").replace('"', "%22")
    for i in range(retries):
        r = subprocess.run(["curl", "-s", "--max-time", "90", url], capture_output=True, timeout=100)
        try:
            d = json.loads(r.stdout.decode("utf-8"))
        except Exception:
            d = None
        if d and "data" in d:
            return d
        msg = (r.stdout.decode("utf-8", "ignore"))[:120]
        wait = min(60, 8 * (i + 1))
        print(f"  retry {i+1}: rc={r.returncode} {msg}; sleep {wait}s", flush=True)
        time.sleep(wait)
    raise RuntimeError("s2 fail")


def main():
    token, n = None, 0
    if os.path.exists(PROG):
        pr = json.load(open(PROG))
        token, n = pr.get("token"), pr.get("n", 0)
        print("resume from", n, flush=True)
    mode = "a" if token else "w"
    f = open(os.path.join(OUT, "s2_records.jsonl"), mode, encoding="utf-8")
    while True:
        d = fetch(token)
        for w in d["data"]:
            f.write(json.dumps({
                "id": "s2:" + w["paperId"], "year": w.get("year"), "title": w.get("title") or "",
                "journal": w.get("venue") or "",
                "a1": (w.get("authors") or [{}])[0].get("name", "") if w.get("authors") else "",
                "kw": [], "abstract": w.get("abstract") or "",
                "type": ";".join(w.get("publicationTypes") or []),
            }, ensure_ascii=False) + "\n")
        n += len(d["data"])
        token = d.get("token")
        print(f"  {n}/{d.get('total')}", flush=True)
        json.dump({"token": token, "n": n}, open(PROG, "w"))
        f.flush()
        if not token or not d["data"]:
            break
        time.sleep(1.2)
    f.close()
    print("DONE", n, flush=True)


if __name__ == "__main__":
    main()
