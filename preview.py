"""
설정 및 좌석 현황 미리보기

config.yaml + seatlist.csv를 읽어 다음을 출력합니다:
  1. 좌석 현황: 열람실별 / 좌석타입별 / 상태별 좌석 수
  2. 좌석 중복 검증: 동일 (열람실, 좌석번호) 중복 여부
  3. 사물함 매핑: 열람실 → 사물함 위치/번호 범위

결과는 콘솔에 출력되고 config_preview.txt로 저장됩니다.

사용법: python preview.py
"""

import csv
import re
import unicodedata
from collections import defaultdict

from config import load_config


# ============================================================
# 한글 정렬 유틸리티
# ============================================================

def display_width(text):
    """문자열의 터미널 표시 폭을 계산합니다 (한글=2칸, 영문/숫자=1칸)."""
    width = 0
    for ch in str(text):
        if unicodedata.east_asian_width(ch) in ('F', 'W'):
            width += 2
        else:
            width += 1
    return width


def pad(text, target_width, align='left'):
    """한글 포함 문자열을 target_width 폭에 맞춰 공백 패딩합니다."""
    text = str(text)
    current = display_width(text)
    padding = max(0, target_width - current)
    if align == 'left':
        return text + ' ' * padding
    else:
        return ' ' * padding + text


# ============================================================
# 1. 좌석 현황
# ============================================================

def generate_seat_summary(config):
    """seatlist.csv를 읽어 열람실별 좌석 현황 표를 생성합니다."""
    paths = config['paths']
    laptop_zones = set(config.get('laptop_not_allowed_zones', []))

    with open(paths['input_seats'], mode='rt', encoding='UTF-8') as f:
        reader = csv.reader(f)
        next(reader)  # 헤더 건너뛰기
        rows = [row for row in reader if len(row) >= 4]

    # 집계: (열람실, 좌석타입, 상태) → 좌석 수
    counts = defaultdict(int)  # (room, grade, status) → count
    rooms_order = []  # 등장 순서 유지
    rooms_seen = set()
    grades_seen = set()
    statuses_seen = set()

    for row in rows:
        grade, room, seat_num, status = row[0], row[1], row[2], row[3]
        counts[(room, grade, status)] += 1
        grades_seen.add(grade)
        statuses_seen.add(status)
        if room not in rooms_seen:
            rooms_seen.add(room)
            rooms_order.append(room)

    grades = sorted(grades_seen)
    statuses = sorted(statuses_seen, key=lambda s: (s != 'open', s))  # open 먼저

    # 칸막이 → 평상 순으로 정렬 (같은 유형 내에서는 등장 순서 유지)
    def room_sort_key(room_name):
        m = re.search(r'\(([^)]+)\)', room_name)
        room_type = m.group(1) if m else ""
        # 칸막이=0, 평상=1, 기타=2
        type_order = 0 if room_type == "칸막이" else (1 if room_type == "평상" else 2)
        return (type_order, rooms_order.index(room_name))

    rooms_sorted = sorted(rooms_order, key=room_sort_key)

    # 열 폭 계산
    COL_ROOM = 22
    COL_NUM = 7

    lines = []
    lines.append("=" * 60)
    lines.append("좌석 현황 (seatlist.csv 기준)")
    lines.append("=" * 60)
    lines.append("")

    # 상태별로 각각 표 생성
    for status in statuses:
        status_label = "배정 대상 (open)" if status == "open" else f"비배정 ({status})"
        lines.append(f"[ {status_label} ]")

        # 헤더
        header = pad("열람실", COL_ROOM)
        for g in grades:
            header += " " + pad(g, COL_NUM, 'right')
        header += " " + pad("합계", COL_NUM, 'right')
        lines.append(header)
        lines.append("-" * display_width(header))

        # 열람실을 좌석 유형별로 분류 (괄호 안 텍스트 기준)
        def get_room_type(room_name):
            m = re.search(r'\(([^)]+)\)', room_name)
            return m.group(1) if m else ""

        type_groups = []  # [(type_label, [rooms])]
        current_type = None
        current_rooms = []
        for room in rooms_sorted:
            # 이 상태에 좌석이 있는 열람실만 포함
            room_total = sum(counts.get((room, g, status), 0) for g in grades)
            if room_total == 0:
                continue
            rt = get_room_type(room)
            if rt != current_type:
                if current_rooms:
                    type_groups.append((current_type, current_rooms))
                current_type = rt
                current_rooms = [room]
            else:
                current_rooms.append(room)
        if current_rooms:
            type_groups.append((current_type, current_rooms))

        # 행 출력 (그룹별 소계 포함)
        grand_totals = defaultdict(int)
        grand_total = 0
        separator = "-" * display_width(header)

        for group_idx, (type_label, group_rooms) in enumerate(type_groups):
            group_totals = defaultdict(int)
            group_total = 0

            for room in group_rooms:
                row_str = pad(room, COL_ROOM)
                row_total = 0
                for g in grades:
                    n = counts.get((room, g, status), 0)
                    row_str += " " + pad(str(n), COL_NUM, 'right')
                    group_totals[g] += n
                    grand_totals[g] += n
                    row_total += n
                row_str += " " + pad(str(row_total), COL_NUM, 'right')
                group_total += row_total
                grand_total += row_total
                lines.append(row_str)

            # 그룹 소계 (그룹이 2개 이상일 때만)
            if len(type_groups) > 1:
                lines.append(separator)
                subtotal_label = f"소계 ({type_label})" if type_label else "소계"
                sub_str = pad(subtotal_label, COL_ROOM)
                for g in grades:
                    sub_str += " " + pad(str(group_totals[g]), COL_NUM, 'right')
                sub_str += " " + pad(str(group_total), COL_NUM, 'right')
                lines.append(sub_str)
                # 그룹 사이 빈 줄 (마지막 그룹 제외)
                if group_idx < len(type_groups) - 1:
                    lines.append("")

        # 전체 합계
        lines.append(separator)
        total_str = pad("합계", COL_ROOM)
        for g in grades:
            total_str += " " + pad(str(grand_totals[g]), COL_NUM, 'right')
        total_str += " " + pad(str(grand_total), COL_NUM, 'right')
        lines.append(total_str)
        lines.append("")

    # 노트북 금지 열람실 표시
    if laptop_zones:
        lines.append(f"노트북 사용 불가: {', '.join(sorted(laptop_zones))}")
        lines.append("")

    return lines


