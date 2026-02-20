"""
테스트용 input_data.csv 샘플 생성기

seatlist.csv의 열람실별 open 좌석 수와 config.yaml의 학년→좌석타입 매핑을
기반으로, 실제 신청 패턴과 유사한 분포의 샘플 데이터를 생성합니다.

사용법: python temp/gen_sample.py
출력:   input/input_data.csv
"""

import csv
import random
import os
import string
import sys
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from config import load_config

# 학년별 인원수
GRADE_COUNTS = {
    "1학년": 150,
    "2학년": 162,
    "3학년": 150,
    "졸업생": 11,
    "수료생": 1,
}

# 한글 성 (상위 빈도순)
LAST_NAMES = list(
    "김이박최정강조윤장임한오서신권황안송류전홍고문양손배백허유남심노하주우구신"
    "민유나진채원천방공강현변함석탁제편선설길연위곽여추마도석"
)

# 한글 이름 음절 (충분히 다양하게)
FIRST_SYLLABLES = list(
    "민서지윤하은수현준영진우성호재혁정다예솔아빈율원도경승태상"
    "연주희찬별담온결한나래슬기새롬겨울봄빛꽃샘들풀"
    "동석훈철광명선혜숙자옥순임복남일종근용달"
    "소유채린시안윤건도연시현서윤지안하윤서준이준"
    "규담찬미소윤서연하진채은수빈예린지호서영민재"
    "태현유빈하람가온나윤다온라온마루바다사랑하늘"
    "세아이안수아예나지유하율주아지윤채아시아서아"
    "은우시우도윤예준이찬재윤한결지환태윤"
)


def random_name():
    last = random.choice(LAST_NAMES)
    first = random.choice(FIRST_SYLLABLES) + random.choice(FIRST_SYLLABLES)
    return last + first


def random_email():
    local = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    return f"{local}@snu.ac.kr"


def load_room_weights(config):
    """
    seatlist.csv에서 열람실별 open 좌석 수를 집계하고,
    학년(grade)별 신청 가중치를 계산합니다.

    가중치 로직:
      - 해당 학년의 preferred seat_type과 일치하는 좌석이 있는 열람실 → 해당 좌석 수 가중치
      - 일치하지 않는 좌석도 있지만 낮은 가중치 (0.3배)
      - 결과적으로 좌석이 많은 열람실일수록, 그리고 자기 학년 좌석이 많을수록 더 많이 신청

    Returns: { grade: [room별 가중치 리스트] }  (valid_rooms 순서)
    """
    paths = config['paths']
    valid_rooms = config['valid_rooms']
    grade_map = config['grade_to_seat_type']

    # 열람실별, 좌석타입별 open 좌석 수 집계
    room_type_counts = defaultdict(lambda: defaultdict(int))  # room → seat_type → count
    with open(paths['input_seats'], mode='rt', encoding='UTF-8') as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            if len(row) >= 4 and row[3] == 'open':
                seat_type, room = row[0], row[1]
                room_type_counts[room][seat_type] += 1

    # 학년별 가중치 계산
    weights_by_grade = {}
    for grade in GRADE_COUNTS:
        preferred_type = grade_map.get(grade, grade)
        w = []
        for room in valid_rooms:
            counts = room_type_counts.get(room, {})
            matched = counts.get(preferred_type, 0)
            other = sum(c for t, c in counts.items() if t != preferred_type)
            # 매칭 좌석은 풀 가중치, 비매칭은 0.3배
            w.append(matched + other * 0.3)
        weights_by_grade[grade] = w

    return weights_by_grade


def pick_preferences(rooms, weights):
    """가중치 기반으로 중복 없이 1~3지망을 선택합니다."""
    chosen = []
    available = list(range(len(rooms)))

    for _ in range(3):
        w = [weights[i] if i in available else 0.0 for i in range(len(rooms))]
        total = sum(w)
        if total == 0:
            pick = random.choice(available)
        else:
            pick = random.choices(range(len(rooms)), weights=w, k=1)[0]
        chosen.append(rooms[pick])
        available.remove(pick)

    return chosen


def main():
    random.seed(42)

    config = load_config()
    valid_rooms = config['valid_rooms']
    weights_by_grade = load_room_weights(config)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(script_dir, "..", "input", "input_data.csv")
    output_path = os.path.normpath(output_path)

    header = (
        "타임스탬프,"
        "이메일 주소,"
        "1. 본인의 성명을 입력해주십시오.,"
        "2. 본인의 학번을 입력해 주십시오,"
        "3. 본인의 학년 또는 지위를 선택해 주십시오.,"
        "4. 1지망~3지망 지정좌석을 각각 선택해 주십시오. [1지망],"
        "4. 1지망~3지망 지정좌석을 각각 선택해 주십시오. [2지망],"
        "4. 1지망~3지망 지정좌석을 각각 선택해 주십시오. [3지망]"
    )

    timestamp = "1/11/2000 12:00"
    student_id_counter = 11111

    rows = []
    for grade, count in GRADE_COUNTS.items():
        weights = weights_by_grade[grade]
        for _ in range(count):
            name = random_name()
            email = random_email()
            sid = f"2000-{student_id_counter:05d}"
            student_id_counter += 1
            prefs = pick_preferences(valid_rooms, weights)
            rows.append(f"{timestamp},{email},{name},{sid},{grade},{prefs[0]},{prefs[1]},{prefs[2]}")

    # 셔플 (학년별로 뭉치지 않도록)
    random.shuffle(rows)

    with open(output_path, mode='wt', encoding='UTF-8', newline='') as f:
        f.write(header + "\n")
        for row in rows:
            f.write(row + "\n")

    print(f"[+] {len(rows)}명 샘플 생성 완료: {output_path}")

    # 가중치 확인용 출력
    print("\n[*] 열람실별 가중치:")
    for grade in GRADE_COUNTS:
        w = weights_by_grade[grade]
        total = sum(w)
        print(f"  {grade}:")
        for i, room in enumerate(valid_rooms):
            pct = w[i] / total * 100 if total > 0 else 0
            print(f"    {room}: {w[i]:.1f} ({pct:.1f}%)")


if __name__ == "__main__":
    main()
