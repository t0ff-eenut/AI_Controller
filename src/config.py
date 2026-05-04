# =============================================================================
# config.py - 전역 설정값
# =============================================================================

# --- BCU (ESP32-C3) UART 설정 ---
BCU_PORT     = '/dev/ttyUSB0'   # 시리얼 포트 (ls /dev/ttyUSB* 로 확인)
BCU_BAUDRATE = 115200

# --- BCU 패킷 프로토콜 ---
PKT_STX = 0xAA
PKT_ETX = 0x55
CMD_HEARTBEAT   = 0x00   # 연결 확인 → ESP32가 CMD_ACK로 응답
CMD_PERCENTAGE  = 0x01   # 스로틀/조향 퍼센테이지 제어 (param: -100 ~ +100)
CMD_BRAKE       = 0x03   # 브레이크 (param1: 전륜 강도, param2: 후륜 강도, 0~100)
CMD_ACK         = 0xA0   # Heartbeat 응답 (ESP32 → RPi)
CMD_ESTOP       = 0xFF   # 비상 정지

# --- Heartbeat 설정 ---
HEARTBEAT_INTERVAL  = 0.2   # Heartbeat 전송 주기 (초) — Failsafe 500ms 이내
HEARTBEAT_TIMEOUT   = 1.0   # ACK 미수신 시 연결 끊김 판정 시간 (초)

# --- OAK-D Lite 뎁스 카메라 설정 ---
DEPTH_FPS           = 30
DEPTH_RESOLUTION    = 'THE_400_P'   # 400p (OAK-D Lite 최대)
OBSTACLE_DIST_MM    = 500           # 장애물 감지 거리 임계값 (mm)
DEPTH_ROI_TOP       = 0.3           # 관심 영역 상단 비율 (전방 영역만 사용)
DEPTH_ROI_BOTTOM    = 0.7           # 관심 영역 하단 비율

# --- 주행 파라미터 ---
SPEED_NORMAL    = 40    # 기본 주행 속도 (%)
SPEED_SLOW      = 20    # 장애물 근접 시 감속 속도 (%)
STEER_MAX       = 60    # 최대 조향 각도 (%)

# --- PID 조향 제어 (차선 추종 시 사용) ---
PID_KP = 0.5
PID_KI = 0.01
PID_KD = 0.1

# --- 컨트롤러 설정 ---
JOYSTICK_INDEX      = 0      # pygame 조이스틱 인덱스
AXIS_THROTTLE       = 1      # 좌측 스틱 상하축
AXIS_STEER          = 0      # 좌측 스틱 좌우축
BTN_AUTONOMOUS      = 9      # 자율주행 모드 전환 버튼 (START)
BTN_MANUAL          = 8      # 수동 모드 전환 버튼 (SELECT)
BTN_ESTOP           = 6      # 비상 정지 버튼 (L2)
AXIS_DEADZONE       = 0.05   # 스틱 데드존 (5%)
