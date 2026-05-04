# =============================================================================
# bcu_comm.py - ESP32-C3 BCU UART 통신 모듈
# 패킷 구조: [STX(0xAA)] [CMD] [PARAM1] [PARAM2] [CHECKSUM] [ETX(0x55)]
# CHECKSUM  = CMD ^ PARAM1 ^ PARAM2  (XOR, 펌웨어 RCcar_protocol.c 기준)
# =============================================================================

import serial
import threading
import time
import logging
from config import (
    BCU_PORT, BCU_BAUDRATE,
    PKT_STX, PKT_ETX,
    CMD_HEARTBEAT, CMD_PERCENTAGE, CMD_BRAKE, CMD_ACK, CMD_ESTOP,
    HEARTBEAT_INTERVAL, HEARTBEAT_TIMEOUT,
)

logger = logging.getLogger(__name__)

PKT_SIZE = 6   # 패킷 고정 크기


class BCUComm:
    def __init__(self, dry_run: bool = False):
        self._ser: serial.Serial | None = None
        self._tx_lock   = threading.Lock()
        self._dry_run   = dry_run

        # --- ACK 수신 상태 ---
        self._last_ack_time: float = 0.0   # 마지막 ACK 수신 시각
        self._ack_event = threading.Event() # send_heartbeat() 동기 대기용

        # --- 수신 스레드 ---
        self._rx_thread: threading.Thread | None = None
        self._running = False

        # --- Heartbeat 스레드 ---
        self._hb_thread: threading.Thread | None = None

    # ------------------------------------------------------------------
    # 연결 관리
    # ------------------------------------------------------------------
    def connect(self) -> bool:
        if self._dry_run:
            logger.info("[DRY-RUN] BCU 연결 생략")
            self._last_ack_time = time.time()
            return True

        try:
            self._ser = serial.Serial(BCU_PORT, BCU_BAUDRATE, timeout=0.1)
        except serial.SerialException as e:
            logger.error(f"BCU 포트 열기 실패: {e}")
            return False

        # 수신 스레드 시작
        self._running = True
        self._rx_thread = threading.Thread(target=self._rx_loop, daemon=True, name='bcu-rx')
        self._rx_thread.start()

        # Heartbeat 를 보내고 ACK 를 기다려 실제 연결 확인
        logger.info(f"BCU 포트 열림: {BCU_PORT} — ACK 대기 중...")
        if not self._verify_connection():
            logger.error("BCU ACK 없음 — ESP32 미연결 또는 펌웨어 오류")
            self.disconnect()
            return False

        # ACK 확인 후 주기적 Heartbeat 스레드 시작
        self._hb_thread = threading.Thread(target=self._heartbeat_loop, daemon=True, name='bcu-hb')
        self._hb_thread.start()

        logger.info("BCU 연결 확인 완료 (ACK 수신)")
        return True

    def _verify_connection(self, retries: int = 3, timeout: float = 1.0) -> bool:
        """Heartbeat 전송 후 ACK 수신 여부로 연결을 검증."""
        for attempt in range(1, retries + 1):
            self._ack_event.clear()
            self._send_packet(CMD_HEARTBEAT, 0, 0)
            if self._ack_event.wait(timeout):
                return True
            logger.warning(f"ACK 대기 타임아웃 ({attempt}/{retries})")
        return False

    def disconnect(self):
        self._running = False
        if self._dry_run:
            return
        if self._ser and self._ser.is_open:
            self.estop()
            self._ser.close()
        logger.info("BCU 연결 종료")

    # ------------------------------------------------------------------
    # 수신 스레드 — 패킷 파싱
    # ------------------------------------------------------------------
    def _rx_loop(self):
        buf = bytearray()
        while self._running:
            try:
                chunk = self._ser.read(PKT_SIZE)
            except serial.SerialException:
                break

            if not chunk:
                continue

            buf.extend(chunk)

            # STX 동기화: STX 이전 바이트 버림
            while buf and buf[0] != PKT_STX:
                buf.pop(0)

            # 완성 패킷 처리
            while len(buf) >= PKT_SIZE:
                pkt = buf[:PKT_SIZE]
                buf = buf[PKT_SIZE:]

                if not self._validate_packet(pkt):
                    continue

                self._handle_rx_packet(pkt)

    @staticmethod
    def _validate_packet(pkt: bytes) -> bool:
        if pkt[0] != PKT_STX or pkt[5] != PKT_ETX:
            return False
        expected_cs = pkt[1] ^ pkt[2] ^ pkt[3]
        return expected_cs == pkt[4]

    def _handle_rx_packet(self, pkt: bytes):
        cmd = pkt[1]
        if cmd == CMD_ACK:
            self._last_ack_time = time.time()
            self._ack_event.set()
            logger.debug("ACK 수신")
        else:
            logger.debug(f"RX 알 수 없는 CMD: 0x{cmd:02X}")

    # ------------------------------------------------------------------
    # Heartbeat 스레드
    # ------------------------------------------------------------------
    def _heartbeat_loop(self):
        while self._running:
            time.sleep(HEARTBEAT_INTERVAL)
            self._ack_event.clear()
            self._send_packet(CMD_HEARTBEAT, 0, 0)

            if not self._ack_event.wait(HEARTBEAT_TIMEOUT):
                logger.warning("BCU Heartbeat ACK 없음 — 연결 끊김 의심")

    # ------------------------------------------------------------------
    # 연결 상태 확인 (외부 조회용)
    # ------------------------------------------------------------------
    @property
    def is_alive(self) -> bool:
        """마지막 ACK 수신 후 HEARTBEAT_TIMEOUT 이내이면 True."""
        if self._dry_run:
            return True
        return (time.time() - self._last_ack_time) < HEARTBEAT_TIMEOUT

    # ------------------------------------------------------------------
    # 패킷 전송 (내부)
    # ------------------------------------------------------------------
    def _send_packet(self, cmd: int, param1: int, param2: int):
        if self._dry_run:
            label = {CMD_ESTOP: 'ESTOP', CMD_HEARTBEAT: 'HEARTBEAT'}.get(cmd, f'0x{cmd:02X}')
            logger.info(f"[DRY-RUN] TX → CMD={label}  P1={param1:+4d}  P2={param2:+4d}")
            return

        if not self._ser or not self._ser.is_open:
            logger.warning("BCU 미연결 상태에서 전송 시도")
            return

        p1 = max(-127, min(127, int(param1)))
        p2 = max(-127, min(127, int(param2)))
        checksum = cmd ^ (p1 & 0xFF) ^ (p2 & 0xFF)
        packet = bytes([PKT_STX, cmd, p1 & 0xFF, p2 & 0xFF, checksum, PKT_ETX])

        with self._tx_lock:
            self._ser.write(packet)

    # ------------------------------------------------------------------
    # 공개 API
    # ------------------------------------------------------------------
    def send_control(self, speed: int, steering: int):
        """
        CMD 0x01: 퍼센테이지 제어 (권장 방식)
        speed    : -100 ~ 100  (음수=후진, 양수=전진)
        steering : -100 ~ 100  (음수=좌, 양수=우)
        ESP32 모터 듀티: |value| * 1023 / 127  → 0~100%를 0~127로 스케일
        """
        speed    = max(-100, min(100, int(speed)))
        steering = max(-100, min(100, int(steering)))
        hw_speed    = speed    * 127 // 100
        hw_steering = steering * 127 // 100
        self._send_packet(CMD_PERCENTAGE, hw_speed, hw_steering)

    def send_brake(self, front: int = 100, rear: int = 100):
        """
        CMD 0x03: 브레이크
        front / rear : 0~100 (%) → 0~127로 스케일
        """
        front = max(0, min(100, int(front)))
        rear  = max(0, min(100, int(rear)))
        self._send_packet(CMD_BRAKE, front * 127 // 100, rear * 127 // 100)

    def send_heartbeat(self):
        """CMD 0x00: 연결 확인 전송 (Heartbeat 스레드가 자동 처리)"""
        self._send_packet(CMD_HEARTBEAT, 0, 0)

    def estop(self):
        """CMD 0xFF: 비상 정지 — 즉시 모든 모터 정지"""
        self._send_packet(CMD_ESTOP, 0x00, 0x00)
        logger.warning("비상 정지 전송")

    # ------------------------------------------------------------------
    # 컨텍스트 매니저 지원
    # ------------------------------------------------------------------
    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *_):
        self.disconnect()

