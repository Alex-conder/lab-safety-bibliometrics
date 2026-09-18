# -*- coding: utf-8 -*-
"""
OpenAlex 记录级全量拉取（游标分页 + 断点续传）
输出 outputs/bibliometric_openalex/records/en_records.jsonl（每行一条精简记录）
"""
import json
import os
import time
import urllib.parse
import urllib.request

BASE = "https://api.openalex.org/works"
MAILTO = "lab-safety-biblio@example.org"
OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "outputs", "bibliometric_openalex", "records"))
os.makedirs(OUT, exist_ok=True)
EN_SEARCH = '((university OR college OR "higher education") AND laboratory AND (safety OR accident OR incident OR risk OR hazard OR management))'
FILTER = (f"title_and_abstract.search:{EN_SEARCH},"
          "publication_year:2000-2026,type:article|review,language:en")
FIELDS = "id,publication_year,title,primary_location,authorships,keywords,abstract_inverted_index,type"
PROG = os.path.join(OUT, "pull_progress.json")


def api(params, retries=8):
    import subprocess
    params = dict(params)
    params["mailto"] = MAILTO
    url = BASE + "?" + urllib.parse.urlencode(params)
    for i in range(retries):
        try:
            r = subprocess.run(["curl", "-s", "--max-time", "120", "-A", "lab-safety-biblio/2.0", url],
                               capture_output=True, timeout=140)
            if r.returncode != 0:
                raise RuntimeError(f"curl rc={r.returncode}")
            d = json.loads(r.stdout.decode("utf-8"))
            if "results" not in d:
                raise RuntimeError("bad payload: " + r.stdout.decode("utf-8")[:120])
            return d
        except Exception as e:
            print(f"  retry {i+1}: {e}", flush=True)
            time.sleep(5 * (i + 1))
    raise RuntimeError("api fail")


def abstract_of(w):
    inv = w.get("abstract_inverted_index")
    if not inv:
        return ""
    pos = []
    for word, idxs in inv.items():
        for i in idxs:
            pos.append((i, word))
    return " ".join(w for _, w in sorted(pos))


def slim(w):
    src = None
    pl = w.get("primary_location") or {}
    if pl.get("source"):
        src = pl["source"].get("display_name")
    a1 = ""
    if w.get("authorships"):
        a1 = w["authorships"][0].get("author", {}).get("display_name", "")
    return {
        "id": w["id"], "year": w.get("publication_year"), "title": w.get("title") or "",
        "journal": src, "a1": a1,
        "kw": [k["display_name"] for k in w.get("keywords", [])],
        "abstract": abstract_of(w), "type": w.get("type"),
    }


def main():
    cursor = "*"
    n_done = 0
    if os.path.exists(PROG):
        pr = json.load(open(PROG))
        cursor, n_done = pr["cursor"], pr["n"]
        print(f"resume from {n_done}", flush=True)
    mode = "a" if cursor != "*" else "w"
    f = open(os.path.join(OUT, "en_records.jsonl"), mode, encoding="utf-8")
    total = None
    while True:
        d = api({"filter": FILTER, "per_page": 200, "cursor": cursor, "select": FIELDS})
        if total is None:
            total = d["meta"]["count"]
            print("total:", total, flush=True)
        for w in d["results"]:
            f.write(json.dumps(slim(w), ensure_ascii=False) + "\n")
        n_done += len(d["results"])
        if n_done % 2000 < 200:
            print(f"  {n_done}/{total}", flush=True)
            json.dump({"cursor": cursor, "n": n_done}, open(PROG, "w"))
            f.flush()
        cursor = d["meta"].get("next_cursor")
        if not cursor or not d["results"]:
            break
        time.sleep(0.15)
    f.close()
    json.dump({"cursor": "DONE", "n": n_done}, open(PROG, "w"))
    print("DONE", n_done, flush=True)


if __name__ == "__main__":
    main()
