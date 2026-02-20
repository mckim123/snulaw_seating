"""
신청자 검증 스크립트

compare.csv (학적부)와 input_data.csv (신청서)를 대조하여 다음을 검증합니다:
  1. 학번 매칭 후 이름이 다른 사람
  2. 학적상태가 '휴학'인데 신청한 사람
  3. 학년 불일치 (compare 학년 0/1/2 → input 1학년/2학년/3학년)
  4. 1학년/2학년/3학년 외의 학년으로 신청한 사람
  5. 매칭 안 된 사람 (한쪽에만 존재)
  6. input_data 내 동명이인

해당 목록에 있다고 하여 문제되는 것은 아니며, 단지 검토가 필요한 경우입니다.
"""

import csv
import os
import sys
from collections import defaultdict


def load_compare(path):
    """compare.csv를 읽어 학번을 key로 하는 dict 반환"""
    students = {}
    with open(path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sid = row["학번"].strip()
            students[sid] = {
                "이름": row["한글성명"].strip(),
                "학적상태": row["학적상태"].strip(),
                "학년": row["학년"].strip(),
            }
    return students


def load_input(path):
    """input_data.csv를 읽어 학번을 key로 하는 dict 반환"""
    students = {}
    with open(path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name_col = "1. 본인의 성명을 입력해주십시오."
            sid_col = "2. 본인의 학번을 입력해 주십시오."
            grade_col = "3. 본인의 학년 또는 지위를 선택해 주십시오."

            sid = row[sid_col].strip()
            students[sid] = {
                "이름": row[name_col].strip(),
                "학년": row[grade_col].strip(),
                "이메일": row["이메일 주소"].strip(),
            }
    return students


# compare 학년 -> input 학년 매핑
GRADE_MAP = {
    "0": "1학년",
    "1": "2학년",
    "2": "3학년",
}

VALID_GRADES = {"1학년", "2학년", "3학년"}


def validate(compare_path, input_path):
    compare = load_compare(compare_path)
    inp = load_input(input_path)

    compare_ids = set(compare.keys())
    input_ids = set(inp.keys())
    matched_ids = compare_ids & input_ids

    # 1. 이름 불일치
    name_mismatch = []
    for sid in sorted(matched_ids):
        c_name = compare[sid]["이름"]
        i_name = inp[sid]["이름"]
        if c_name != i_name:
            name_mismatch.append((sid, c_name, i_name))

    # 2. 휴학자 신청
    on_leave = []
    for sid in sorted(matched_ids):
        if compare[sid]["학적상태"] == "휴학":
            on_leave.append((sid, inp[sid]["이름"]))

    # 3. 학년 불일치
    grade_mismatch = []
    for sid in sorted(matched_ids):
        c_grade = compare[sid]["학년"]
        i_grade = inp[sid]["학년"]
        expected = GRADE_MAP.get(c_grade)
        if expected is not None and i_grade != expected:
            grade_mismatch.append((sid, inp[sid]["이름"], c_grade, expected, i_grade))

    # 4. 1학년/2학년/3학년 외 학년으로 신청한 사람 (전체 input 대상)
    invalid_grade = []
    for sid in sorted(input_ids):
        i_grade = inp[sid]["학년"]
        if i_grade not in VALID_GRADES:
            invalid_grade.append((sid, inp[sid]["이름"], i_grade))

    # 5. input_data 내 동명이인
    name_to_sids = defaultdict(list)
    for sid in sorted(input_ids):
        name_to_sids[inp[sid]["이름"]].append(sid)
    duplicated_names = {
        name: sids for name, sids in name_to_sids.items() if len(sids) >= 2
    }

    # 6. 매칭 안 된 사람
    # compare에만 있는 사람 중 2024학번 이상만 출력 (2023 이하는 제외)
    only_compare = sorted(
        sid for sid in (compare_ids - input_ids)
        if int(sid.split("-")[0]) >= 2024
    )
    only_input = sorted(input_ids - compare_ids)

    # --- 출력 ---
    print("=" * 60)
    print("1. 이름 불일치 (학번 매칭됨, 이름 다름)")
    print("=" * 60)
    if name_mismatch:
        for sid, c_name, i_name in name_mismatch:
            print(f"  학번: {sid} | 학적부: {c_name} | 신청서: {i_name}")
    else:
        print("  없음")

    print()
    print("=" * 60)
    print("2. 휴학자인데 신청한 사람")
    print("=" * 60)
    if on_leave:
        for sid, name in on_leave:
            print(f"  학번: {sid} | 이름: {name}")
    else:
        print("  없음")

    print()
    print("=" * 60)
    print("3. 학년 불일치 (학적부 학년 vs 신청서 학년)")
    print("=" * 60)
    if grade_mismatch:
        for sid, name, c_grade, expected, actual in grade_mismatch:
            print(f"  학번: {sid} | 이름: {name} | 학적부: {c_grade}(→{expected}) | 신청서: {actual}")
    else:
        print("  없음")

    print()
    print("=" * 60)
    print("4. 1학년/2학년/3학년 외 학년으로 신청한 사람")
    print("=" * 60)
    if invalid_grade:
        for sid, name, grade in invalid_grade:
            print(f"  학번: {sid} | 이름: {name} | 신청 학년: {grade}")
    else:
        print("  없음")

    print()
    print("=" * 60)
    print("5. input_data 내 동명이인")
    print("=" * 60)
    if duplicated_names:
        for name in sorted(duplicated_names.keys()):
            sids = duplicated_names[name]
            print(f"  이름: {name}")
            for sid in sids:
                print(f"    학번: {sid} | 학년: {inp[sid]['학년']}")
    else:
        print("  없음")

    print()
    print("=" * 60)
    print("6. 매칭 안 된 사람")
    print("=" * 60)
    print(f"  [compare.csv에만 있는 사람 - 2024학번 이상 ({len(only_compare)}명)]")
    if only_compare:
        for sid in only_compare:
            print(f"    학번: {sid} | 이름: {compare[sid]['이름']}")
    else:
        print("    없음")

    print()
    print(f"  [input_data.csv에만 있는 사람 ({len(only_input)}명)]")
    if only_input:
        for sid in only_input:
            print(f"    학번: {sid} | 이름: {inp[sid]['이름']}")
    else:
        print("    없음")

    # 요약
    print()
    print("=" * 60)
    print("요약")
    print("=" * 60)
    print(f"  학적부 인원: {len(compare)}명")
    print(f"  신청자 인원: {len(inp)}명")
    print(f"  매칭 성공: {len(matched_ids)}명")
    print(f"  이름 불일치: {len(name_mismatch)}건")
    print(f"  휴학자 신청: {len(on_leave)}건")
    print(f"  학년 불일치: {len(grade_mismatch)}건")
    print(f"  유효하지 않은 학년: {len(invalid_grade)}건")
    print(f"  동명이인: {len(duplicated_names)}건 ({sum(len(s) for s in duplicated_names.values())}명)")
    print(f"  compare에만 존재: {len(only_compare)}명")
    print(f"  input에만 존재: {len(only_input)}명")


if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))
    compare_path = os.path.join(base_dir, "input", "compare.csv")
    input_path = os.path.join(base_dir, "input", "input_data.csv")

    if not os.path.exists(compare_path):
        print(f"[!] compare.csv를 찾을 수 없습니다: {compare_path}")
    elif not os.path.exists(input_path):
        print(f"[!] input_data.csv를 찾을 수 없습니다: {input_path}")
    else:
        output_path = os.path.join(base_dir, "output", "validation_result.txt")
        with open(output_path, "w", encoding="utf-8") as f:
            old_stdout = sys.stdout
            sys.stdout = f
            validate(compare_path, input_path)
            sys.stdout = old_stdout
        # 콘솔에도 출력
        with open(output_path, encoding="utf-8") as f:
            print(f.read())
        print(f"[*] 결과가 {output_path} 에 저장되었습니다.")
