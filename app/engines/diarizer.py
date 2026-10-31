import logging
from pathlib import Path
from typing import List

import numpy as np
import soundfile as sf
from scipy.signal import welch

logger = logging.getLogger(__name__)


class LightweightDiarizer:
    """
    จัดกลุ่มผู้พูด 2 ฝั่ง (2-Speaker Clustering) โดยวิเคราะห์คุณลักษณะเสียง:
    1. Spectral Centroid (ตำแหน่งศูนย์กลางความถี่เสียงสะท้อน Pitch/Timbre)
    2. RMS Energy (ระดับความดังเฉลี่ย)
    3. Zero-Crossing Rate (ความคมชัดของเสียงพูด)
    """

    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate

    def _extract_segment_features(self, audio_data: np.ndarray, sr: int) -> np.ndarray:
        if len(audio_data) < 256:
            return np.array([0.0, 0.0, 0.0])

        # 1. RMS Energy
        rms = np.sqrt(np.mean(audio_data**2))

        # 2. Zero Crossing Rate
        zcr = np.mean(np.abs(np.diff(np.signbit(audio_data))))

        # 3. Spectral Centroid (Approximation via Welch PSD)
        freqs, psd = welch(audio_data, fs=sr, nperseg=min(len(audio_data), 512))
        total_p = np.sum(psd)
        centroid = np.sum(freqs * psd) / total_p if total_p > 0 else 0.0

        return np.array([rms * 100.0, zcr * 100.0, centroid / 1000.0])

    def diarize_segments(self, audio_path: Path, segments: list) -> list:
        if not segments:
            return segments

        data, sr = sf.read(str(audio_path), dtype="float32")
        if data.ndim > 1:
            data = data.mean(axis=1)

        features = []
        valid_indices = []

        for idx, seg in enumerate(segments):
            start_idx = int(seg.start * sr)
            end_idx = int(seg.end * sr)
            segment_audio = data[start_idx:end_idx]

            feat = self._extract_segment_features(segment_audio, sr)
            features.append(feat)
            valid_indices.append(idx)

        feat_matrix = np.array(features)

        # ทำ 2-Means Clustering พื้นฐาน
        # กำหนด centroid เริ่มต้นจากจุดที่มี Spectral Centroid ต่ำสุดและสูงสุด
        if len(feat_matrix) >= 2:
            sort_idx = np.argsort(feat_matrix[:, 2])
            c1 = feat_matrix[sort_idx[0]]
            c2 = feat_matrix[sort_idx[-1]]

            labels = []
            for _ in range(5):  # 5 iterations
                dist1 = np.linalg.norm(feat_matrix - c1, axis=1)
                dist2 = np.linalg.norm(feat_matrix - c2, axis=1)
                labels = np.where(dist1 <= dist2, 0, 1)

                group0 = feat_matrix[labels == 0]
                group1 = feat_matrix[labels == 1]
                if len(group0) > 0:
                    c1 = group0.mean(axis=0)
                if len(group1) > 0:
                    c2 = group1.mean(axis=0)

            for i, seg in enumerate(segments):
                seg.speaker = f"SPEAKER_{labels[i]:02d}"
        else:
            for seg in segments:
                seg.speaker = "SPEAKER_00"

        return segments