# 변경 로그 (Changelog)

모든 주요 변경 사항은 이 파일에 기록됩니다.
형식은 [Keep a Changelog](https://keepachangelog.com/ko/1.0.0/)를 따릅니다.

---

## [Unreleased]

### 추가 예정
- 차선 인식 모듈 (`_compute_lane_error` 구현)
- YOLO 기반 객체 감지 노드 (OAK-D 온디바이스)
- 곡률 기반 코너 감속 로직

---

## [0.5.0] - 2026-05-01

### 추가
- **BCU Heartbeat + ACK 양방향 연결 확인** 구현
  - `ESP32 RCcar_protocol.h`: `CMD_ACK = 0xA0` 추가
  - `ESP32 RCcar_control.c`: `CMD_HEARTBEAT` 수신 시 ACK 패킷 응답 전송
  - `config.py`: `CMD_ACK`, `HEARTBEAT_INTERVAL(0.2s)`, `HEARTBEAT_TIMEOUT(1.0s)` 추가
  - `bcu/bcu_comm.py`: 수신 스레드(`_rx_loop`), Heartbeat 스레드(`_heartbeat_loop`) 추가
  - `bcu/bcu_comm.py`: `connect()` 시 ACK 수신으로 실제 연결 검증 (3회 재시도)
  - `bcu/bcu_comm.py`: `is_alive` 프로퍼티 — 마지막 ACK 기준 연결 상태 반환
  - `main.py`: 메인 루프에서 `is_alive` 체크 → 끊기면 자동 비상 정지

### 변경
- `bcu/bcu_comm.py`: UART `timeout` 을 `1` → `0.1`로 변경 (수신 스레드 응답성 개선)
- `bcu/bcu_comm.py`: `_lock` → `_tx_lock` 으로 명칭 변경 (TX 전용 명확화)

---

## [0.4.0] - 2026-05-01

### 추가
- `src/` 하위 모듈별 패키지 폴더 분리
  - `src/bcu/bcu_comm.py` — BCU UART 통신
  - `src/camera/depth_camera.py` — 뎁스 카메라
  - `src/gamepad/controller.py` — 게임 컨트롤러 입력
  - `src/ai/autonomous.py` — 자율주행 로직
  - 각 패키지에 `__init__.py` 생성

### 수정
- **모터 출력 스케일링 버그 수정**: Python `100` 전송 시 ESP32 실제 출력 78.7% 문제
  - `send_control()`: `speed/steering * 127 // 100` 으로 0~127 네이티브 범위 변환
  - `send_brake()`: `front/rear * 127 // 100` 으로 동일 변환 적용
- **체크섬 계산 방식 수정**: `(CMD + P1 + P2) & 0xFF` (합산) → `CMD ^ P1 ^ P2` (XOR)
  - 펌웨어 `RCcar_protocol.c` 실제 구현과 일치하도록 수정 (이전 코드는 패킷이 항상 거부됐음)
- `controller.py`: `_joystick`이 `None`일 때 `read()` 호출 시 `AttributeError` 수정
  - 미연결 시 더미 상태(`_DUMMY_STATE`) 반환으로 변경

### 변경
- `main.py`: import 경로를 패키지 구조에 맞게 수정 (`bcu.bcu_comm`, `camera.depth_camera` 등)

---

## [0.3.0] - 2026-05-01

### 추가
- `config.py`: 누락된 명령어 추가 — `CMD_HEARTBEAT(0x00)`, `CMD_BRAKE(0x03)`
- `bcu_comm.py`: `send_brake()`, `send_heartbeat()` 메서드 추가
- `main.py`: `--dry-run` 옵션 추가 (`argparse`)
  - BCU/카메라 없이 실행 가능, 전송 명령을 로그로만 출력
  - `BCUComm(dry_run=True)` 전파, 수신 스레드/포트 오픈 생략
- `controller.py`: 컨트롤러 미연결 시 더미 입력 반환 (`_DUMMY_STATE`)
- `depth_camera.py`: `start()` 반환값을 `bool`로 변경, 카메라 미연결 시 `False` 반환
- `main.py`: 카메라/컨트롤러 미연결 조합에 따른 시작 모드 자동 결정 로직 추가
  - 카메라 없음 → 수동 모드 강제
  - 컨트롤러 없음 → 자율주행 모드 강제
  - 둘 다 없음 → 종료 (dry-run 제외)

### 수정
- `depth_camera.py`: 파이프라인 빌드를 `__init__` → `start()` 시점으로 지연
  - 카메라 미연결 상태에서 프로그램 시작 시 `RuntimeError` 발생하던 문제 수정

---

## [0.2.1] - 2026-05-01

### 추가
- `README.md`: 설치, 하드웨어 연결, 설정, 실행 방법 문서화
  - USB 권한 설정, Bluetooth 페어링, 버튼 인덱스 확인 방법 포함

---

## [0.2.0] - 2026-05-01

### 추가
- `src/` 디렉터리 하위에 Python 뼈대 코드 생성
  - `config.py`: 전역 설정값 (포트, PID 게인, 버튼 매핑 등)
  - `bcu_comm.py`: ESP32-C3 UART 통신 (`BCUComm` 클래스, 패킷 인코딩)
  - `depth_camera.py`: OAK-D Lite DepthAI 파이프라인 + 장애물 감지
  - `controller.py`: pygame 기반 게임 컨트롤러 입력 처리
  - `autonomous.py`: PID 조향 + 속도 결정 자율주행 로직
  - `main.py`: 수동/자율 모드 전환 메인 루프 (30Hz, SIGINT 처리)
- `requirements.txt`: 의존성 목록 (depthai, pyserial, pygame, opencv, numpy)

---

## [0.1.1] - 2026-05-01

### 추가
- `AUTONOMOUS_DRIVING_PLAN.md`: 게임 컨트롤러 무선 연결 섹션 추가 (섹션 6)
  - 컨트롤러 제품 비교표 (8BitDo SN30 Pro 최종 추천)
  - Bluetooth 페어링 방법
  - pygame 기반 Python 제어 코드 구조
  - 수동/자율주행 모드 전환 버튼 매핑
- 향후 구현 항목에 수동 조종 관련 항목 추가

---

## [0.1.0] - 2026-05-01

### 추가
- 프로젝트 초기 구성
- `AUTONOMOUS_DRIVING_PLAN.md`: 자율주행 구현 계획 문서 작성
  - 뎁스 카메라 제품 비교 (OAK-D Lite 최종 추천)
  - AI Controller 하드웨어 선택 가이드
  - 소프트웨어 스택 정의
  - 자율주행 알고리즘 단계별 구성
  - BCU(ESP32-C3) 통신 프로토콜 정리

---

<!-- 변경 로그 작성 가이드
## [버전] - YYYY-MM-DD
### 추가 (Added)       - 새로운 기능
### 변경 (Changed)     - 기존 기능 변경
### 수정 (Fixed)       - 버그 수정
### 제거 (Removed)     - 삭제된 기능
### 보안 (Security)    - 보안 관련 수정
-->
