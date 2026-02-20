import hashlib
import argparse

import check_input
import seat
import locker
from config import load_config


def print_file_hash(label, filepath):
    """파일 경로와 SHA256 해시를 출력합니다 (무결성 검증용)."""
    print(f"[***]{label} 경로 : {filepath}")
    with open(filepath, "rb") as f:
        data = f.read()
    print(f"[***]{label} 해시(SHA256) : {hashlib.sha256(data).hexdigest()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["normal", "add"],
                        help="normal: 전체 배정 / add: 추가 배정")
    parser.add_argument("--expected", type=int,
                        help="추가된 데이터 개수 검증용")
    args = parser.parse_args()

    config = load_config()
    paths = config['paths']
    mode = args.mode or "normal"

    # 입력값 해시 출력
    print_file_hash("입력값", paths['input_students'])

    # 입력 데이터 검증
    check_input.main(config)

    # 좌석 배정
    if mode == "normal":
        seat.main()
    else:
        seat.main_additional(
            paths['input_students'],
            paths['output_result'],
            paths['output_unmatched_seats'],
            expected=args.expected)

    # 사물함 배정
    locker.main(mode=mode)

    # 불변 검증용 입력값 해시 재출력
    print_file_hash("입력값", paths['input_students'])

    # 출력값 해시 출력
    print_file_hash("출력값", paths['output_locker_result'])
