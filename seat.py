"""
좌석 배정 모듈

설문 데이터(input_data.csv)와 좌석 목록(seatlist.csv)을 읽어
config.yaml에 정의된 단계(phases)에 따라 학생들을 좌석에 배정합니다.

배정 흐름:
  1. CSV에서 학생 데이터와 좌석 데이터를 로드
  2. config.yaml의 phases 순서대로 배정 실행
     - "preference" 타입: 1지망 → 2지망 → 3지망 순서로 매칭
     - "unmatched" 타입: 남은 학생을 잔여 좌석에 랜덤 배정
  3. 결과를 CSV 파일로 저장
"""

import csv
import random
import argparse
import hashlib

from config import load_config


# ============================================================
# CSV 로드 함수
# ============================================================

def load_students(filename):
    """
    설문 응답 CSV를 읽어 학생 딕셔너리를 반환합니다.

    입력 CSV 형식: 타임스탬프, 이메일, 이름, 학번, 학년, 1지망, 2지망, 3지망
    반환값: { '이름_학번': ['학년', '1지망', '2지망', '3지망'] }
    """
    with open(filename, mode='rt', encoding='UTF-8') as file:
        reader = csv.reader(file)
        next(reader)  # 헤더 건너뛰기
        students = {}
        for row in reader:
            row.pop(0)  # 타임스탬프 제거
            row.pop(0)  # 이메일 제거
            key = row.pop(0) + "_" + row.pop(0)  # 이름_학번
            if len(key) > 1:  # 빈 행 방어
                students[key] = row  # ['학년', '1지망', '2지망', '3지망']
    return students


def load_seats(filename):
    """
    좌석 목록 CSV를 읽어 좌석 리스트를 반환합니다.

    반환값: [ ['학년', '열람실', '좌석번호', 'open/closed'], ... ]
    """
    with open(filename, mode='rt', encoding='UTF-8') as file:
        reader = csv.reader(file)
        next(reader)  # 헤더 건너뛰기
        return [row for row in reader if len(row) > 1]


# ============================================================
# 배정 핵심 로직
# ============================================================

def get_preferred_seat_type(student_grade, grade_map):
    """
    학년에 따라 우선 배정할 좌석 타입을 반환합니다.
    예: '1학년' → '2학년' 좌석 우선, '3학년' → '3학년' 좌석 우선
    매핑에 없는 학년은 그대로 반환합니다.
    """
    return grade_map.get(student_grade, student_grade)


