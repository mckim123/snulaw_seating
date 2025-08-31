import hashlib
import argparse
import subprocess

import check_input
import test

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["normal", "add"],
                        help="normal: 전체 배정 / add: 추가 배정")
    parser.add_argument("--expected", type=int,
                        help="추가된 데이터 개수 검증용")
    args = parser.parse_args()

    # input_data.csv 해시값 출력
    print("[***]입력값 경로 : ./input/input_data.csv")
    with open("./input/input_data.csv", "rb") as f:
        data = f.read()
    print("[***]입력값 해시(SHA256) : " + hashlib.sha256(data).hexdigest())

    # 입력 데이터 검증
    check_input.main()

    # 좌석 배정 (seat.py)
    seat_cmd = ["python", "seat.py"]
    if args.mode:
        seat_cmd += ["--mode", args.mode]
    if args.expected:
        seat_cmd += ["--expected", str(args.expected)]
    subprocess.run(seat_cmd, check=True)

    # 사물함 배정 (drawer.py)
    drawer_cmd = ["python", "drawer.py"]
    if args.mode:
        drawer_cmd += ["--mode", args.mode]
    subprocess.run(drawer_cmd, check=True)

    # 불변 검증용 input_data.csv 해시값 출력
    print("[***]입력값 경로 : ./input/input_data.csv")
    with open("./input/input_data.csv", "rb") as f:
        data = f.read()
    print("[***]입력값 해시(SHA256) : " + hashlib.sha256(data).hexdigest())

    # seat_drawer_result.csv 해시값 출력
    print("[***]출력값 경로 : ./output/seat_drawer_result.csv")
    with open("./output/seat_drawer_result.csv", "rb") as f:
        data = f.read()
    print("[***]출력값 해시(SHA256) : " + hashlib.sha256(data).hexdigest())

    # test.main()
