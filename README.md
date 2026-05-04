# Pseudo F1 RC Car — AI Controller

Raspberry Pi 기반 AI Controller 소프트웨어.  
OAK-D Lite 뎁스 카메라로 자율주행을 수행하고, 게임 컨트롤러로 수동 조종을 지원하며,  
UART를 통해 ESP32-C3 BCU(Body Control Unit)에 제어 명령을 전송합니다.

---

## 목차

1. [시스템 구조](#시스템-구조)
2. [요구 사항](#요구-사항)
3. [설치](#설치)
4. [하드웨어 연결](#하드웨어-연결)
5. [설정](#설정)
6. [실행](#실행)
7. [모드 전환 버튼 매핑](#모드-전환-버튼-매핑)
8. [파일 구조](#파일-구조)

---

## 시스템 구조

```
[OAK-D Lite 뎁스 카메라]
        ↓ USB 3.0
[Raspberry Pi (AI Controller)]
        ↓ UART (115200bps)
[ESP32-C3 (BCU)]
        ↓
[DC모터 + 조향 서보]
```

---

## 요구 사항

| 항목 | 최소 사양 |
|------|---------|
| **보드** | Raspberry Pi 4B (4GB RAM 이상 권장) |
| **OS** | Raspberry Pi OS (64-bit, Bullseye 이상) |
| **Python** | 3.10 이상 |
| **카메라** | Luxonis OAK-D Lite |
| **컨트롤러** | 8BitDo SN30 Pro (Bluetooth) 또는 PS4 DualShock 4 |
| **USB** | USB 3.0 포트 (OAK-D Lite 연결용) |

---

## 설치

### 1. 저장소 클론

```bash
git clone https://github.com/t0ff-eenut/Pseudo_F1_Body_ESP32_C3.git
cd Pseudo_RC/AI_Controller
```

### 2. Python 가상환경 생성 및 의존성 설치

```bash
cd AI_Controller
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

> Raspberry Pi OS는 시스템 Python이 보호되어 있어 (`externally-managed-environment`)
> 반드시 가상환경을 사용해야 합니다.

> **OAK-D Lite USB 권한 설정 (Linux)**  
> 처음 한 번만 실행합니다.
> ```bash
> echo 'SUBSYSTEM=="usb", ATTRS{idVendor}=="03e7", MODE="0666"' | sudo tee /etc/udev/rules.d/80-movidius.rules
> sudo udevadm control --reload-rules && sudo udevadm trigger
> ```

---

## 하드웨어 연결

### ESP32-C3 BCU (UART)

| Raspberry Pi | ESP32-C3 |
|-------------|---------|
| GPIO 14 (TXD) | GPIO 21 (RXD) |
| GPIO 15 (RXD) | GPIO 20 (TXD) |
| GND | GND |

> `/dev/ttyUSB0` 또는 `/dev/ttyAMA0` 으로 인식됩니다.  
> `ls /dev/tty*` 로 포트를 확인한 뒤 `src/config.py`의 `BCU_PORT`를 수정하세요.

### OAK-D Lite

USB 3.0 포트에 직접 연결합니다.  
USB 2.0 포트에 연결하면 대역폭 부족으로 프레임 드롭이 발생할 수 있습니다.

### 게임 컨트롤러 (Bluetooth)

```bash
bluetoothctl
> power on
> agent on
> scan on
# 컨트롤러의 페어링 버튼을 누릅니다
> pair   XX:XX:XX:XX:XX:XX
> trust  XX:XX:XX:XX:XX:XX
> connect XX:XX:XX:XX:XX:XX
> quit
```

> **8BitDo SN30 Pro**: 전원을 켤 때 **START + B** 를 길게 눌러 **D모드(DirectInput)** 로 부팅해야  
> 추가 드라이버 없이 바로 인식됩니다.

---

## 설정

모든 설정은 `src/config.py` 에서 변경합니다.

### 주요 설정 항목

```python
# BCU 연결 포트 — ls /dev/ttyUSB* 로 확인
BCU_PORT = '/dev/ttyUSB0'

# 장애물 감지 거리 임계값 (mm)
# 이 거리 이하로 장애물이 감지되면 비상 정지
OBSTACLE_DIST_MM = 500

# 기본 주행 속도 / 감속 속도 (%)
SPEED_NORMAL = 40
SPEED_SLOW   = 20

# PID 조향 게인 (차선 추종 시 튜닝)
PID_KP = 0.5
PID_KI = 0.01
PID_KD = 0.1

# 게임 컨트롤러 버튼 인덱스
# pygame의 get_button() 인덱스와 일치해야 합니다
BTN_AUTONOMOUS = 9   # 자율주행 전환 (START)
BTN_MANUAL     = 8   # 수동 전환 (SELECT)
BTN_ESTOP      = 6   # 비상 정지 (L2)
```

### 버튼 인덱스 확인 방법

컨트롤러 모델마다 인덱스가 다를 수 있습니다.  
아래 명령으로 버튼을 눌러보며 인덱스를 확인하세요.

```bash
python3 - <<'EOF'
import pygame
pygame.init(); pygame.joystick.init()
js = pygame.joystick.Joystick(0); js.init()
print(f"컨트롤러: {js.get_name()}")
while True:
    pygame.event.pump()
    for i in range(js.get_numbuttons()):
        if js.get_button(i):
            print(f"버튼 {i} 눌림")
EOF
```

---

## 실행

```bash
cd AI_Controller
.venv/bin/python3 src/main.py
```

> 또는 가상환경을 활성화한 뒤 실행할 수도 있습니다.
> ```bash
> source .venv/bin/activate
> python3 src/main.py
> ```

### 컨트롤러 없이 실행 (자율주행 전용)

컨트롤러가 연결되지 않은 경우, 시작 시 자동으로 자율주행 모드로 진입합니다.

---

## 모드 전환 버튼 매핑

| 버튼 | 8BitDo SN30 Pro | 기능 |
|------|----------------|------|
| `BTN_AUTONOMOUS` (9) | START | 자율주행 모드 전환 |
| `BTN_MANUAL` (8) | SELECT | 수동 조종 모드 전환 |
| `BTN_ESTOP` (6) | L2 | 비상 정지 (CMD 0xFF 전송) |
| 좌측 스틱 상하 | Axis 1 | 스로틀 제어 |
| 좌측 스틱 좌우 | Axis 0 | 조향 제어 |

> PS4 DualShock 4 사용 시 버튼 인덱스가 다를 수 있습니다.  
> 위의 **버튼 인덱스 확인 방법**으로 확인 후 `config.py`를 수정하세요.

---

## 파일 구조

```
AI_Controller/
├── README.md                    ← 이 파일
├── CHANGELOG.md                 ← 버전별 변경 로그
├── AUTONOMOUS_DRIVING_PLAN.md   ← 자율주행 구현 계획서
├── requirements.txt             ← Python 의존성
└── src/
    ├── config.py        ← 전역 설정값
    ├── bcu_comm.py      ← ESP32-C3 UART 통신 (BCUComm 클래스)
    ├── depth_camera.py  ← OAK-D Lite DepthAI 파이프라인
    ├── controller.py    ← 게임 컨트롤러 입력 처리
    ├── autonomous.py    ← 자율주행 로직 (PID 조향, 장애물 회피)
    └── main.py          ← 진입점, 모드 전환 메인 루프
```