def allocate_by_preference(students, seatlist, target_grades, target_seat_types, grade_map):
    """
    지망(1지망→2지망→3지망) 순서로 학생을 좌석에 매칭합니다.

    동작 방식:
      1. target_grades에 해당하는 학생만 대상으로 선별 (빈 리스트면 전체)
      2. 1지망부터 3지망까지 순서대로:
         - 학생 순서를 랜덤 셔플 (공정성)
         - 각 학생의 N지망 열람실에서 빈 좌석을 찾음
         - 학년에 맞는 좌석 타입을 우선 배정, 없으면 다른 타입이라도 배정
      3. 배정된 학생과 좌석은 원본 리스트에서 제거됨 (in-place)

    Args:
        students: 전체 학생 dict (배정되면 제거됨)
        seatlist: 전체 좌석 list (배정되면 제거됨)
        target_grades: 이 단계에서 배정할 학년 리스트 (예: ['3학년', '수료생'])
        target_seat_types: 이 단계에서 사용할 좌석 타입 리스트 (예: ['3학년'])
        grade_map: 학년→좌석타입 매핑 (config에서 로드)

    Returns: { '이름_학번': ['학년', '열람실', '좌석번호', 'open', '1지망배정여부(O/X)'], ... }
    """
    result = {}

    # 배정 대상 학생 선별
    if target_grades:
        candidates = {k: v for k, v in students.items() if v[0] in target_grades}
    else:
        candidates = students.copy()

    def process_preference(pref_idx):
        """pref_idx번째 지망(1~3)에 대해 매칭 처리"""
        candidate_keys = list(candidates.keys())
        random.shuffle(candidate_keys)

        for student_key in candidate_keys:
            student_grade = candidates[student_key][0]
            preferred_type = get_preferred_seat_type(student_grade, grade_map)
            preferred_room = candidates[student_key][pref_idx]

            # 지망 열람실 내 좌석을 학년 우선/비우선으로 분류
            seats_preferred = []  # 학년 타입이 맞는 좌석
            seats_other = []     # 학년 타입이 다른 좌석
            for seat in seatlist:
                if target_seat_types and seat[0] not in target_seat_types:
                    continue
                if seat[1] == preferred_room:
                    if seat[0] == preferred_type:
                        seats_preferred.append(seat)
                    else:
                        seats_other.append(seat)

            # 우선 타입 좌석이 있으면 그 중에서 랜덤 배정, 없으면 비우선 좌석에서 배정
            chosen_seat = None
            if seats_preferred:
                chosen_seat = random.choice(seats_preferred)
            elif seats_other:
                chosen_seat = random.choice(seats_other)

            if chosen_seat:
                # 1지망 배정 여부 태그 추가 (pref_idx==1이면 O, 아니면 X)
                first_pref = 'O' if pref_idx == 1 else 'X'
                result[student_key] = chosen_seat + [first_pref]
                seatlist.remove(chosen_seat)
                students.pop(student_key)
                candidates.pop(student_key)

    # 1지망 → 2지망 → 3지망 순서로 처리
    for pref_idx in [1, 2, 3]:
        process_preference(pref_idx)

    return result


def allocate_remaining(students, seatlist, grade_map, laptop_zones):
    """
    지망에 매칭되지 못한 학생을 남은 좌석에 랜덤 배정합니다.

    우선순위:
      1. 1~3지망 중 노트북 금지 열람실을 신청한 학생 → 허용/금지 구분 없이 배정
         그 외 학생 → 허용 열람실 좌석 우선
      2. 학년에 맞는 좌석 타입을 우선 배정

    Args:
        students: 미배정 학생 dict (배정되면 제거됨)
        seatlist: 잔여 좌석 list (배정되면 제거됨)
        grade_map: 학년→좌석타입 매핑
        laptop_zones: 노트북 금지 열람실 리스트
    """
    result = {}
    student_keys = list(students.keys())
    random.shuffle(student_keys)

    laptop_zones_set = set(laptop_zones)

    for student_key in student_keys:
        student_data = students[student_key]
        student_grade = student_data[0]
        preferred_type = get_preferred_seat_type(student_grade, grade_map)

        # 이 학생이 1~3지망 중 노트북 금지 열람실을 신청했는지 확인
        applied_laptop_zone = any(
            student_data[i] in laptop_zones_set for i in (1, 2, 3)
        )

        # 좌석 분류
        #   - 금지 열람실 신청자 → 허용/금지 구분 없이 학년 매칭만 우선
        #   - 그 외 학생      → 허용 좌석 우선, 금지 좌석 후순위
        if applied_laptop_zone:
            # 금지 열람실 신청자: 학년 매칭만 고려
            seats_matched = []
            seats_other = []
            for seat in seatlist:
                if seat[0] == preferred_type:
                    seats_matched.append(seat)
                else:
                    seats_other.append(seat)
            pools = (seats_matched, seats_other)
        else:
            # 비신청자: 허용 좌석 우선 + 학년 매칭 우선
            seats_allowed_matched = []    # 허용 + 학년 매칭
            seats_allowed_other = []      # 허용 + 학년 미매칭
            seats_banned_matched = []     # 금지 + 학년 매칭
            seats_banned_other = []       # 금지 + 학년 미매칭
            for seat in seatlist:
                is_banned = seat[1] in laptop_zones_set
                is_grade_match = seat[0] == preferred_type
                if not is_banned and is_grade_match:
                    seats_allowed_matched.append(seat)
                elif not is_banned:
                    seats_allowed_other.append(seat)
                elif is_grade_match:
                    seats_banned_matched.append(seat)
                else:
                    seats_banned_other.append(seat)
            pools = (seats_allowed_matched, seats_allowed_other,
                     seats_banned_matched, seats_banned_other)

        chosen_seat = None
        for pool in pools:
            if pool:
                chosen_seat = random.choice(pool)
                break
        if chosen_seat is None and seatlist:
            chosen_seat = random.choice(seatlist)

        if chosen_seat:
            # 잔여 배정은 1지망 배정이 아니므로 X
            result[student_key] = chosen_seat + ['X']
            seatlist.remove(chosen_seat)
            students.pop(student_key)

    return result


