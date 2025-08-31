import csv
import random
import argparse
import hashlib

## [2024.8.] 남는좌석 배치시 학년별 좌석에 우선적으로 배치. 2024-1 민원사항 반영.
STD_TYPE_TO_SEAT_TYPE = {
    '3학년': '3학년',
    '수료생': '3학년',
    '졸업생': '졸업생',
    '1학년': '2학년',
    '2학년': '2학년'
}

## [2025.8.] 남는 좌석 배치시 노트북 허용 열람실에 우선적으로 배치
LAPTOP_NOT_ALLOWED_ZONES = [
    '15동 401호(평상)',
    '15동 401호(칸막이)',
]

def get_preferred_seat_type(std_type):
    """
    우선적으로 배정되어야 할 좌석 타입 반환 ('1학년' -> '2학년', '2학년' -> '2학년', '3학년' -> '3학년')
    dict에 없는 경우 std_type 그대로 반환
    """
    return STD_TYPE_TO_SEAT_TYPE.get(std_type, std_type)


def csv_to_dict_std(filename):
    # '김학생_2020-20000': ['1학년', '법오 큰방(칸막이)', '국산(칸막이)', '15동 404호(칸막이)']
    with open(filename, mode='rt', encoding='UTF-8') as file:
        reader = csv.reader(file)
        next(reader)
        result = {}
        for row in reader:
            row.pop(0)  # 타임스탬프
            row.pop(0)  # 이메일 주소
            key = row.pop(0) + "_" + row.pop(0)
            if len(key) > 1:
                result[key] = row
    return result


def csv_to_list_seat(filename):  # ['3학년', '15동 401호(칸막이)', '38', 'open']
    with open(filename, mode='rt', encoding='UTF-8') as file:
        reader = csv.reader(file)
        next(reader)
        result = []
        for row in reader:
            if len(row) > 1:
                result.append(row)
    return result


def std_alloc(student, seatlist, std_types, seat_types):
    """
    학생들을 좌석에 배치하는 함수
    student: {학생이름: [학년, 1지망, 2지망, 3지망, ...]}
    seatlist: [[배정 대상 학년, 열람실, 번호, 상태], ...]
    std_types: 배정 대상 학년 리스트 (예: ['3학년', '수료생', '졸업생']), 비어있으면 전체 학생 대상
    seat_types: 배정 가능한 좌석 종류 리스트 (예: ['3학년']), 비어있으면 전체 좌석 대상
    """

    result = {}  # 최종 배치 결과

    # 좌석 배정 대상이 되는 학년 학생 선별(비어있는 경우 전체 학생 대상)
    if std_types:
        curr_students = {k: v for k, v in student.items() if v[0] in std_types}
    else:
        curr_students = student.copy()

    def alloc_pref(pref_idx):
        """
        한 지망(pref_idx)에 대해 배치 처리
        pref_idx: 학생 preference index (1: 1지망, 2: 2지망, 3: 3지망)
        """
        curr_students_pref = list(curr_students.keys())  # 배정 대상 학생 명단
        random.shuffle(curr_students_pref)  # 배정 순서 섞기

        for std_key in curr_students_pref:
            std_type = curr_students.get(std_key)[0]
            ## [2025.8.] 좌석 배정 시 이전 단계 잔여 좌석도 활용하되, 학년별 좌석에 우선적으로 배치하도록 로직 수정
            preferred_seat_type = get_preferred_seat_type(std_type)

            seatlist_preferred_tmp = []  # 지망 열람실 내 현재 우선 배정 가능 좌석 목록
            seatlist_tmp = []  # 지망 열람실 내 현재 우선X 배정 가능 좌석 목록
            for seat in seatlist:
                if seat_types and seat[0] not in seat_types:  # 좌석 타입 조건이 있으나 미충족 시 생략
                    continue
                if seat[1] == curr_students[std_key][pref_idx]:
                    if seat[0] == preferred_seat_type:
                        seatlist_preferred_tmp.append(seat)  # 우선 배정 가능 좌석
                    else:
                        seatlist_tmp.append(seat)

            # 조건에 맞는 좌석이 있으면 배정
            if seatlist_preferred_tmp:
                seat = random.choice(seatlist_preferred_tmp)
                result[std_key] = seat
                seatlist.remove(seat)  # 좌석 제거
                student.pop(std_key)  # 학생 제거
                curr_students.pop(std_key)  # 배정 대상에서 제거

            elif seatlist_tmp:
                seat = random.choice(seatlist_tmp)
                result[std_key] = seat
                seatlist.remove(seat)  # 좌석 제거
                student.pop(std_key)  # 학생 제거
                curr_students.pop(std_key)  # 배정 대상에서 제거

    # 1지망, 2지망, 3지망 순서대로 배치 처리
    for pref_idx in [1, 2, 3]:
        alloc_pref(pref_idx)

    return result


