# modules/scraper.py
import re
from typing import List, Dict, Tuple, Optional

Record = Dict[str, str]

_TIME_RE = re.compile(r'^\d{1,2}:\d{2}$')

def _iso_from_header(html: str) -> str:
    """
    例: <h3><span>令和07年10月04日(土)</span></h3> から ISO (YYYY-MM-DD) を作る。
    取れない場合は "" を返す。
    """
    m = re.search(r'<h3>\s*<span>\s*([^<]+?)\s*</span>\s*</h3>', html)
    if not m:
        return ""
    text = m.group(1)
    # "令和07年10月04日(土)" -> era, yy, mm, dd
    m2 = re.search(r'(令和|平成|昭和)\s*(\d{1,2})年\s*(\d{1,2})月\s*(\d{1,2})日', text)
    if not m2:
        return ""
    era, yy, mm, dd = m2.group(1), int(m2.group(2)), int(m2.group(3)), int(m2.group(4))

    # 和暦→西暦（元年 = base + 1）
    era_base = {"令和": 2018, "平成": 1988, "昭和": 1925}.get(era)
    if not era_base:
        return ""
    yyyy = era_base + yy
    return f"{yyyy:04d}-{mm:02d}-{dd:02d}"

def _iso_from_selectdate(html: str) -> str:
    """ <input type="hidden" name="selectdate" value="YYYYMMDD"> からISOを作る（フォールバック） """
    m = re.search(r'name="selectdate"\s+value="(\d{8})"', html)
    if not m:
        return ""
    ymd = m.group(1)
    return f"{ymd[0:4]}-{ymd[4:6]}-{ymd[6:8]}"

def _pick_iso_date(html: str) -> str:
    """ ヘッダ優先、なければ selectdate をフォールバックに """
    iso = _iso_from_header(html)
    if iso:
        return iso
    return _iso_from_selectdate(html)

def _strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", "", text)
    return text

def _parse_time_label_from_header_fragment(th_html: str) -> Tuple[str, str]:
    """
    <th ...>11:00<br>～<br>13:00</th> などから ("11:00", "13:00")
    """
    txt = _strip_html(th_html)
    if "～" in txt:
        s, e = txt.split("～", 1)
        s, e = s.strip(), e.strip()
        if _TIME_RE.match(s) and _TIME_RE.match(e):
            return s, e
    return "", ""

def _find_header_time_near(html: str, anchor_pos: int, col: int, search_back_chars: int = 8000) -> Tuple[str, str]:
    """
    アンカー位置（施設行の開始付近）から上方向（最大 search_back_chars）へ遡って、
    同じ col の <th id="tdX_col"> ... </th> を最後に見つかったものを採用。
    これにより、ページ内に複数ブロックがあっても、該当ブロックのヘッダーに紐づく。
    """
    start = max(0, anchor_pos - search_back_chars)
    window = html[start:anchor_pos]
    # 最後に出現する該当 th を拾う（右端＝直近）
    pat = re.compile(rf'<th[^>]+id="td(\d+)_{col}"[^>]*>(.*?)</th>', re.DOTALL)
    last_match: Optional[re.Match] = None
    for m in pat.finditer(window):
        last_match = m
    if not last_match:
        return "", ""
    th_html = last_match.group(2)
    return _parse_time_label_from_header_fragment(th_html)

def _iter_facility_rows_with_span(html: str):
    """
    施設見出し行を抽出（マッチ位置も返す）。
    <tr>
      <th ...><strong>施設名</strong><br>部屋名</th>
      ... <td id="td11_2" class="ok"><img alt="O"> ...
    </tr>
    yield: (facility_full_name, row_html, start_pos, end_pos)
    """
    tr_re = re.compile(
        r"(<tr>\s*<th[^>]*>\s*<strong>(?P<n1>[^<]+)</strong>\s*<br\s*/?>(?P<n2>[^<]+)</th>(?P<rest>.*?)</tr>)",
        re.DOTALL
    )
    for m in tr_re.finditer(html):
        facility = (m.group("n1") + " " + m.group("n2")).strip()
        block = m.group(1)           # <tr> ... </tr>（施設行全体）
        row_html = m.group("rest")   # 右側セル部分
        yield facility, row_html, m.start(), m.end()

def _ok_cells(row_html: str) -> List[int]:
    """
    行内の「○」列番号（col）を抽出。
    例: <td id="td11_2" class="ok"><img alt="O"...>
    """
    cols: List[int] = []
    for m in re.finditer(r'<td\s+id="td\d+_(\d+)"[^>]*class="ok"[^>]*>.*?alt="O"', row_html, re.DOTALL):
        cols.append(int(m.group(1)))
    cols.sort()
    return cols

def _merge_ranges(pairs: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
    """
    連続する時間（前のend == 次のstart）を結合。
    入力は col 昇順で対応する (start, end) のリスト。
    """
    out: List[Tuple[str, str]] = []
    cur_s: str = ""
    cur_e: str = ""
    for s, e in pairs:
        if not (s and e):
            continue
        if not cur_s:
            cur_s, cur_e = s, e
            continue
        if cur_e == s:
            cur_e = e
        else:
            out.append((cur_s, cur_e))
            cur_s, cur_e = s, e
    if cur_s:
        out.append((cur_s, cur_e))
    return out

def parse_result_html(html: str) -> List[Record]:
    """
    方針：
      1) 日付はヘッダの和暦→ISOを最優先（なければ selectdate）。
      2) 各施設行ごとに、行のアンカー位置から“直前に出現した同じcolのヘッダー<th id="tdX_col">”を逆探索し、
         そのヘッダーに書かれた "HH:MM～HH:MM" を時刻として採用。
      3) 同一行で連続する枠は time を結合（例: 13:00–15:00 + 15:00–17:00 → 13:00–17:00）。
    """
    date_iso = _pick_iso_date(html)
    out: List[Record] = []

    for facility, row_html, row_start, _row_end in _iter_facility_rows_with_span(html):
        cols = _ok_cells(row_html)
        if not cols:
            continue

        # 各○について、この施設行の開始位置（row_start）より手前で直近のヘッダーを探す
        time_pairs: List[Tuple[str, str]] = []
        for col in cols:
            s, e = _find_header_time_near(html, row_start, col)
            time_pairs.append((s, e))

        # 連続結合
        merged = _merge_ranges(time_pairs)
        for s, e in merged:
            if not (s and e):
                continue
            out.append({
                "date": date_iso,            # ISOで保存（仕様）
                "time": f"{s}–{e}",
                "facility": facility,
            })
    return out