# ============================================================
# 배정 실행 (config 기반)
# ============================================================

def run_allocation(students, seatlist, config, phases=None):
    """
    config의 phases에 따라 배정 단계를 순서대로 실행합니다.

    students와 seatlist는 in-place로 수정됩니다 (배정된 항목이 제거됨).
    phases를 지정하면 해당 단계만 실행합니다 (추가 배정 시 사용).
    """
    if phases is None:
        phases = config['phases']

    grade_map = config['grade_to_seat_type']
    laptop_zones = config['laptop_not_allowed_zones']

    result_total = {}
    for phase in phases:
        if phase['type'] == 'preference':
            result = allocate_by_preference(
                students, seatlist,
                phase.get('student_types', []),
                phase.get('seat_types', []),
                grade_map)
        elif phase['type'] == 'unmatched':
            result = allocate_remaining(
                students, seatlist,
                grade_map, laptop_zones)
        else:
            raise ValueError(f"[!] 알 수 없는 phase type: {phase['type']}")
        result_total.update(result)

    return result_total


# ============================================================
# 결과 CSV 저장 유틸리티
# ============================================================

def get_seed_from_file(filename):
    """
    파일 내용의 SHA256 해시를 시드로 변환합니다.

    [2025.8.] 추가 배정 시 생방송 진행하는 대신 input file 기반 시드 고정.
    동일한 입력 파일이면 항상 동일한 시드가 생성되어 결과 재현 가능.
    """
    with open(filename, 'rb') as f:
        content = f.read()
    return int(hashlib.sha256(content).hexdigest(), 16) % (2**32)


def write_result_csv(filepath, result, mode='wt'):
    """배정 결과를 CSV로 저장합니다. mode='at'이면 기존 파일에 추가합니다."""
    with open(filepath, mode=mode, encoding='UTF-8') as file:
        if mode == 'wt':
            file.write("이름,학번뒤2자리,열람실,좌석번호,1지망배정여부\n")
        for key, value in result.items():
            name = key.split("_")[0]
            student_id = key.split("_")[1][-2:]  # 가명처리: 뒷 2자리만
            first_pref = value[4]  # 'O' 또는 'X'
            file.write(f"{name},{student_id},{value[1]},{value[2]},{first_pref}\n")


# ============================================================
# 메인 실행
# ============================================================

def main():
    """전체 배정을 실행합니다."""
    config = load_config()
    paths = config['paths']

    students = load_students(paths['input_students'])
    seatlist_all = load_seats(paths['input_seats'])

    # open 좌석만 배정 대상, closed는 잔여석 출력용으로 보관
    seatlist_open = [s for s in seatlist_all if s[3] == 'open']
    seatlist_closed = [s for s in seatlist_all if s[3] != 'open']

    result = run_allocation(students, seatlist_open, config)
    print(f"[+]미배정된 학생 수: {len(students)}")
    print(f"[+]잔여 좌석 수: {len(seatlist_open)}")

    # 배정 결과 저장
    write_result_csv(paths['output_result'], result)
    print(f"[+]배치결과 저장 경로: {paths['output_result']}")

    # 미배정 학생 저장
    with open(paths['output_unmatched_students'], mode='wt', encoding='UTF-8') as file:
        file.write("이름_학번,학년,1지망,2지망,3지망\n")
        for key, value in students.items():
            file.write(f"{key},{value[0]},{value[1]},{value[2]},{value[3]}\n")
    print(f"[+]남은 학생 리스트 저장 경로: {paths['output_unmatched_students']}")

    # 잔여 좌석 저장
    with open(paths['output_unmatched_seats'], mode='wt', encoding='UTF-8') as file:
        for seat in seatlist_open + seatlist_closed:
            file.write(f"{seat[0]},{seat[1]},{seat[2]},{seat[3]}\n")
    print(f"[+]남은 좌석 리스트 저장 경로: {paths['output_unmatched_seats']}")