# ============================================================
# 2. 좌석 중복 검증
# ============================================================

def generate_seat_validation(config):
    """seatlist.csv에서 (열람실, 좌석번호) 중복 및 열람실/좌석타입 유효성을 검증합니다."""
    paths = config['paths']
    valid_rooms = set(config.get('valid_rooms', []))
    valid_seat_types = set(config.get('valid_seat_types', []))

    with open(paths['input_seats'], mode='rt', encoding='UTF-8') as f:
        reader = csv.reader(f)
        next(reader)
        rows = [row for row in reader if len(row) >= 4]

    lines = []
    lines.append("=" * 60)
    lines.append("좌석 데이터 검증")
    lines.append("=" * 60)
    lines.append("")

    # 열람실/좌석타입 유효성 검증 (open 좌석이 있는 항목만 대상)
    open_rows = [row for row in rows if row[3] == 'open']
    invalid_rooms = set()
    invalid_seat_types = set()
    for row in open_rows:
        grade, room = row[0], row[1]
        if valid_rooms and room not in valid_rooms:
            invalid_rooms.add(room)
        if valid_seat_types and grade not in valid_seat_types:
            invalid_seat_types.add(grade)

    # 역방향 검증: valid_rooms에 있지만 seatlist(open)에 없는 열람실
    open_rooms_in_seatlist = {row[1] for row in open_rows}
    missing_rooms = valid_rooms - open_rooms_in_seatlist if valid_rooms else set()

    if invalid_rooms:
        lines.append(f"[!] seatlist에 valid_rooms에 없는 열람실 {len(invalid_rooms)}건:")
        for room in sorted(invalid_rooms):
            lines.append(f"  - {room}")
    if invalid_seat_types:
        lines.append(f"[!] seatlist에 valid_seat_types에 없는 좌석타입 {len(invalid_seat_types)}건:")
        for st in sorted(invalid_seat_types):
            lines.append(f"  - {st}")
    if missing_rooms:
        lines.append(f"[!] valid_rooms에 있지만 seatlist에 없는 열람실 {len(missing_rooms)}건:")
        for room in sorted(missing_rooms):
            lines.append(f"  - {room}")
    if not invalid_rooms and not invalid_seat_types and not missing_rooms:
        lines.append("[OK] 열람실/좌석타입 유효성 통과")
    lines.append("")

    # 중복 검증
    seen = {}       # (room, seat_num) → (grade, status) 첫 등장
    duplicates = [] # 중복 목록

    for row in rows:
        grade, room, seat_num, status = row[0], row[1], row[2], row[3]
        key = (room, seat_num)
        if key in seen:
            duplicates.append((room, seat_num, seen[key], (grade, status)))
        else:
            seen[key] = (grade, status)

    if duplicates:
        lines.append(f"[!] 좌석 중복 {len(duplicates)}건 발견:")
        for room, seat_num, first, second in duplicates:
            lines.append(f"  - {room} {seat_num}번: "
                         f"{first[0]}/{first[1]} vs {second[0]}/{second[1]}")
    else:
        lines.append("[OK] 좌석 중복 없음")

    lines.append("")
    return lines


