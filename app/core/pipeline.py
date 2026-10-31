import os
import subprocess
import tempfile
import uuid
import logging
from pathlib import Path
from typing import Callable, Optional

from app.engines.transcriber import AudioTranscriber
from app.engines.threat_analyzer import NZVishingThreatAnalyzer
from app.engines.acoustic_forensics import AcousticForensicsAnalyzer
from app.engines.diarizer import LightweightDiarizer
from app.models.report import VishingIncidentReport, AcousticForensicsReport

logger = logging.getLogger(__name__)


class VishingForensicsPipeline:
    def __init__(
        self,
        model_size: str = "base",
        device: str = "cpu",
        compute_type: str = "int8"
    ):
        logger.info("Initializing Vishing Forensics Dual-Track Engines...")
        self.transcriber = AudioTranscriber(
            model_size=model_size,
            device=device,
            compute_type=compute_type
        )
        self.threat_analyzer = NZVishingThreatAnalyzer()
        self.acoustic_analyzer = AcousticForensicsAnalyzer()
        self.diarizer = LightweightDiarizer()

    def _convert_to_wav(self, input_path: Path) -> Path:
        wav_tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        wav_path = Path(wav_tmp.name)
        wav_tmp.close()

        cmd = [
            "afconvert",
            "-f", "WAVE",
            "-d", "LEI16@16000",
            "-c", "1",
            str(input_path),
            str(wav_path)
        ]
        
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode != 0:
            if wav_path.exists():
                os.remove(wav_path)
            raise RuntimeError(f"Audio conversion failed: {result.stderr.decode('utf-8')}")

        return wav_path

    def _attribute_speakers(self, transcription, threat_report):
        """วิเคราะห์จับคู่ Threat Hits ลงใน Segment และหาว่า Speaker ใดเป็น Scammer"""
        speaker_threat_scores = {}

        # 1. เช็กแต่ละ Segment เทียบกับ Threat Patterns ที่พบ
        for seg in transcription.segments:
            seg_text_lower = seg.text.lower()
            speaker_id = seg.speaker or "SPEAKER_00"
            if speaker_id not in speaker_threat_scores:
                speaker_threat_scores[speaker_id] = 0

            for hit in threat_report.hits:
                if hit.matched_text.lower() in seg_text_lower:
                    seg.matched_threats.append(f"{hit.category}: {hit.matched_text}")
                    speaker_threat_scores[speaker_id] += hit.weight

        # 2. ระบุตัว Scammer จากคะแนน Threat Weight สะสม
        scammer_id = None
        if speaker_threat_scores:
            max_speaker = max(speaker_threat_scores, key=speaker_threat_scores.get)
            if speaker_threat_scores[max_speaker] > 0:
                scammer_id = max_speaker

        transcription.scammer_speaker_id = scammer_id

        # 3. กำหนด Label บทบาทให้ทุก Segment
        for seg in transcription.segments:
            if scammer_id and seg.speaker == scammer_id:
                seg.speaker_role = "SCAMMER"
            elif scammer_id:
                seg.speaker_role = "VICTIM"
            else:
                seg.speaker_role = "UNKNOWN"

    def run(
        self,
        audio_path: Path,
        language: Optional[str] = "en",
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> VishingIncidentReport:
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        converted_path = None
        if audio_path.suffix.lower() != ".wav":
            if progress_callback:
                progress_callback(0.02, "Converting audio to normalized 16kHz WAV format...")
            target_path = self._convert_to_wav(audio_path)
            converted_path = target_path
        else:
            target_path = audio_path

        try:
            # Track A: Signal & Spectral Forensics
            if progress_callback:
                progress_callback(0.08, "Analyzing acoustic spectrum and telephony bandwidth...")
            acoustic_raw = self.acoustic_analyzer.analyze(target_path)
            acoustic_report = AcousticForensicsReport(**acoustic_raw)

            # Track B: Speech-to-Text with Real-time Progress
            if progress_callback:
                progress_callback(0.12, "Starting Faster-Whisper Speech Recognition...")

            def whisper_progress(ratio: float, msg: str):
                scaled_ratio = 0.12 + (ratio * 0.65)
                if progress_callback:
                    progress_callback(scaled_ratio, msg)

            transcription = self.transcriber.transcribe(
                target_path,
                language=language,
                progress_callback=whisper_progress
            )

            # Track C: Speaker Diarization
            if progress_callback:
                progress_callback(0.80, "Clustering speakers (Caller vs Receiver)...")
            transcription.segments = self.diarizer.diarize_segments(
                target_path,
                transcription.segments
            )

            # Stage 3: Threat Analysis & Auto-Attribution
            if progress_callback:
                progress_callback(0.90, "Evaluating NZ threat vectors and social engineering patterns...")
            threat_report = self.threat_analyzer.analyze(transcription.full_text)

            if progress_callback:
                progress_callback(0.95, "Running Speaker Attribution and Role Assignment...")
            self._attribute_speakers(transcription, threat_report)

            # Stage 4: Correlation & Final Scoring
            combined_score = int(
                (0.60 * threat_report.threat_score) + 
                (0.40 * acoustic_report.synthetic_suspicion_score)
            )
            combined_score = min(combined_score, 100)

            incident_id = f"VISH-{uuid.uuid4().hex[:8].upper()}"
            is_malicious = (
                threat_report.risk_level in ["HIGH", "CRITICAL"] 
                or combined_score >= 60 
                or acoustic_report.synthetic_suspicion_score >= 70
            )

            verdict = (
                f"SUSPICIOUS / VISHING DETECTED (Combined Risk: {combined_score}/100)"
                if is_malicious
                else f"BENIGN INTERACTION (Combined Risk: {combined_score}/100)"
            )

            if progress_callback:
                progress_callback(1.0, "Incident triage report generated successfully!")

            return VishingIncidentReport(
                incident_id=incident_id,
                audio_file_name=audio_path.name,
                duration_seconds=transcription.duration,
                transcription=transcription,
                threat_analysis=threat_report,
                acoustic_analysis=acoustic_report,
                combined_risk_score=combined_score,
                is_malicious=is_malicious,
                summary_verdict=verdict,
            )
        finally:
            if converted_path and converted_path.exists():
                os.remove(converted_path)