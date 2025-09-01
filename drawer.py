import random
import csv
import argparse
import hashlib
from collections import defaultdict

DEFAULT_INDICES = {
    "bg": 53,   # 법오 골방 : 53~64
    "bkp": 65,  # 법오 큰방 평상 : 65~96
    "bkk": 97,  # 법오 큰방 칸막이 : 97~348
    "bj": 1,    # 법오 작은방 1~52
    "hp": 1,    # 해동(401호) 평상 1~38
    "hk": 39,   # 해동(401호) 칸막이 39~54
    "fa": 55,   # 404호 - 404(A) 55~66
    "fb": 1,    # 404호 - 404(B) 1~150
    "ys": 1,    # 역사관 - 서암 1~34
    "gs": 81,   # 국산 - 81~162
}

## [2025.8.] 추가 배정 시 생방송 진행하는 대신 input file 기반 시드 고정
def get_seed_from_file(filename):
    """input_data.csv 내용을 기반으로 reproducible seed 생성"""
    with open(filename, 'rb') as f:
        content = f.read()
    return int(hashlib.sha256(content).hexdigest(), 16) % (2**32)

def load_indices_from_existing(file_path):
    """
    seat_drawer_result.csv 파일을 읽어, 이미 배정된 사물함 번호들의 max값을 기반으로
    시작 인덱스들을 갱신해준다.
    """
    indices = DEFAULT_INDICES.copy()

    try:
        with open(file_path, mode='rt', encoding='UTF-8') as csvfile:
            csvreader = csv.reader(csvfile)
            next(csvreader)  # header skip
            for row in csvreader:
                locker_room = row[4]
                locker_num = int(row[5])

                if locker_room == "법오 큰방":
                    if 53 <= locker_num <= 64:   # 골방
                        indices["bg"] = max(indices["bg"], locker_num + 1)
                    elif 65 <= locker_num <= 96:  # 큰방 평상
                        indices["bkp"] = max(indices["bkp"], locker_num + 1)
                    else:  # 큰방 칸막이
                        indices["bkk"] = max(indices["bkk"], locker_num + 1)
                elif locker_room == "법오 작은방":
                    indices["bj"] = max(indices["bj"], locker_num + 1)
                elif locker_room == "404(A)":
                    if locker_num <= 38:
                        indices["hp"] = max(indices["hp"], locker_num + 1)
                    elif 39 <= locker_num <= 54:
                        indices["hk"] = max(indices["hk"], locker_num + 1)
                    elif 55 <= locker_num <= 66:
                        indices["fa"] = max(indices["fa"], locker_num + 1)
                elif locker_room == "404(B)":
                    indices["fb"] = max(indices["fb"], locker_num + 1)
                elif locker_room == "국산":
                    if 81 <= locker_num <= 162:
                        indices["gs"] = max(indices["gs"], locker_num + 1)
                elif locker_room == "서암":
                    if locker_num <= 34:  # 역사관 평상
                        indices["ys"] = max(indices["ys"], locker_num + 1)
    except FileNotFoundError:
        print(f"[!] 기존 파일 {file_path} 없음. 기본 인덱스로 진행하나, 반드시 수작업 필요")

    return indices


