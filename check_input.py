"""
입력 데이터 검증 모듈

input_data.csv와 seatlist.csv를 읽어 다음을 검증합니다:
  - 이메일 중복 여부
  - 학번 중복 여부
  - 이름+학번뒤2자리 조합 중복 여부 (결과 파일에서 식별자로 사용되므로)
  - 학생 수 ≤ 좌석 수 여부
"""

from config import load_config


def main(config=None):
    if config is None:
        config = load_config()
    paths = config['paths']

    valid_rooms = set(config.get('valid_rooms', []))
    valid_student_types = set(config.get('valid_student_types', []))

    stdnum, seatnum = 0, 0
    emails = set()
    student_ids = set()
    name_id2_set = set()  # 이름+학번뒤2자리 조합 중복 확인
    invalid_values = []  # (행번호, 필드명, 값) 목록

    with open(paths['input_students'], encoding="utf-8-sig") as f_std:
        lines = f_std.readlines()

        # 첫 줄(header) 건너뛰기
        for line in lines[1:]:
            if len(line.strip()) == 0:
                break
            stdnum += 1
            vals = line.strip().split(",")
            name = vals[2]       # 이름
            email = vals[1]      # 이메일
            student_id = vals[3] # 학번
            grade = vals[4]      # 학년/지위
            pref1 = vals[5]      # 1지망
            pref2 = vals[6]      # 2지망
            pref3 = vals[7]      # 3지망

            # 이메일 중복 체크
            if email in emails:
                print(f"[-] 중복 이메일 발생: {email}")
            else:
                emails.add(email)

            # 학번 중복 체크
            if student_id in student_ids:
                print(f"[-] 중복 학번 발생: {student_id}")
            else:
                student_ids.add(student_id)

            # 이름+학번뒤2자리 중복 체크
            key = name + "_" + student_id[-2:]
            if key in name_id2_set:
                print(f"[-] 이름+학번뒤2자리 중복 발생: {key}")
            else:
                name_id2_set.add(key)

            # 학년/지위 유효성 검증
            if valid_student_types and grade not in valid_student_types:
                invalid_values.append((stdnum + 1, "학년", grade, name))

            # 1~3지망 열람실 유효성 검증
            if valid_rooms:
                for pref_idx, pref in enumerate([pref1, pref2, pref3], 1):
                    if pref not in valid_rooms:
                        invalid_values.append((stdnum + 1, f"{pref_idx}지망", pref, name))

    # 유효하지 않은 값 출력
    if invalid_values:
        print(f"[!] 입력 데이터에 유효하지 않은 값 {len(invalid_values)}건:")
        for row_num, field, value, name in invalid_values:
            print(f"  - {row_num}행 {name}: {field} = '{value}'")
        raise ValueError(f"[!] input_data에 유효하지 않은 값이 {len(invalid_values)}건 있습니다. 위 목록을 확인하세요.")

    with open(paths['input_seats'], 'rt', encoding='UTF8') as f_seat:
        for line in f_seat.readlines():
            if "open" in line:
                seatnum += 1

    if stdnum > seatnum:
        print("[-]좌석 수 부족. 입력값 조정할 것!")


if __name__ == "__main__":
    main()
