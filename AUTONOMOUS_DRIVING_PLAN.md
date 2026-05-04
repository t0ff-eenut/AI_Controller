# 자율주행 구현 계획

## 전체 시스템 구조

```
[뎁스 카메라]
     ↓ USB 3.0
[AI Controller (RPi / Jetson)]  ← AI 추론, 경로 계획
     ↓ UART (115200bps)
[ESP32-C3 (BCU)]  ← 모터/서보 실행
     ↓
[DC모터 + 서보]
```

---

## 1. 뎁스 카메라 제품 비교

| 제품 | 가격 | RPi 호환 | 특징 | 추천도 |
|------|------|---------|------|--------|
| **Intel RealSense D435i** | ~₩200,000 | ✅ USB3 | IMU 내장, SDK 완성도 높음 | ⭐⭐⭐ |
| **Luxonis OAK-D Lite** | ~₩150,000 | ✅ USB3 | **온디바이스 AI 추론** 가능 | ⭐⭐⭐⭐ |
| **Luxonis OAK-D Pro** | ~₩300,000 | ✅ USB3 | 액티브 스테레오, 야간 지원 | ⭐⭐⭐ |

### 최종 추천: Luxonis OAK-D Lite
- Raspberry Pi의 낮은 연산 성능을 카메라 내 Myriad X 칩이 보완
- YOLO 같은 딥러닝 추론을 카메라 자체에서 처리 → RPi 부담 최소화
- 가볍고 작아서 1/10 RC카 탑재에 유리

---

## 2. AI Controller 선택

| 보드 | 특징 | 비고 |
|------|------|------|
| **Raspberry Pi 4B (4GB+)** | 현재 사용 중, OAK-D Lite와 조합 시 충분 | 기본 구성 |
| **NVIDIA Jetson Orin Nano** | CUDA 지원, 더 빠른 추론 | 고성능 필요 시 |

---

## 3. 소프트웨어 스택

```python
# 전체 파이프라인 (Python)

# 1단계: 뎁스 데이터 획득
import depthai as dai          # OAK-D Lite SDK
# 또는
import pyrealsense2 as rs      # RealSense SDK

# 2단계: 장애물 감지 + 경로 판단
import numpy as np
import cv2
# YOLO (Ultralytics) 또는 MobileNet-SSD

# 3단계: ESP32-C3에 제어 명령 전송 (기존 프로토콜 활용)
import serial
# CMD 0x01: speed(-100~100), steering(-100~100)
# CMD 0xFF: 비상 정지
```

---

## 4. 자율주행 알고리즘 구성

단계별 구현 순서:

1. **장애물 감지** — 뎁스맵에서 일정 거리 이내 장애물 감지 → 비상 정지 (CMD 0xFF)
2. **트랙 추종** — 색상/엣지 기반 차선 인식 + 조향 PID 제어
3. **속도 제어** — 직선 구간 가속 / 코너 감속 (곡률 기반)
4. **경로 계획** — 장애물 회피 (DWA 또는 단순 룰 기반)

---

## 5. BCU 통신 프로토콜 (ESP32-C3)

패킷 구조 (6 바이트):
`[STX(0xAA)] [CMD] [PARAM1] [PARAM2] [CHECKSUM] [ETX(0x55)]`

| CMD | 기능 | PARAM1 | PARAM2 |
|-----|------|--------|--------|
| `0x01` | 퍼센테이지 제어 (권장) | 스로틀 (-100~100) | 조향 (-100~100) |
| `0xFF` | 비상 정지 | - | - |

---

## 6. 게임 컨트롤러 무선 연결 (수동 조종)

### 연결 대상: Raspberry Pi (AI Controller)

컨트롤러 입력을 RPi에서 받아 `CMD 0x01` 패킷으로 변환 후 UART로 ESP32-C3에 전달하는 구조.
ESP32-C3에 직접 연결 시 BLE HID 파싱 + 모터 제어 동시 처리로 펌웨어 복잡도가 크게 증가하므로 권장하지 않음.

### 컨트롤러 비교

| 제품 | 연결 방식 | RPi 지원 | 추천도 | 비고 |
|------|---------|---------|--------|------|
| **8BitDo SN30 Pro** | Bluetooth | ✅ 완벽 | ⭐⭐⭐⭐⭐ | Linux 최적화, D모드 설정 |
| **PS4 DualShock 4** | Bluetooth | ✅ 좋음 | ⭐⭐⭐⭐ | 보급형, 국내 구하기 쉬움 |
| **PS5 DualSense** | Bluetooth | ✅ 좋음 | ⭐⭐⭐ | 지원은 되나 오버스펙 |
| **Xbox 무선 컨트롤러** | Bluetooth | ⚠️ 드라이버 필요 | ⭐⭐ | xpadneo 설치 필요 |
| **Logitech F710** | USB 동글 | ✅ 플러그앤플레이 | ⭐⭐⭐ | 무선이지만 USB 동글 차지 |

### 최종 추천: 8BitDo SN30 Pro
- RPi(Linux) 공식 지원, `evdev`/`pygame` 모두 바로 인식
- D모드(DirectInput)로 설정하면 추가 드라이버 불필요
- 버튼으로 수동/자율주행 모드 전환 구현에 적합

### Bluetooth 페어링

```bash
bluetoothctl
> power on
> agent on
> scan on
# 컨트롤러 페어링 버튼 누름
> pair XX:XX:XX:XX:XX:XX
> trust XX:XX:XX:XX:XX:XX
> connect XX:XX:XX:XX:XX:XX
```

### Python 제어 코드 구조

```python
import pygame
import serial

pygame.init()
pygame.joystick.init()
joystick = pygame.joystick.Joystick(0)

ser = serial.Serial('/dev/ttyUSB0', 115200)

while True:
    pygame.event.pump()

    throttle = int(joystick.get_axis(1) * -100)  # 좌측 스틱 상하
    steering = int(joystick.get_axis(0) * 100)   # 좌측 스틱 좌우

    # 버튼으로 모드 전환
    if joystick.get_button(9):   # START 버튼
        switch_to_autonomous()

    send_cmd_01(ser, throttle, steering)  # ESP32-C3로 UART 전송
```

### 수동/자율 모드 전환 구조

| 버튼 | 기능 |
|------|------|
| START | 자율주행 모드 전환 (뎁스 카메라 루프 시작) |
| SELECT | 수동 모드 전환 (컨트롤러 입력) |
| L2 | 비상 정지 (CMD 0xFF) |

---

## 7. 향후 구현 항목

**자율주행**
- [ ] OAK-D Lite + Raspberry Pi 연동 코드
- [ ] 뎁스맵 기반 장애물 회피 로직
- [ ] 기존 `rpi_pwm_control_example.py`에 자율주행 루프 통합
- [ ] PID 조향 제어기 구현
- [ ] 트랙 차선 인식 모듈

**수동 조종**
- [ ] 8BitDo SN30 Pro Bluetooth 페어링 및 연결 스크립트
- [ ] pygame 기반 컨트롤러 입력 → UART 변환 코드
- [ ] 수동/자율주행 모드 전환 로직
