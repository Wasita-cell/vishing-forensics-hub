import logging
from pathlib import Path
from typing import List, Tuple

import numpy as np
import soundfile as sf
from scipy.signal import welch

logger = logging.getLogger(__name__)


class AcousticForensicsAnalyzer:
    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate

    def analyze(self, audio_path: Path) -> dict:
        """
        วิเคราะห์ Power Spectral Density (PSD) เพื่อตรวจจับ:
        1. การตัดย่านความถี่ตามมาตรฐานเครือข่ายโทรศัพท์ (PSTN / HD Voice)
        2. พลังงานในย่านความถี่สูงผิดปกติ (>7.5 kHz) ที่บ่งชี้ไฟล์สังเคราะห์จาก TTS/Studio
        """
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        # โหลดไฟล์เสียง
        audio_data, sr = sf.read(str(audio_path), dtype="float32")
        if audio_data.ndim > 1:
            audio_data = audio_data.mean(axis=1)

        # คำนวณ Power Spectral Density (Welch's method)
        freqs, psd = welch(audio_data, fs=sr, nperseg=1024)

        total_power = np.sum(psd)
        if total_power == 0:
            total_power = 1e-10

        # วัดพลังงานย่านความถี่สูง (> 7000 Hz)
        high_freq_indices = np.where(freqs >= 7000)[0]
        high_freq_power = np.sum(psd[high_freq_indices])
        hf_ratio = high_freq_power / total_power

        # หา Cutoff Frequency โดยประมาณ (จุดที่พลังงานสะสมแตะ 95%)
        cum_power = np.cumsum(psd) / total_power
        cutoff_idx = np.where(cum_power >= 0.95)[0]
        cutoff_freq = freqs[cutoff_idx[0]] if len(cutoff_idx) > 0 else freqs[-1]

        # ประเมิน Artifacts
        flags: List[str] = []
        synthetic_score = 0

        # ถ้าเป็นสายโทรศัพท์ทั่วไป Bandwidth มักจะไม่เกิน 7.5 kHz
        is_telephony = cutoff_freq <= 7500

        if not is_telephony and hf_ratio > 0.05:
            flags.append("UNNATURAL_HIGH_BANDWIDTH: พบย่านความถี่สูงผิดวิสัยสายโทรศัพท์ (คล้ายสัญญาณจากระบบสังเคราะห์เสียง)")
            synthetic_score += 40

        if hf_ratio > 0.15:
            flags.append("STUDIO_QUALITY_AUDIO: เสียงมีมิติความถี่กว้างแบบ Audio Studio หรือ Direct TTS generation")
            synthetic_score += 30

        return {
            "is_telephony_bandwidth": is_telephony,
            "cutoff_frequency_hz": round(float(cutoff_freq), 2),
            "high_frequency_energy_ratio": round(float(hf_ratio), 4),
            "synthetic_suspicion_score": min(synthetic_score, 100),
            "acoustic_flags": flags,
        }