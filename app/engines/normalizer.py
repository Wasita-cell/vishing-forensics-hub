import hashlib
import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from app.models.audio_meta import AudioMetadata

logger = logging.getLogger(__name__)


class AudioNormalizationError(Exception):
    """Custom exception สำหรับข้อผิดพลาดในขั้นตอน Normalization"""
    pass


class AudioNormalizer:
    def __init__(self, target_sample_rate: int = 16000, target_channels: int = 1):
        self.target_sample_rate = target_sample_rate
        self.target_channels = target_channels

    @staticmethod
    def calculate_file_hash(file_path: Path) -> str:
        """คำนวณ SHA-256 สำหรับใช้เป็น Forensic Integrity Hash"""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def probe_audio(self, input_path: Path) -> Dict[str, Any]:
        """ใช้ ffprobe ดึง Container และ Audio Stream metadata"""
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            str(input_path),
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return json.loads(result.stdout)
        except subprocess.CalledProcessError as e:
            logger.error("ffprobe failed on %s: %s", input_path, e.stderr)
            raise AudioNormalizationError(f"Failed to probe audio file: {e.stderr}") from e
        except json.JSONDecodeError as e:
            raise AudioNormalizationError("Corrupted ffprobe output") from e

    def normalize(self, input_path: Path, output_dir: Path) -> AudioMetadata:
        """
        แปลง Audio ให้อยู่ในมาตรฐาน 16kHz Mono PCM 16-bit
        ตัด Metadata เดิมออกทั้งหมดเพื่อความเป็นส่วนตัวและมาตรฐานการวิเคราะห์
        """
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")

        output_dir.mkdir(parents=True, exist_ok=True)
        raw_hash = self.calculate_file_hash(input_path)
        raw_probe = self.probe_audio(input_path)

        output_path = output_dir / f"{input_path.stem}_normalized.wav"

        # FFmpeg command: บังคับ sample rate, audio channel, PCM s16le, ตัด metadata ทิ้ง (-map_metadata -1)
        cmd = [
            "ffmpeg",
            "-y",
            "-i", str(input_path),
            "-map_metadata", "-1",
            "-vn",  # ไม่เอา Video stream เผื่อหลุดมาเป็น .mp4/.mkv
            "-ar", str(self.target_sample_rate),
            "-ac", str(self.target_channels),
            "-c:a", "pcm_s16le",
            str(output_path),
        ]

        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError as e:
            logger.error("ffmpeg conversion failed: %s", e.stderr)
            raise AudioNormalizationError(f"Normalization failed: {e.stderr}") from e

        # ดึงความยาวเสียงและ format ดั้งเดิม
        audio_stream = next(
            (s for s in raw_probe.get("streams", []) if s.get("codec_type") == "audio"),
            {},
        )
        duration_sec = float(raw_probe.get("format", {}).get("duration", 0.0))
        original_codec = audio_stream.get("codec_name", "unknown")
        original_sample_rate = int(audio_stream.get("sample_rate", 0))

        return AudioMetadata(
            original_file_name=input_path.name,
            original_sha256=raw_hash,
            normalized_file_path=output_path,
            duration_seconds=duration_sec,
            original_codec=original_codec,
            original_sample_rate=original_sample_rate,
            normalized_sample_rate=self.target_sample_rate,
            channels=self.target_channels,
        )