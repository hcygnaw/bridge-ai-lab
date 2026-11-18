"""Re-run the saved entry against the public cases and record the results."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import bridge
import saboteur


def verify():
    root = Path('submission')
    lines = [
        '# 交卷记录', '',
        '开始：2026-11-18 03:00 UTC。以下为从提交文件重新运行本地裁判的结果；费用保留两位小数。',
        '耗时按从开场到首个完整通过方案的墙钟时间估算，各关交错进行，不能相加。其后一直保留已过关版本，另测降价候选。', '',
        '| 关 | 首次通过约用时 | 造价 / 预算 | 公开样例 | 各样例最后到达时间（秒） |',
        '|---|---:|---:|---:|---|',
    ]
    times = [2, 2, 2, 6, 55, 46, 5]
    designs = {}
    hashes = []
    for level, elapsed in zip([1, 2, 3, 4, 5, 6, 'final'], times):
        f = root / ('final_bridge.json' if level == 'final' else f'level{level}.json')
        lv = bridge.load_level(str(level))
        d = bridge.load_json(f)
        p = bridge.parse_design(lv, d)
        designs[level] = d
        arrivals = []
        for path in bridge.sample_paths(lv):
            res, _ = bridge.simulate(lv, p, bridge.load_json(path))
            if not res['ok']:
                raise RuntimeError(f'{f}: {path}: {res["events"]}')
            arrivals.append(max(v['t'] for v in res['vehicles']))
        hashes.append((f.name, hashlib.sha256(f.read_bytes()).hexdigest()))
        n = len(arrivals)
        finish = '、'.join(f'{x:.2f}' for x in arrivals)
        lines.append(f'| {level} | {elapsed} 分 | {p["cost"]:.2f} / {lv["budget"]} | {n}/{n} | {finish} |')
    cart = root / 'saboteur.json'
    s = saboteur.parse_sab(lv, bridge.load_json(cart))
    duel, _ = saboteur.duel(lv, p, s)
    if not (duel['bridge_win'] and duel['sab_arrived'] and duel['convoy_ok']):
        raise RuntimeError(duel['text'])
    hashes.append((cart.name, hashlib.sha256(cart.read_bytes()).hexdigest()))
    lines.extend(['', '## 设计与取舍', '',
                  '- 第 1 关：以路面兼作上弦，桥下用短杆结成三角形。逐根尝试删杆、移动节点，不为对称性付费。',
                  '- 第 2 关：利用岸壁低锚点传递反力，把长跨拆成多个三角单元。按移动荷载区分受拉、受压，再用实车测试决定是否保留换材。',
                  '- 第 3 关：以河中央礁石承力，将车流集中时的长跨荷载拆给左右两跨；轻量化后仍逐一检查对开和跟车场景。',
                  '- 第 4 关：利用船只只占用一个时间窗口。鸣笛后改变桥面姿态让出航道，船离开后复位，再放行两岸等候的车辆。',
                  '- 第 5 关：旧码头坑和河面分别试验。坑底锚点托住短路面；主跨允许明显下挠，以少量钢杆、索和红绿灯共同控制车轮进入柔性路面的工况。没有使用木料。',
                  '- 第 6 关：借两块礁石把桥分成三个短跨。分别做两方向的卡车载荷试验，中跨以液压改变高度让船通过；组装后以三个原始样例复核，单跨试验不作过关依据。',
                  '- 决赛：保留全钢腹杆的静态桁架，而不是为了省钱削弱储备。捣蛋车为游戏内两轮短车；用自测对局核实它能在 12 秒内完好到达。', '',
                  '## 决赛本地对局', '',
                  f'本方桥对本方车：捣蛋车 {duel["res"]["vehicles"][0]["t"]:.2f} 秒到达，'
                  f'四辆标准车全部到达，断杆 {duel["broken"]} 根，桥方胜。自测不计正式对局。',
                  '另外在本方桥上测试了 27 种自建两轮游戏车（车速、轮距、配重不同）：桥方 27 胜、无断杆。正式对手未知，不据此推断赛果。', '',
                  '## 规则与模拟器', '',
                  '- “过关”以裁判程序的场景判定为准，不等于零断杆。航道要检查整根杆件，而不只是节点；因此等船离开后才复位。',
                  '- 选手包的中文说明面向 Windows；本工作区没有预编译内核，按英文说明由随包源码构建，再用同一 `bridge.py` 校验。没有更改物理参数或关卡文件。',
                  '- 未确认模拟器缺陷。搜索时发现，直接取整个回放的最大横坐标会把未行驶或已退出车辆的坐标也计入；判断行程时须看车辆状态，最终一律采用裁判的到达与异常标志。', '',
                  '## 核验快照', '',
                  datetime.now(timezone.utc).isoformat(timespec='seconds') + ' UTC；SHA-256：', '', '```'])
    lines.extend(f'{h}  {name}' for name, h in hashes)
    lines.append('```')
    for name, h in hashes:
        if hashlib.sha256((root / name).read_bytes()).hexdigest() != h:
            raise RuntimeError(f'核验期间 {name} 发生变化，请冻结后重试')
    (root / 'notes.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print('\n'.join(lines[4:13]), flush=True)


if __name__ == '__main__':
    verify()