def std_alloc_unmatched(student, seatlist):
    """
    학생들을 좌석에 배치하는 함수
    student: {학생이름: [학년, 1지망, 2지망, 3지망, ...]}
    seatlist: [[배정 대상 학년, 열람실, 번호, 상태], ...]
    """

    result = {}  # 최종 배치 결과 저장
    curr_students = list(student.keys())  # 배정 대상 학생 명단
    random.shuffle(curr_students)  # 배정 순서 섞기

    ## [2025.8.] 남는 좌석 배치시 노트북 허용 열람실에 우선적으로 배치
    laptop_allowed_cnt = len([0 for seat in seatlist if seat[1] not in LAPTOP_NOT_ALLOWED_ZONES])

    ## [2024.8.] 남는 좌석 배치시 학년별 좌석에 우선적으로 배치. 2024-1 민원사항 반영.
    for std_key in curr_students:
        std_type = student[std_key][0]
        preferred_seat_type = get_preferred_seat_type(std_type)

        seatlist_tmp_std_type_matched = []      # 지망 열람실 내 현재 배정 가능 좌석 목록
        seatlist_tmp_std_type_unmatched = []    # 지망 열람실 내 현재 배정 가능 좌석 목록

        for seat in seatlist:
            ## [2025.8.] 남는 좌석 배치시 노트북 허용 열람실에 우선적으로 배치
            if laptop_allowed_cnt > 0 and seat[1] in LAPTOP_NOT_ALLOWED_ZONES:
                continue
            if seat[0] == preferred_seat_type:
                seatlist_tmp_std_type_matched.append(seat)
            else:
                seatlist_tmp_std_type_unmatched.append(seat)

        if laptop_allowed_cnt > 0:
            laptop_allowed_cnt -= 1

        if seatlist_tmp_std_type_matched:  # 좌석 타입 조건에 맞는 좌석이 있으면 배정
            seat = random.choice(seatlist_tmp_std_type_matched)
            result[std_key] = seat
            seatlist.remove(seat)  # 좌석 제거
            student.pop(std_key)  # 학생 제거

        elif seatlist_tmp_std_type_unmatched:  # 없는 경우 아무 자리나 배정
            seat = random.choice(seatlist_tmp_std_type_unmatched)
            result[std_key] = seat
            seatlist.remove(seat)  # 좌석 제거
            student.pop(std_key)  # 학생 제거

        elif seatlist:   # 혹시 몰라 넣어 두었으나, 걸릴 일 없음
            seat = random.choice(seatlist)
            result[std_key] = seat
            seatlist.remove(seat)  # 좌석 제거
            student.pop(std_key)  # 학생 제거

    return result


def std_3rd_alloc(student, seatlist):
    return std_alloc(student, seatlist, ['3학년', '수료생'], ['3학년'])


def std_grad_alloc(student, seatlist):
    ## [2025.8.] 좌석 배정 시 이전 단계 잔여 좌석도 활용하되, 학년별 좌석에 우선적으로 배치하도록 로직 수정
    return std_alloc(student, seatlist, ['3학년', '수료생', '졸업생'], ['3학년', '졸업생'])


