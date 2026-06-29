from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass
class FrameVector:
    source_index: int
    timestamp: float
    brightness: float
    contrast: float
    sharpness: float
    distance_from_previous: float | None
    feature: np.ndarray
    frame_bgr: np.ndarray

    def to_public_dict(self) -> dict:
        return {
            "source_index": self.source_index,
            "timestamp": round(self.timestamp, 3),
            "brightness": round(self.brightness, 3),
            "contrast": round(self.contrast, 3),
            "sharpness": round(self.sharpness, 3),
            "distance_from_previous": (
                None if self.distance_from_previous is None else round(self.distance_from_previous, 6)
            ),
        }


def perceptual_hash_bits(gray: np.ndarray) -> np.ndarray:
    resized = cv2.resize(gray, (64, 64), interpolation=cv2.INTER_AREA)
    dct = cv2.dct(np.float32(resized) / 255.0)
    low_freq = dct[:8, :8].copy()
    values = low_freq.flatten()
    median = np.median(values[1:])
    return (values > median).astype(np.float32)


def build_feature(frame_bgr: np.ndarray) -> tuple[np.ndarray, float, float, float]:
    small = cv2.resize(frame_bgr, (160, 90), interpolation=cv2.INTER_AREA)
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)

    brightness = float(np.mean(gray))
    contrast = float(np.std(gray))
    sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())

    thumbnail = cv2.resize(gray, (32, 18), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0
    thumbnail = thumbnail.flatten()
    thumbnail = (thumbnail - np.mean(thumbnail)) / (np.std(thumbnail) + 1e-6)

    hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
    histogram = cv2.calcHist([hsv], [0, 1, 2], None, [12, 4, 4], [0, 180, 0, 256, 0, 256])
    histogram = cv2.normalize(histogram, histogram).flatten().astype(np.float32)

    phash = perceptual_hash_bits(gray)

    feature = np.concatenate(
        [
            thumbnail * 0.85,
            histogram * 0.75,
            phash * 0.35,
            np.array([brightness / 255.0, contrast / 128.0], dtype=np.float32) * 0.25,
        ]
    ).astype(np.float32)
    norm = np.linalg.norm(feature)
    if norm > 0:
        feature /= norm
    return feature, brightness, contrast, sharpness


def frame_to_vector(source_index: int, timestamp: float, frame_bgr: np.ndarray, previous: FrameVector | None) -> FrameVector:
    feature, brightness, contrast, sharpness = build_feature(frame_bgr)
    distance = None
    if previous is not None:
        distance = float(np.linalg.norm(feature - previous.feature))
    return FrameVector(
        source_index=source_index,
        timestamp=timestamp,
        brightness=brightness,
        contrast=contrast,
        sharpness=sharpness,
        distance_from_previous=distance,
        feature=feature,
        frame_bgr=frame_bgr,
    )


def is_useful_frame(vector: FrameVector) -> bool:
    if (vector.brightness < 2.0 or vector.brightness > 253.0) and vector.contrast < 1.0:
        return False
    return True
