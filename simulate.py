"""
좌석 배정 시뮬레이션

서로 다른 시드로 N번 배정을 시뮬레이션하여
열람실별 빈자리 발생 통계를 분석합니다.

사용법: python simulate.py --runs=100
"""

import argparse
import random
import statistics
from collections import defaultdict

from config import load_config
from seat import load_students, load_seats, run_allocation


def run_single_simulation(config, seed):
    """
    주어진 seed로 1회 배정을 실행합니다.

    Returns: { 열람실명: 빈자리 수 }
    """
    paths = config['paths']

    # 매 시뮬레이션마다 데이터를 새로 로드 (run_allocation이 in-place 수정하므로)
    students = load_students(paths['input_students'])
    seatlist_all = load_seats(paths['input_seats'])
    seatlist_open = [s for s in seatlist_all if s[3] == 'open']

    # 배정 전 열람실별 총 좌석 수
    room_total = defaultdict(int)
    for seat in seatlist_open:
        room_total[seat[1]] += 1

    # 배정 실행
    random.seed(seed)
    result = run_allocation(students, seatlist_open, config)

    # 배정된 좌석 수
    room_allocated = defaultdict(int)
    for student_key, seat in result.items():
        room_allocated[seat[1]] += 1

    # 빈자리 = 총 좌석 - 배정된 좌석
    return {room: room_total[room] - room_allocated.get(room, 0) for room in room_total}


def main():
    parser = argparse.ArgumentParser(description='좌석 배정 시뮬레이션')
    parser.add_argument('--runs', type=int, default=100, help='시뮬레이션 횟수 (기본: 100)')
    args = parser.parse_args()

    config = load_config()

    # 시뮬레이션 실행
    all_vacancies = defaultdict(list)

    for i in range(args.runs):
        seed = random.randint(0, 2**32 - 1)
        vacancies = run_single_simulation(config, seed)
        for room, count in vacancies.items():
            all_vacancies[room].append(count)

        if (i + 1) % 10 == 0:
            print(f"[*] {i + 1}/{args.runs} 시뮬레이션 완료")

    # 결과 출력
    print(f"\n=== 시뮬레이션 결과 ({args.runs}회) ===")
    print(f"{'열람실':<25} {'평균':>6} {'최소':>6} {'최대':>6} {'표준편차':>8}")
    print("-" * 55)

    total_vacancy_mean = 0
    for room in sorted(all_vacancies.keys()):
        data = all_vacancies[room]
        mean = statistics.mean(data)
        mn = min(data)
        mx = max(data)
        stdev = statistics.stdev(data) if len(data) > 1 else 0
        print(f"{room:<25} {mean:>6.1f} {mn:>6} {mx:>6} {stdev:>8.2f}")
        total_vacancy_mean += mean

    print("-" * 55)
    print(f"{'전체 빈자리 합계':<25} {total_vacancy_mean:>6.1f}")


if __name__ == "__main__":
    main()
