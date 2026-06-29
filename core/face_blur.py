from __future__ import annotations

import logging
from typing import Callable

import cv2
import mediapipe as mp
import numpy as np

log = logging.getLogger(__name__)

_mp_face = mp.solutions.face_detection


def build_face_blur_filter(
    blur_ksize: int = 61,
    expand: float = 0.35,
    min_confidence: float = 0.5,
) -> Callable[[np.ndarray], np.ndarray]:
    """
    Return a frame-level processor that blurs detected faces.

    The returned callable accepts and returns RGB uint8 numpy arrays
    (MoviePy's native format).
    """
    face_det = _mp_face.FaceDetection(
        model_selection=1, min_detection_confidence=min_confidence
    )
    # blur_ksize must be odd
    ksize = blur_ksize if blur_ksize % 2 == 1 else blur_ksize + 1

    def process_frame(frame: np.ndarray) -> np.ndarray:
        h, w, _ = frame.shape
        results = face_det.process(frame)  # expects RGB
        if not results.detections:
            return frame

        img_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        for det in results.detections:
            bb = det.location_data.relative_bounding_box
            x = max(0, int(bb.xmin * w))
            y = max(0, int(bb.ymin * h))
            bw = int(bb.width * w)
            bh = int(bb.height * h)
            x_e = max(0, int(x - expand * bw))
            y_e = max(0, int(y - expand * bh))
            bw_e = min(w - x_e, int(bw * (1 + 2 * expand)))
            bh_e = min(h - y_e, int(bh * (1 + 2 * expand)))
            roi = img_bgr[y_e : y_e + bh_e, x_e : x_e + bw_e]
            if roi.size > 0:
                img_bgr[y_e : y_e + bh_e, x_e : x_e + bw_e] = cv2.GaussianBlur(
                    roi, (ksize, ksize), 0
                )
        return cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)

    return process_frame