def std_2nd_alloc(student, seatlist):
    ## [2025.8.] 좌석 배정 시 이전 단계 잔여 좌석도 활용하되, 학년별 좌석에 우선적으로 배치하도록 로직 수정
    return std_alloc(student, seatlist, [], ['3학년', '졸업생', '2학년'])

## [2025.8.] 추가 배정 시 생방송 진행하는 대신 input file 기반 시드 고정
def get_seed_from_file(filename):
    """input_data.csv 내용을 기반으로 reproducible seed 생성"""
    with open(filename, 'rb') as f:
        content = f.read()
    return int(hashlib.sha256(content).hexdigest(), 16) % (2**32)

def main():
    # if __name__=="__main__":
    # def and input
    infile_std = './input/input_data.csv'
    infile_seat = './input/seatlist.csv'

    student_all = csv_to_dict_std(infile_std)
    seatlist_all = csv_to_list_seat(infile_seat)

    # 배정 가능 좌석 필터링
    seatlist_open, seatlist_closed = [], []
    for seat in seatlist_all:
        if seat[3] == 'open':
            seatlist_open.append(seat)
        else:
            seatlist_closed.append(seat)

    print("[*]전체 학생 수: " + str(len(student_all)))
    result_3rd = std_3rd_alloc(student_all, seatlist_open)
    result_grad = std_grad_alloc(student_all, seatlist_open)
    result_2nd = std_2nd_alloc(student_all, seatlist_open)
    result_unmatched = std_alloc_unmatched(student_all, seatlist_open)

    result_total = {}  # 최종 결과
    result_total.update(result_3rd)
    result_total.update(result_grad)
    result_total.update(result_2nd)
    result_total.update(result_unmatched)

    print("[*]배정된 학생 수: " + str(len(result_total)))
    print("[+]미배정된 학생 수: " + str(len(student_all)))

    # print(student_all)
    # print(seatlist_open)
    # print(seatlist_closed)

    # 결과 출력
    with open('./output/seat_result.csv', mode='wt', encoding='UTF-8') as file:
        file.write("이름,학번뒤2자리,열람실,좌석번호\n")
        for key, value in result_total.items():
            name = key.split("_")[0]
            id = key.split("_")[1][-2:]  # 가명처리 목적으로 뒷 2자리만
            room = value[1]
            roomid = value[2]
            file.write(name + "," + id + "," + room + "," + roomid + "\n")
    print("[+]배치결과 저장 경로: ./output/seat_result.csv")

    # 남은 학생 출력
    with open('./output/seat_unmatched_student.csv', mode='wt', encoding='UTF-8') as file:
        file.write("이름_학번,학년,1지망,2지망,3지망\n")
        for key, value in student_all.items():
            file.write(key + "," + value[0] + "," + value[1] + "," + value[2] + "," + value[3] + "\n")
    print("[+]남은 학생 리스트 저장 경로: ./output/seat_unmatched_student.csv")

    # 남은 좌석 출력
    with open('./output/seat_unmatched_seat.csv', mode='wt', encoding='UTF-8') as file:
        unmatched_seats = {}
        for i in seatlist_open:
            file.write(i[0] + "," + i[1] + "," + i[2] + "," + i[3] + "\n")
        #     key = i[0] + "_" + i[1]
        #     if key not in unmatched_seats:
        #         unmatched_seats[key] = 0
        #     unmatched_seats[key] += 1
        # print(unmatched_seats)
        for i in seatlist_closed:
            file.write(i[0] + "," + i[1] + "," + i[2] + "," + i[3] + "\n")
    print("[+]남은 좌석 리스트 저장 경로: ./output/seat_unmatched_seat.csv")


