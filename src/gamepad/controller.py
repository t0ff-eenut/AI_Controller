# =============================================================================
# controller.py - 게임 컨트롤러 입력 처리 모듈 (8BitDo SN30 Pro / PS4 등)
# =============================================================================

import pygame
import logging
from config import (
    JOYSTICK_INDEX,
    AXIS_THROTTLE, AXIS_STEER,
    BTN_AUTONOMOUS, BTN_MANUAL, BTN_ESTOP,
    AXIS_DEADZONE,
)

logger = logging.getLogger(__name__)


class ControllerInput:
    """
    pygame 기반 게임 컨트롤러 래퍼.

    사용 예시:
        ctrl = ControllerInput()
        ctrl.start()
        state = ctrl.read()
        # state = {'throttle': 70, 'steering': -30, 'btn_auto': False, ...}
        ctrl.stop()
    """

    def __init__(self):
        self._joystick: pygame.joystick.Joystick | None = None

    # ------------------------------------------------------------------
    # 초기화 / 종료
    # ------------------------------------------------------------------
    def start(self) -> bool:
        pygame.init()
        pygame.joystick.init()

        count = pygame.joystick.get_count()
        if count == 0:
            logger.error("연결된 컨트롤러 없음")
            return False

        self._joystick = pygame.joystick.Joystick(JOYSTICK_INDEX)
        self._joystick.init()
        logger.info(f"컨트롤러 연결: {self._joystick.get_name()}")
        return True

    def stop(self):
        pygame.joystick.quit()
        pygame.quit()
        logger.info("컨트롤러 해제")

    # ------------------------------------------------------------------
    # 입력 읽기
    # ------------------------------------------------------------------
    # ------------------------------------------------------------------
    # 더미 입력 (컨트롤러 미연결 시)
    # ------------------------------------------------------------------
    _DUMMY_STATE: dict = {
        'throttle': 0, 'steering': 0,
        'btn_auto': False, 'btn_manual': False, 'btn_estop': False,
    }

    def read(self) -> dict:
        """
        현재 컨트롤러 상태를 반환.
        컨트롤러 미연결 시 모든 값이 0/False인 더미 상태를 반환.

        반환값:
            {
                'throttle'  : int,   # -100 ~ 100
                'steering'  : int,   # -100 ~ 100
                'btn_auto'  : bool,  # 자율주행 모드 전환 버튼
                'btn_manual': bool,  # 수동 모드 전환 버튼
                'btn_estop' : bool,  # 비상 정지 버튼
            }
        """
        if self._joystick is None:
            return dict(self._DUMMY_STATE)

        pygame.event.pump()

        throttle = self._apply_deadzone(
            self._joystick.get_axis(AXIS_THROTTLE)
        ) * -100   # 스틱 위 = 양수 스로틀

        steering = self._apply_deadzone(
            self._joystick.get_axis(AXIS_STEER)
        ) * 100

        return {
            'throttle'  : int(throttle),
            'steering'  : int(steering),
            'btn_auto'  : bool(self._joystick.get_button(BTN_AUTONOMOUS)),
            'btn_manual': bool(self._joystick.get_button(BTN_MANUAL)),
            'btn_estop' : bool(self._joystick.get_button(BTN_ESTOP)),
        }

    # ------------------------------------------------------------------
    # 내부 유틸
    # ------------------------------------------------------------------
    @staticmethod
    def _apply_deadzone(value: float) -> float:
        if abs(value) < AXIS_DEADZONE:
            return 0.0
        return value

    # ------------------------------------------------------------------
    # 컨텍스트 매니저 지원
    # ------------------------------------------------------------------
    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *_):
        self.stop()
