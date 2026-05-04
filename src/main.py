# =============================================================================
# main.py - 메인 진입점 / 모드 전환 관리
# =============================================================================
#
# 실행:  python main.py
#        python main.py --dry-run     # 하드웨어 없이 로그만 출력
#
# 모드:
#   MANUAL     - 컨트롤러 입력으로 수동 조종
#   AUTONOMOUS - 뎁스 카메라 기반 자율주행
#
# 버튼 매핑 (8BitDo SN30 Pro 기준):
#   START   → 자율주행 모드 전환
#   SELECT  → 수동 모드 전환
#   L2      → 비상 정지
# =============================================================================

import argparse
import time
import signal
import logging
import sys
from enum import Enum, auto

from bcu.bcu_comm      import BCUComm
from camera.depth_camera import DepthCamera
from gamepad.controller  import ControllerInput
from ai.autonomous       import AutonomousDriving

# --- 로깅 설정 ---
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s %(name)s: %(message)s',
    datefmt='%H:%M:%S',
)
logger = logging.getLogger('main')

LOOP_HZ = 30   # 제어 루프 주파수 (Hz)


class Mode(Enum):
    MANUAL     = auto()
    AUTONOMOUS = auto()


class RCCarApp:
    def __init__(self, dry_run: bool = False):
        self._dry_run      = dry_run
        self._bcu          = BCUComm(dry_run=dry_run)
        self._camera       = DepthCamera()
        self._controller   = ControllerInput()
        self._auto         = None
        self._camera_ready = False
        self._mode         = Mode.MANUAL
        self._running      = False

    # ------------------------------------------------------------------
    # 시작 / 종료
    # ------------------------------------------------------------------
    def start(self):
        if self._dry_run:
            logger.info("===== DRY-RUN 모드: 하드웨어 명령은 로그로만 출력됩니다 =====")

        if not self._bcu.connect():
            logger.error("BCU 연결 실패. 종료합니다.")
            sys.exit(1)

        self._camera_ready = self._dry_run or self._camera.start()
        if not self._camera_ready:
            logger.warning("카메라 없음 — 자율주행 모드 사용 불가. 수동 모드로 시작합니다.")

        if not self._controller.start():
            if not self._camera_ready and not self._dry_run:
                logger.error("카메라와 컨트롤러 모두 없음. 종료합니다.")
                sys.exit(1)
            logger.warning("컨트롤러 없음 — 자율주행 모드로 시작합니다.")
            self._mode = Mode.AUTONOMOUS

        self._auto = AutonomousDriving(self._bcu, self._camera)
        self._running = True
        logger.info(f"시작 — 모드: {self._mode.name}")

    def stop(self):
        self._running = False
        self._bcu.estop()
        self._camera.stop()
        self._controller.stop()
        self._bcu.disconnect()
        logger.info("종료 완료")

    # ------------------------------------------------------------------
    # 메인 루프
    # ------------------------------------------------------------------
    def run(self):
        interval = 1.0 / LOOP_HZ

        while self._running:
            t_start = time.time()

            ctrl = self._controller.read()

            # --- 비상 정지 ---
            if ctrl['btn_estop']:
                self._bcu.estop()
                logger.warning("수동 비상 정지")

            # --- BCU 연결 끊김 감지 ---
            elif not self._bcu.is_alive:
                logger.error("BCU 연결 끊김 — 비상 정지")
                self._bcu.estop()

            # --- 모드 전환 ---
            elif ctrl['btn_auto'] and self._mode != Mode.AUTONOMOUS:
                if not self._camera_ready:
                    logger.warning("카메라 미연결 — 자율주행 모드 전환 불가")
                else:
                    self._mode = Mode.AUTONOMOUS
                    self._auto.reset()
                    logger.info("→ 자율주행 모드")

            elif ctrl['btn_manual'] and self._mode != Mode.MANUAL:
                self._mode = Mode.MANUAL
                logger.info("→ 수동 모드")

            # --- 제어 ---
            elif self._mode == Mode.MANUAL:
                self._bcu.send_control(ctrl['throttle'], ctrl['steering'])

            elif self._mode == Mode.AUTONOMOUS:
                self._auto.step()

            # 루프 주파수 유지
            elapsed = time.time() - t_start
            sleep_t = interval - elapsed
            if sleep_t > 0:
                time.sleep(sleep_t)


# ------------------------------------------------------------------
# 진입점
# ------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description='Pseudo F1 RC Car AI Controller')
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='하드웨어 없이 실행 (BCU/카메라 연결 생략, 명령을 로그로 출력)',
    )
    args = parser.parse_args()

    app = RCCarApp(dry_run=args.dry_run)

    # Ctrl+C / SIGTERM 처리
    def _shutdown(sig, frame):
        logger.info("종료 신호 수신")
        app.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT,  _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    app.start()
    app.run()


if __name__ == '__main__':
    main()
