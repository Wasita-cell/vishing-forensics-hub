import logging
from pathlib import Path
from typing import Callable, Optional

import soundfile as sf
from faster_whisper import WhisperModel

from app.models.transcript import TranscriptionResult, TranscriptSegment

logger = logging.getLogger(__name__)


class AudioTranscriber:
    def __init__(
        self,
        model_size: str = "base",
        device: str = "cpu",
        compute_type: str = "int8",
        download_root: Optional[Path] = None,
    ):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.download_root = str(download_root) if download_root else None

        logger.info(
            "Loading Faster-Whisper model [%s] on %s with %s quantization...",
            self.model_size,
            self.device,
            self.compute_type,
        )
        self.model = WhisperModel(
            self.model_size,
            device=self.device,
            compute_type=self.compute_type,
            download_root=self.download_root,
        )

    def transcribe(
        self,
        audio_path: Path,
        language: Optional[str] = None,  # เปลี่ยนเป็น None เพื่อให้ auto-detect ภาษาได้
        beam_size: int = 5,
        vad_filter: bool = False,       # ปิด VAD ชั่วคราวเพื่อป้องกันไม่ให้เสียงถูกตัดทิ้ง
        progress_callback: Optional[Callable[[float, str], None]] = None,
    ) -> TranscriptionResult:
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found at: {audio_path}")

        # โหลด raw audio data
        audio_data, sample_rate = sf.read(str(audio_path), dtype="float32")
        if audio_data.ndim > 1:
            audio_data = audio_data.mean(axis=1)

        total_duration = len(audio_data) / sample_rate

        segments_raw, info = self.model.transcribe(
            audio_data,
            language=language,
            beam_size=beam_size,
            vad_filter=vad_filter,
            condition_on_previous_text=False,  # ป้องกันข้อความติดลูปซ้ำ
        )

        segments: list[TranscriptSegment] = []
        full_text_list: list[str] = []

        # วนลูปอ่าน Generator ทีละ Segment พร้อมอัปเดต Progress
        for seg in segments_raw:
            cleaned_text = seg.text.strip()
            if cleaned_text:
                full_text_list.append(cleaned_text)
                segments.append(
                    TranscriptSegment(
                        id=seg.id,
                        start=round(seg.start, 2),
                        end=round(seg.end, 2),
                        text=cleaned_text,
                        avg_logprob=round(seg.avg_logprob, 4),
                        no_speech_prob=round(seg.no_speech_prob, 4),
                    )
                )

            if progress_callback and total_duration > 0:
                current_progress = min(seg.end / total_duration, 1.0)
                status_msg = f"Transcribing: {seg.end/60:.1f} / {total_duration/60:.1f} mins ({int(current_progress * 100)}%)"
                progress_callback(current_progress, status_msg)

        full_text = " ".join(full_text_list)

        # กรณีไม่มีเสียงพูดตรวจพบเลย ให้ใส่ข้อความแจ้งเตือนแทนกล่องว่าง
        if not full_text:
            full_text = "[No speech detected in this audio file]"

        return TranscriptionResult(
            full_text=full_text,
            detected_language=info.language or "unknown",
            language_probability=round(info.language_probability, 4) if info.language_probability else 0.0,
            duration=round(total_duration, 2),
            segments=segments,
        )