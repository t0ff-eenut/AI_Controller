# =============================================================================
# autonomous.py - 자율주행 로직 모듈
# =============================================================================

import time
import logging
from config import (
    SPEED_NORMAL, SPEED_SLOW,
    STEER_MAX,
    OBSTACLE_DIST_MM,
    PID_KP, PID_KI, PID_KD,
)

logger = logging.getLogger(__name__)


class PIDController:
    """단순 PID 제어기 (조향에 사용)"""

    def __init__(self, kp: float, ki: float, kd: float):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self._prev_error = 0.0
        self._integral   = 0.0
        self._prev_time  = time.time()

    def compute(self, error: float) -> float:
        now = time.time()
        dt  = now - self._prev_time
        if dt <= 0:
            dt = 1e-6

        self._integral   += error * dt
        derivative        = (error - self._prev_error) / dt
        output            = (self.kp * error
                             + self.ki * self._integral
                             + self.kd * derivative)

        self._prev_error  = error
        self._prev_time   = now
        return output

    def reset(self):
        self._prev_error = 0.0
        self._integral   = 0.0
        self._prev_time  = time.time()


class AutonomousDriving:
    """
    자율주행 로직 클래스.
    DepthCamera의 결과를 받아 BCUComm으로 제어 명령을 전송.

    사용 예시:
        auto = AutonomousDriving(bcu, camera)
        cmd = auto.step()
        # cmd = {'speed': 40, 'steering': 0, 'estop': False}
    """

    def __init__(self, bcu, camera):
        self._bcu    = bcu
        self._camera = camera
        self._steer_pid = PIDController(PID_KP, PID_KI, PID_KD)

    def reset(self):
        self._steer_pid.reset()

    # ------------------------------------------------------------------
    # 메인 스텝 (매 루프마다 호출)
    # ------------------------------------------------------------------
    def step(self) -> dict:
        """
        한 프레임 처리 후 제어 명령을 BCU에 전송하고 결과를 반환.

        반환값:
            {
                'speed'    : int,   # 전송한 속도 (%)
                'steering' : int,   # 전송한 조향 (%)
                'estop'    : bool,  # 비상 정지 여부
            }
        """
        obstacle = self._camera.detect_obstacle()

        if obstacle['detected']:
            # --- 장애물 감지: 비상 정지 ---
            self._bcu.estop()
            self.reset()
            logger.warning(f"장애물 감지 @ {obstacle['distance']}mm → 비상 정지")
            return {'speed': 0, 'steering': 0, 'estop': True}

        # --- 정상 주행 ---
        speed    = self._decide_speed(obstacle['distance'])
        steering = self._decide_steering()

        self._bcu.send_control(speed, steering)
        return {'speed': speed, 'steering': steering, 'estop': False}

    # ------------------------------------------------------------------
    # 속도 결정
    # ------------------------------------------------------------------
    def _decide_speed(self, distance_mm: int) -> int:
        """
        장애물 거리에 따라 속도를 결정.
        TODO: 곡률 기반 코너 감속 로직 추가
        """
        threshold_slow = OBSTACLE_DIST_MM * 2   # 감지 거리의 2배 이내 = 감속

        if 0 < distance_mm < threshold_slow:
            return SPEED_SLOW
        return SPEED_NORMAL

    # ------------------------------------------------------------------
    # 조향 결정
    # ------------------------------------------------------------------
    def _decide_steering(self) -> int:
        """
        TODO: 뎁스맵 또는 차선 인식 결과를 이용한 PID 조향 계산.
        현재는 직진 유지 (error = 0).
        """
        # 차선 중심 오차 계산 (추후 구현)
        lane_error = self._compute_lane_error()
        raw = self._steer_pid.compute(lane_error)
        return int(max(-STEER_MAX, min(STEER_MAX, raw)))

    def _compute_lane_error(self) -> float:
        """
        TODO: 컬러 카메라 프레임에서 차선 중심 오차를 계산.
        반환값: 음수 = 좌편향, 양수 = 우편향
        """
        return 0.0
