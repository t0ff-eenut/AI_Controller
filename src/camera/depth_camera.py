# =============================================================================
# depth_camera.py - Luxonis OAK-D Lite DepthAI 연동 모듈
# =============================================================================

import numpy as np
import depthai as dai
import logging
from config import (
    DEPTH_FPS, DEPTH_RESOLUTION,
    OBSTACLE_DIST_MM, DEPTH_ROI_TOP, DEPTH_ROI_BOTTOM,
)

logger = logging.getLogger(__name__)


class DepthCamera:
    """
    OAK-D Lite 스테레오 뎁스 카메라 래퍼.

    사용 예시:
        cam = DepthCamera()
        cam.start()
        frame = cam.get_depth_frame()   # numpy uint16 배열 (mm 단위)
        result = cam.detect_obstacle()  # ObstacleResult
        cam.stop()
    """

    def __init__(self):
        self._device: dai.Device | None = None
        self._depth_queue = None
        self._pipeline: dai.Pipeline | None = None  # start() 시점에 빌드

    # ------------------------------------------------------------------
    # DepthAI 파이프라인 구성
    # ------------------------------------------------------------------
    def _build_pipeline(self) -> dai.Pipeline:
        pipeline = dai.Pipeline()

        # 좌/우 흑백 카메라 (스테레오용)
        cam_left  = pipeline.create(dai.node.MonoCamera)
        cam_right = pipeline.create(dai.node.MonoCamera)
        cam_left.setResolution(dai.MonoCameraProperties.SensorResolution.THE_400_P)
        cam_right.setResolution(dai.MonoCameraProperties.SensorResolution.THE_400_P)
        cam_left.setBoardSocket(dai.CameraBoardSocket.CAM_B)
        cam_right.setBoardSocket(dai.CameraBoardSocket.CAM_C)
        cam_left.setFps(DEPTH_FPS)
        cam_right.setFps(DEPTH_FPS)

        # 스테레오 뎁스 노드
        stereo = pipeline.create(dai.node.StereoDepth)
        stereo.setDefaultProfilePreset(dai.node.StereoDepth.PresetMode.HIGH_DENSITY)
        stereo.setLeftRightCheck(True)     # 좌우 일관성 검사 (노이즈 감소)
        stereo.setExtendedDisparity(False)
        stereo.setSubpixel(False)
        stereo.setDepthAlign(dai.CameraBoardSocket.CAM_A)  # RGB 정렬

        # 좌/우 → 스테레오 연결
        cam_left.out.link(stereo.left)
        cam_right.out.link(stereo.right)

        # 뎁스 출력 → 호스트
        xout_depth = pipeline.create(dai.node.XLinkOut)
        xout_depth.setStreamName('depth')
        stereo.depth.link(xout_depth.input)

        # TODO: 컬러 카메라 + 차선 인식 노드 추가
        # TODO: NeuralNetwork 노드 (YOLO 장애물 감지)

        return pipeline

    # ------------------------------------------------------------------
    # 장치 시작 / 정지
    # ------------------------------------------------------------------
    def start(self) -> bool:
        """
        카메라를 초기화하고 파이프라인을 시작합니다.
        카메라 미연결 시 False를 반환합니다.
        """
        try:
            self._pipeline = self._build_pipeline()
            self._device = dai.Device(self._pipeline)
            self._depth_queue = self._device.getOutputQueue(
                name='depth', maxSize=4, blocking=False
            )
            logger.info("OAK-D Lite 시작")
            return True
        except RuntimeError as e:
            logger.warning(f"OAK-D Lite 초기화 실패 (카메라 미연결?): {e}")
            self._pipeline = None
            return False

    def stop(self):
        if self._device:
            self._device.close()
            self._device = None
        logger.info("OAK-D Lite 정지")

    # ------------------------------------------------------------------
    # 뎁스 프레임 획득
    # ------------------------------------------------------------------
    def get_depth_frame(self) -> np.ndarray | None:
        """
        최신 뎁스 프레임을 numpy 배열로 반환.
        반환값: uint16 배열, 단위 mm. 카메라 미연결 시 None.
        """
        if not self._depth_queue:
            return None
        msg = self._depth_queue.tryGet()
        if msg is None:
            return None
        return msg.getFrame()

    # ------------------------------------------------------------------
    # 장애물 감지
    # ------------------------------------------------------------------
    def detect_obstacle(self) -> dict:
        """
        전방 ROI 영역의 중앙 뎁스값으로 장애물 유무를 판단.

        반환값:
            {
                'detected' : bool,    # 장애물 감지 여부
                'distance' : int,     # 최근접 거리 (mm), 0 이면 데이터 없음
            }
        """
        frame = self.get_depth_frame()
        if frame is None:
            return {'detected': False, 'distance': 0}

        h, w = frame.shape
        # 관심 영역 (전방 중앙 ROI)
        roi = frame[
            int(h * DEPTH_ROI_TOP)  : int(h * DEPTH_ROI_BOTTOM),
            int(w * 0.25)           : int(w * 0.75),
        ]

        # 유효 픽셀(0보다 큰 값)의 최솟값을 최근접 거리로 사용
        valid = roi[roi > 0]
        if valid.size == 0:
            return {'detected': False, 'distance': 0}

        min_dist = int(np.percentile(valid, 5))  # 하위 5% → 노이즈 제거
        detected = min_dist < OBSTACLE_DIST_MM

        return {'detected': detected, 'distance': min_dist}

    # ------------------------------------------------------------------
    # 컨텍스트 매니저 지원
    # ------------------------------------------------------------------
    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *_):
        self.stop()
