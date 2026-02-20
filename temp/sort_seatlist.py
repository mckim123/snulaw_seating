"""
seatlist CSV를 열람실명 → 좌석번호(숫자) 순으로 정렬하여 덮어씁니다.

사용법: python temp/sort_seatlist.py [파일경로]
기본값: input/seatlist.csv
"""

import csv
import sys
import os


def sort_seatlist(filepath):
    with open(filepath, mode='rt', encoding='UTF-8') as f:
        reader = csv.reader(f)
        header = next(reader)
        rows = [row for row in reader if len(row) >= 4]

    before = len(rows)

    # 열람실명(문자열) → 좌석번호(숫자) 순 정렬
    rows.sort(key=lambda r: (r[1], int(r[2])))

    with open(filepath, mode='wt', encoding='UTF-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)

    print(f"[+] {filepath}: {before}행 정렬 완료")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        path = sys.argv[1]
    else:
        path = os.path.join("input", "seatlist.csv")
    sort_seatlist(path)
