# SNU Law School 좌석 배정 시스템

## Requirement
- Python 3
- `pip install -r requirements.txt`

## 사용 방법

### 1. 사전 준비

#### (1) config.yaml 수정
매 학기 변경사항(열람실 구성, 배정 정책 등)이 있으면 `config.yaml`을 수정합니다.
- `valid_rooms`: 배정 대상 열람실 목록
- `grade_to_seat_type`: 학년별 우선 배정 좌석 유형
- `phases`: 배정 단계 설정
- `locker_mapping`: 사물함 매핑

#### (2) seatlist.csv 수정
좌석 구성에 변화가 있다면 `input/seatlist.csv`를 수정합니다.
- **좌석 유형 수정**: 각 좌석의 `학년` 열 값을 조정 (예: "2학년", "3학년", "졸업생")
- **폐쇄 열람실**: 이전 학기에 사용했던 열람실은 `input/seatlist_archived.csv`에 보관되어 있습니다. 필요시 참조하거나 복구할 수 있습니다.

#### (3) 설정 미리보기로 검증
```bash
python preview.py
```
좌석 현황(열람실별/학년별/상태별 좌석 수), 좌석 중복 검증, 사물함 매핑을 통합 출력합니다.
- **반드시 확인**: 공지한 좌석 유형별 개수와 실제 `seatlist.csv`의 좌석 개수가 일치하는지 확인
- `config_preview.txt` 파일도 함께 생성되어 git diff로 변경사항 추적 가능

### 2. 본 배정
1. 입력받은 설문 시트를 그대로 CSV로 출력 후 `input/input_data.csv`에 저장
2. `python run.py` 실행
3. `output/seat_locker_result.csv` 확인 및 검증
4. 입력값, 결과값 무결성 검증 위해 해시값 및 파일 백업 필요

### 3. 미응답자 추가 배정
1. 입력받은 설문 시트를 그대로 CSV로 출력 후 `input/input_data.csv`에 저장 (이미 배정한 응답도 포함)
2. `python run.py --mode=add --expected=2` 실행 (expected에는 추가배정해야하는 인원 입력)
3. `output/seat_locker_result_additional.csv` 확인 및 검증

### 4. 시뮬레이션 (선택)
```bash
python simulate.py --runs=100
```
서로 다른 시드로 100번 배정을 실행하여 열람실별 빈자리 평균/최소/최대/표준편차를 출력합니다.
좌석 구성이나 배정 단계를 변경하기 전에, 시뮬레이션으로 빈자리 분포를 미리 확인할 수 있습니다.

## 배정 로직 (4단계)

좌석 배정은 다음 4단계로 순차 실행됩니다 (`config.yaml`의 `phases` 참조):

1. **3학년 배정**: 3학년+수료생을 '3학년' 좌석에 1지망→2지망→3지망 순으로 배정
2. **3학년+졸업생 배정**: 3학년+수료생+졸업생을 '3학년'+'졸업생' 좌석에 배정 (1단계 잔여 좌석 포함)
3. **전체 학생 배정**: 남은 전체 학생을 '3학년'+'졸업생'+'2학년' 좌석에 배정
4. **잔여석 배정**: 아직 미배정된 학생을 남은 좌석에 랜덤 배정 (1~3지망 중 노트북 금지 열람실을 신청한 학생은 구분 없이, 그 외는 허용 열람실 우선)

각 단계 내에서:
- 학생 처리 순서는 매번 랜덤 셔플 (공정성)
- 학년에 맞는 좌석 타입 우선 배정 (예: 1학년 → '2학년' 좌석 우선)

## config.yaml 설정 가이드

### valid_rooms / valid_student_types / valid_seat_types
허용되는 열람실, 학년/지위, 좌석 타입 목록. 입력 데이터 검증에 사용됩니다.

### grade_to_seat_type
학년/지위별 우선 배정 좌석 유형. 예) `1학년: "2학년"` → 1학년은 2학년 좌석에 우선 배정.

### laptop_not_allowed_zones
노트북 사용 불가 열람실 목록. 잔여석 배정 시 이 열람실은 후순위.

### phases
배정 단계 설정. `type`이 `preference`이면 1~3지망 매칭, `unmatched`이면 잔여석 랜덤 배정.
`student_types`가 비어있으면 전체 학생 대상. `seat_types`가 비어있으면 전체 좌석 대상.

### add_mode_phase_indices
추가 배정(--mode=add) 시 실행할 단계 인덱스 (0부터 시작). 기본값 [2, 3]은 3단계+4단계만 실행.

### locker_mapping
열람실 → 사물함 매핑. `lockers` 리스트의 순서대로 채우며, 첫 번째가 가득 차면 다음으로 overflow.
`start`~`end`는 사물함 번호 범위 (inclusive).

## 파일 구성

### 메인 파일
- **run.py**: 메인 파일. `python run.py` 실행
- **config.yaml**: 설정 파일. 학년 매핑, 배정 단계, 사물함 매핑 등 모든 설정이 여기에 있음

### 입력 파일
- **input/input_data.csv**: 설문 응답 CSV (타임스탬프, 이메일, 이름, 학번, 학년, 1~3지망)
- **input/seatlist.csv**: 열람실 좌석 리스트 (학년, 열람실, 번호, 배치유무)
- **input/seatlist_archived.csv**: 이전 학기 좌석 리스트 (참조용)

### 출력 파일
- **output/seat_result.csv**: 각 인원별 배정 결과 (이름, 학번뒤2자리, 열람실, 좌석번호)
- **output/seat_locker_result.csv**: 최종 결과 (사물함 배정 포함)
  - **주의**: UTF-8 인코딩. 엑셀에서 열 때 인코딩 변환 필요 (엑셀→데이터→텍스트/CSV에서→UTF-8 선택)
- **output/seat_unmatched_student.csv**: 미배정 학생 리스트 (비어있는게 정상)
- **output/seat_unmatched_seat.csv**: 잔여 좌석 리스트

### 보조 파일
- **check_input.py**: 입력 데이터 검증 (중복 체크, 좌석수-학생수 비교, 유효성 검증)
- **seat.py**: 좌석 배정 로직
- **locker.py**: 사물함 배정 로직
- **stats.py**: 배정 결과 통계 (열람실별 1지망/2지망/3지망 충족률)
- **simulate.py**: 시뮬레이션 (열람실별 빈자리 통계 분석)
- **preview.py**: 설정 미리보기 (좌석 현황, 중복 검증, 사물함 매핑)
- **config_preview.txt**: preview.py 실행 시 생성되는 설정 미리보기 파일 (git diff 추적용)
- **temp/gen_sample.py**: 테스트용 샘플 데이터 생성기
- **temp/sort_seatlist.py**: 좌석 리스트 정렬 유틸리티
