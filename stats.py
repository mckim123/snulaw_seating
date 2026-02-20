"""
배정 결과 통계 모듈

좌석 배정 결과를 분석하여 열람실별 1지망/2지망/3지망 충족률을 출력합니다.
학년 그룹별(1-2학년, 3학년+수료생, 졸업생)로 분리하여 통계를 냅니다.
"""

import csv
from collections import defaultdict

from config import load_config


# 학년 그룹 정의: 라벨 → 해당 학년 리스트
GRADE_GROUPS = {
    '1-2학년': ['1학년', '2학년'],
    '3학년': ['3학년', '수료생'],
    '졸업생': ['졸업생'],
}


def load_applicants(input_path):
    """설문 응답 데이터를 로드합니다."""
    with open(input_path, mode='r', encoding='utf-8') as infile:
        reader = csv.reader(infile)
        next(reader)
        headers = ['타임스탬프', '이메일', '성명', '학번', '학년', '1지망', '2지망', '3지망']
        return [dict(zip(headers, row[:len(headers)])) for row in reader]


def load_results(result_path):
    """좌석 배정 결과를 로드합니다."""
    with open(result_path, mode='r', encoding='utf-8') as infile:
        reader = csv.reader(infile)
        next(reader)
        return [dict(zip(['성명', '학번뒤2자리', '열람실', '좌석번호'], row)) for row in reader]


def compute_stats_for_group(students, results_lookup, group_label):
    """
    학생 그룹에 대한 열람실별 지망 통계를 계산합니다.

    Returns: { "열람실_그룹라벨": { '1지망 지원자 수': N, '1지망 당첨자 수': N, ... } }
    """
    # 해당 그룹 학생들이 지망한 모든 열람실 수집
    all_rooms = set()
    for s in students:
        all_rooms.update([s['1지망'], s['2지망'], s['3지망']])
    all_rooms.discard(None)

    stats = {room: defaultdict(int) for room in all_rooms}

    # 1지망 지원자 수
    for s in students:
        room = s['1지망']
        if room in stats:
            stats[room]['1지망 지원자 수'] += 1

    # 당첨자 지망 매칭 통계
    for s in students:
        key = s['성명'] + s['학번'][-2:]
        if key not in results_lookup:
            continue
        assigned = results_lookup[key]
        if assigned not in stats:
            stats[assigned] = defaultdict(int)

        if s['1지망'] == assigned:
            stats[assigned]['1지망 당첨자 수'] += 1
        elif s['2지망'] == assigned:
            stats[assigned]['2지망 당첨자 수'] += 1
        elif s['3지망'] == assigned:
            stats[assigned]['3지망 당첨자 수'] += 1
        else:
            stats[assigned]['지망X 당첨자 수'] += 1

    return {f"{room}_{group_label}": data for room, data in stats.items()}


def main():
    try:
        config = load_config()
        paths = config['paths']

        applicants = load_applicants(paths['input_students'])
        results = load_results(paths['output_result'])
        results_lookup = {r['성명'] + r['학번뒤2자리']: r['열람실'] for r in results}

        all_stats = {}
        for label, grades in GRADE_GROUPS.items():
            group = [a for a in applicants if a.get('학년') in grades]
            all_stats.update(compute_stats_for_group(group, results_lookup, label))

        print("--- 열람실 신청 및 배정 결과 통계 ---")
        for room in sorted(all_stats.keys()):
            data = all_stats[room]
            if (sum(data.values()) > 0 and
                    data['1지망 지원자 수'] > data['1지망 당첨자 수'] and
                    (data['2지망 당첨자 수'] > 0 or data['3지망 당첨자 수'] > 0 or data['지망X 당첨자 수'] > 0)):
                print(f"\n[ {room} ]")
                print(f"  - 1지망 지원자 / 1지망 당첨자 / 2지망 당첨자 / 3지망 당첨자 / 지망X 당첨자: "
                      f"{data['1지망 지원자 수']} / {data['1지망 당첨자 수']} / {data['2지망 당첨자 수']} / "
                      f"{data['3지망 당첨자 수']} / {data['지망X 당첨자 수']}")

    except FileNotFoundError as e:
        print(f"오류: '{e.filename}' 파일을 찾을 수 없습니다.")
    except Exception as e:
        print(f"오류 발생: {e}")


if __name__ == "__main__":
    main()