def main(mode="normal"):
    # 좌석배치 완료된 파일에서 정보 입력
    student = []
    result = []
    indices = DEFAULT_INDICES.copy()

    if mode == "normal":
        file_path = "./output/seat_result.csv"
    else:
        file_path = "./output/seat_result_additional.csv"
        seed = get_seed_from_file(file_path)
        random.seed(seed)
        indices = load_indices_from_existing("./output/seat_drawer_result.csv")

    with open(file_path, mode='rt', encoding='UTF-8', newline='') as csvfile:
        csvreader = csv.reader(csvfile)
        next(csvreader)  # 첫 번째 행 skip
        for row in csvreader:
            student.append(row)
    random.shuffle(student)

    failed = defaultdict(int)

    for std in student:
        if std[2] == '법오 골방(칸막이)':
            drawer = ['법오 큰방', indices["bg"]]
            indices["bg"] += 1
        elif std[2] == '법오 큰방(평상)':
            drawer = ['법오 큰방', indices["bkp"]]
            indices["bkp"] += 1
        elif std[2] == '법오 큰방(칸막이)':
            drawer = ['법오 큰방', indices["bkk"]]
            indices["bkk"] += 1
        elif std[2] == '법오 작은방(평상)':
            drawer = ['법오 작은방', indices["bj"]]
            indices["bj"] += 1
        elif std[2] == '15동 401호(평상)':
            drawer = ['404(A)', indices["hp"]]
            indices["hp"] += 1
        elif std[2] == '15동 401호(칸막이)':
            drawer = ['404(A)', indices["hk"]]
            indices["hk"] += 1
        elif std[2] == '15동 404호(칸막이)':
            if indices["fa"] <= 66:
                drawer = ['404(A)', indices["fa"]]
                indices["fa"] += 1
            else:
                drawer = ['404(B)', indices["fb"]]
                indices["fb"] += 1
        elif std[2] == '역사관(평상)':
            drawer = ['서암', indices["ys"]]
            indices["ys"] += 1
        elif std[2] == '국산(칸막이)':
            drawer = ['국산', indices["gs"]]
            indices["gs"] += 1
        else:
            failed[std[2]] += 1
            continue
        result.append(std + drawer)

    # 인덱스 초과 체크
    if indices["bg"] > 65:
        print("[-] 골방 사물함 넘버 초과")
    if indices["bkp"] > 97:
        print("[-] 큰방 평상 사물함 넘버 초과")
    if indices["bkk"] > 349:
        print("[-] 큰방 칸막이 사물함 넘버 초과")
    if indices["bj"] > 53:
        print("[-] 작은방 사물함 넘버 초과")
    if indices["hp"] > 39:
        print("[-] 401 평상 사물함 넘버 초과")
    if indices["hk"] > 55:
        print("[-] 401 칸막이 사물함 넘버 초과")
    if indices["fa"] > 67:
        print("[-] 404A 사물함 넘버 초과")
    if indices["fb"] > 151:
        print("[-] 404B 사물함 넘버 초과")
    if indices["ys"] > 35:
        print("[-] 역사관 사물함 넘버 초과")
    if indices["gs"] > 163:
        print("[-] 국산 사물함 넘버 초과")

    if len(result) != len(student):
        print("[-] 전체 숫자 안맞음. 데이터 오타 확인할 것")
        print(f"[-] len(result), len(student), err_cnt: {len(result)}, {len(student)}, {sum(failed.values())}")

    if failed:
        for k, v in failed.items():
            print(f"열람실(또는 오류 종류): {k}, 실패 횟수: {v}")

    # 결과 출력
    with open('./output/seat_drawer_result.csv', mode='at' if mode == "add" else 'wt', encoding='utf-8') as file:
        if mode == "normal":
            file.write("이름,학번뒤2자리,열람실,좌석번호,사물함,사물함번호\n")
        for r in result:
            file.write(r[0] + "," + r[1] + "," + r[2] + "," + r[3] + "," + r[4] + "," + str(r[5]) + "\n")

    print('[+]좌석 및 사물함 배치 결과 저장 경로: ./output/seat_drawer_result.csv')

    if mode == "add":
        with open('./output/seat_drawer_result_additional.csv', mode='wt', encoding='utf-8') as file:
            file.write("이름,학번뒤2자리,열람실,좌석번호,사물함,사물함번호\n")
            for r in result:
                file.write(r[0] + "," + r[1] + "," + r[2] + "," + r[3] + "," + r[4] + "," + str(r[5]) + "\n")

        print('[+]좌석 및 사물함 추가 배치 결과 저장 경로: ./output/seat_drawer_result_additional.csv')

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["normal", "add"], default="normal")
    args = parser.parse_args()

    main(mode=args.mode)