# ============================================================
# 3. 사물함 매핑
# ============================================================

COL_L_ROOM = 22
COL_L_LOC = 12
COL_L_RANGE = 14
COL_L_QTY = 6
LOCKER_LINE_WIDTH = COL_L_ROOM + 1 + COL_L_LOC + 1 + COL_L_RANGE + 1 + COL_L_QTY


def format_locker_row(room, loc, range_str, qty):
    return (f"{pad(room, COL_L_ROOM)} {pad(loc, COL_L_LOC)} "
            f"{pad(range_str, COL_L_RANGE)} {pad(qty, COL_L_QTY, 'right')}")


def generate_locker_preview(config):
    """config의 locker_mapping을 직관적 텍스트 표로 변환합니다."""
    mapping = config['locker_mapping']
    lines = []

    lines.append("=" * LOCKER_LINE_WIDTH)
    lines.append("사물함 배정 매핑 (config.yaml 기준)")
    lines.append("=" * LOCKER_LINE_WIDTH)
    lines.append("")
    lines.append(format_locker_row("열람실", "사물함 위치", "번호 범위", "수량"))
    lines.append("-" * LOCKER_LINE_WIDTH)

    total_capacity = 0

    for room, info in mapping.items():
        lockers = info['lockers']
        for i, lk in enumerate(lockers):
            loc = lk['location']
            start = lk['start']
            end = lk['end']
            capacity = end - start + 1
            total_capacity += capacity

            range_str = f"{start}~{end}번"
            qty_str = f"{capacity}개"
            room_display = room if i == 0 else "  └ overflow →"

            lines.append(format_locker_row(room_display, loc, range_str, qty_str))

        if len(lockers) > 1:
            room_total = sum(l['end'] - l['start'] + 1 for l in lockers)
            lines.append(format_locker_row("", "", "소계", f"{room_total}개"))

    lines.append("-" * LOCKER_LINE_WIDTH)
    lines.append(format_locker_row("", "", "전체 합계", f"{total_capacity}개"))
    lines.append("")

    return lines


# ============================================================
# 메인
# ============================================================

def main():
    config = load_config()

    all_lines = []
    all_lines += generate_seat_summary(config)
    all_lines += generate_seat_validation(config)
    all_lines += generate_locker_preview(config)

    output = "\n".join(all_lines)

    # 콘솔 출력
    print(output)

    # 파일 저장 (git diff 추적용)
    output_path = "config_preview.txt"
    with open(output_path, mode='wt', encoding='UTF-8') as f:
        f.write(output + "\n")
    print(f"\n[+] {output_path} 저장 완료")


if __name__ == "__main__":
    main()