def main_additional(infile_std, infile_result, infile_seat_unmatched, expected=None):
    # 전체 학생 목록
    student_all = csv_to_dict_std(infile_std)

    # 이미 배정된 학생 목록
    assigned = set()
    with open(infile_result, mode='rt', encoding='UTF-8') as file:
        next(file)  # header skip
        for line in file:
            parts = line.strip().split(",")
            if len(parts) >= 2:
                name = parts[0]
                id2 = parts[1]   # seat_result.csv에는 이미 학번 뒷 2자리만 남음
                key = name + "_" + id2
                assigned.add(key)

    # 배정 안 된 학생만 추출
    # student_all의 key는 "이름_전체학번"이라서 뒷자리만 잘라서 비교해야 함
    unassigned_students = {
        k: v for k, v in student_all.items()
        if (k.split("_")[0] + "_" + k.split("_")[1][-2:]) not in assigned
    }

    # 검증
    if expected is not None and expected != len(unassigned_students):
        raise ValueError(f"[!] 예상 추가 배정자 수 {expected}명과 실제 {len(unassigned_students)}명이 다릅니다.")

    # 좌석 불러오기 (unmatched seat 파일)
    seatlist_open = []
    with open(infile_seat_unmatched, mode='rt', encoding='UTF-8') as file:
        next(file)
        for row in csv.reader(file):
            if row[3] == 'open':
                seatlist_open.append(row)

    # seed 고정
    seed = get_seed_from_file(infile_std)
    random.seed(seed)

    # 배정 실행
    result_additional_2nd = std_2nd_alloc(unassigned_students, seatlist_open)
    result_additional_unmatched = std_alloc_unmatched(unassigned_students, seatlist_open)

    result_additional = {}  # 최종 결과
    result_additional.update(result_additional_2nd)
    result_additional.update(result_additional_unmatched)

    # 로그 출력
    print("[+] 추가 배정 결과:")
    for key, seat in result_additional.items():
        print(f" - {key}: {seat[1]} {seat[2]}번")

    # 추가 배정 결과 저장 (별도 파일)
    with open('./output/seat_result_additional.csv', mode='wt', encoding='UTF-8') as file:
        file.write("이름,학번뒤2자리,열람실,좌석번호\n")
        for key, value in result_additional.items():
            name = key.split("_")[0]
            id = key.split("_")[1][-2:]
            room = value[1]
            roomid = value[2]
            file.write(name + "," + id + "," + room + "," + roomid + "\n")
    print("[+] 추가 배치결과 저장 경로: ./output/seat_result_additional.csv")

    # seat_result.csv 에 append
    with open('./output/seat_result.csv', mode='at', encoding='UTF-8') as file:
        for key, value in result_additional.items():
            name = key.split("_")[0]
            id = key.split("_")[1][-2:]
            room = value[1]
            roomid = value[2]
            file.write(name + "," + id + "," + room + "," + roomid + "\n")
    print("[+] seat_result.csv 갱신 완료")

    # seat_unmatched_seat.csv 업데이트
    # → 원본 읽어서 result_additional 에 배정된 좌석 제거 후 다시 저장
    updated_seats = []
    with open('./output/seat_unmatched_seat.csv', mode='rt', encoding='UTF-8') as file:
        for row in csv.reader(file):
            updated_seats.append(row)

    # 배정된 좌석 key = (열람실, 좌석번호)
    allocated_keys = {(v[1], v[2]) for v in result_additional.values()}
    updated_seats = [s for s in updated_seats if (s[1], s[2]) not in allocated_keys]

    with open('./output/seat_unmatched_seat.csv', mode='wt', encoding='UTF-8', newline='') as file:
        writer = csv.writer(file)
        for s in updated_seats:
            writer.writerow(s)
    print("[+] seat_unmatched_seat.csv 갱신 완료")

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["normal", "add"], default="normal")
    parser.add_argument("--expected", type=int, default=None, help="추가 배정 예상 인원")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    infile_std = './input/input_data.csv'
    infile_seat = './input/seatlist.csv'

    if args.mode == "normal":
        main()
    else:
        main_additional(infile_std,
                        './output/seat_result.csv',
                        './output/seat_unmatched_seat.csv',
                        expected=args.expected)