def main_additional(infile_std, infile_result, infile_seat_unmatched, expected=None):
    """추가 배정을 실행합니다 (기한 후 신청자용)."""
    config = load_config()
    paths = config['paths']

    # 전체 학생 목록 로드
    students = load_students(infile_std)

    # 이미 배정된 학생 목록 로드
    assigned = set()
    with open(infile_result, mode='rt', encoding='UTF-8') as file:
        next(file)  # header skip
        for line in file:
            parts = line.strip().split(",")
            if len(parts) >= 2:
                assigned.add(parts[0] + "_" + parts[1])  # 이름_학번뒤2자리

    # 미배정 학생만 추출 (학번 뒷 2자리로 비교)
    unassigned = {
        k: v for k, v in students.items()
        if (k.split("_")[0] + "_" + k.split("_")[1][-2:]) not in assigned
    }

    # 예상 인원 검증
    if expected is not None and expected != len(unassigned):
        raise ValueError(f"[!] 예상 추가 배정자 수 {expected}명과 실제 {len(unassigned)}명이 다릅니다.")

    # 잔여 좌석 로드
    seatlist_open = []
    with open(infile_seat_unmatched, mode='rt', encoding='UTF-8') as file:
        next(file)
        for row in csv.reader(file):
            if row[3] == 'open':
                seatlist_open.append(row)

    # [2025.8.] 추가 배정: 입력 파일 해시 기반 시드 → 동일 입력이면 동일 결과 보장
    random.seed(get_seed_from_file(infile_std))

    # config에서 지정된 추가 배정 단계만 실행
    add_phases = [config['phases'][i] for i in config['add_mode_phase_indices']]
    result_additional = run_allocation(unassigned, seatlist_open, config, phases=add_phases)

    # 로그 출력
    print("[+] 추가 배정 결과:")
    for key, seat in result_additional.items():
        print(f" - {key}: {seat[1]} {seat[2]}번")

    # 추가 배정 결과 저장
    write_result_csv(paths['output_result_additional'], result_additional)
    print(f"[+] 추가 배치결과 저장 경로: {paths['output_result_additional']}")

    # 기존 seat_result.csv에도 추가
    write_result_csv(paths['output_result'], result_additional, mode='at')
    print("[+] seat_result.csv 갱신 완료")

    # 잔여 좌석 파일 업데이트 (배정된 좌석 제거)
    updated_seats = []
    with open(paths['output_unmatched_seats'], mode='rt', encoding='UTF-8') as file:
        for row in csv.reader(file):
            updated_seats.append(row)

    allocated_keys = {(v[1], v[2]) for v in result_additional.values()}
    updated_seats = [s for s in updated_seats if (s[1], s[2]) not in allocated_keys]

    with open(paths['output_unmatched_seats'], mode='wt', encoding='UTF-8', newline='') as file:
        writer = csv.writer(file)
        for s in updated_seats:
            writer.writerow(s)
    print("[+] seat_unmatched_seat.csv 갱신 완료")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["normal", "add"], default="normal")
    parser.add_argument("--expected", type=int, default=None, help="추가 배정 예상 인원")
    args = parser.parse_args()

    config = load_config()
    paths = config['paths']

    if args.mode == "normal":
        main()
    else:
        main_additional(paths['input_students'],
                        paths['output_result'],
                        paths['output_unmatched_seats'],
                        expected=args.expected)
