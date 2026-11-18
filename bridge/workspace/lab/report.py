"""Refresh the measured fields in the contest notes after a full verification."""
import argparse
from collections import defaultdict
import json
from pathlib import Path

from verify import verify


def measurements():
    buckets = defaultdict(set)
    passing = defaultdict(dict)
    for path in Path("archive/log").glob("*.jsonl"):
        with path.open(encoding="utf-8") as lines:
            for line in lines:
                row = json.loads(line)
                level, ts = str(row["level"]), row["ts"]
                buckets[level].add(int(ts // 5))
                if row["official"] and row["ok"] and not row["sab"]:
                    key = (level, row["design"])
                    previous = passing[key].get(row["official"], ts)
                    passing[key][row["official"]] = min(previous, ts)
    return buckets, passing


def section(text, name, content):
    start, end = f"<!-- {name}:start -->", f"<!-- {name}:end -->"
    first, body = text.split(start, 1)
    _, last = body.split(end, 1)
    return first + start + "\n" + content + "\n" + end + last


def update(start_epoch):
    data, passed = verify()
    if not passed:
        raise SystemExit("存在未通过场景，不更新笔记。")
    buckets, runs = measurements()
    table = [
        "| 关卡 | 调试分钟 | 首次全过（分） | 造价 | 各样例最后一辆到达（秒） | 各样例断杆数 |",
        "|---|---:|---:|---:|---|---|",
    ]
    for key in ["1", "2", "3", "4", "5", "6", "final"]:
        samples = data[key]["samples"]
        first = min(max(d.values()) for (k, _), d in runs.items() if k == key and len(d) == len(samples))
        arrivals = " / ".join(f"{max(s['arrivals']):.2f}" for s in samples)
        damage = " / ".join(str(s["bridge_breaks"]) for s in samples)
        name = "决赛桥" if key == "final" else key
        minutes = (first - start_epoch) / 60
        table.append(f"| {name} | {len(buckets[key])/12:.1f} | {minutes:.1f} | {data[key]['cost']:.2f} | {arrivals} | {damage} |")
    duel = data["local_duel"]
    arrival = f"{duel['sab_time']:.2f} 秒完好到达" if duel["sab_arrived"] else "未按时完好到达"
    convoy = "标准车队全到" if duel["convoy_ok"] else "标准车队未全到"
    winner = "桥方胜" if duel["bridge_win"] else "桥方未得分"
    line = (f"本队桥车自测：捣蛋车造价 {duel['sab_cost']:.2f}，质量 {duel['sab_mass']:.2f} kg，"
            f"{arrival}；{convoy}，{winner}。此结果不计入正式交叉对局。")
    notes = Path("submission/notes.md")
    text = section(notes.read_text(encoding="utf-8"), "results", "\n".join(table))
    notes.write_text(section(text, "duel", line), encoding="utf-8")
    print("\n".join(table))
    print(line)


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--start-epoch", type=int, required=True)
    update(cli.parse_args().start_epoch)
