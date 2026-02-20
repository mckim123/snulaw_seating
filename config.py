import yaml


def load_config(path='config.yaml'):
    with open(path, mode='rt', encoding='UTF-8') as f:
        config = yaml.safe_load(f)
    validate_config(config)
    return config


def validate_config(config):
    """config.yaml 내부 참조값이 valid 목록과 일치하는지 검증합니다."""
    valid_rooms = set(config.get('valid_rooms', []))
    valid_student_types = set(config.get('valid_student_types', []))
    valid_seat_types = set(config.get('valid_seat_types', []))

    errors = []

    # grade_to_seat_type 검증
    for student_type, seat_type in config.get('grade_to_seat_type', {}).items():
        if student_type not in valid_student_types:
            errors.append(f"grade_to_seat_type의 키 '{student_type}'이(가) valid_student_types에 없습니다.")
        if seat_type not in valid_seat_types:
            errors.append(f"grade_to_seat_type의 값 '{seat_type}'이(가) valid_seat_types에 없습니다.")

    # laptop_not_allowed_zones 검증
    for room in config.get('laptop_not_allowed_zones', []):
        if room not in valid_rooms:
            errors.append(f"laptop_not_allowed_zones의 '{room}'이(가) valid_rooms에 없습니다.")

    # phases 검증
    for i, phase in enumerate(config.get('phases', [])):
        name = phase.get('name', f'phase[{i}]')
        for st in phase.get('student_types', []):
            if st not in valid_student_types:
                errors.append(f"phases '{name}'의 student_types '{st}'이(가) valid_student_types에 없습니다.")
        for st in phase.get('seat_types', []):
            if st not in valid_seat_types:
                errors.append(f"phases '{name}'의 seat_types '{st}'이(가) valid_seat_types에 없습니다.")

    # locker_mapping 검증
    for room in config.get('locker_mapping', {}):
        if room not in valid_rooms:
            errors.append(f"locker_mapping의 열람실 '{room}'이(가) valid_rooms에 없습니다.")

    if errors:
        msg = "[!] config.yaml 검증 오류:\n" + "\n".join(f"  - {e}" for e in errors)
        raise ValueError(msg)
