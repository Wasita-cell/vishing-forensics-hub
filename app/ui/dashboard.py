import os
import subprocess
import tempfile
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import soundfile as sf
import streamlit as st

from app.core.pipeline import VishingForensicsPipeline

st.set_page_config(
    page_title="Audio & Vishing Forensics Hub",
    page_icon="🛡️",
    layout="wide"
)

st.title("🛡️ Audio & Vishing Forensics Hub (NZ Context)")
st.caption("Dual-Track Acoustic & Social Engineering Triage Platform")

@st.cache_resource
def load_pipeline():
    return VishingForensicsPipeline(model_size="base", device="cpu", compute_type="int8")

pipeline = load_pipeline()

def generate_markdown_report(report) -> str:
    """แปลงข้อมูล Forensic Report ให้อยู่ในฟอร์แมต Markdown Ticket สำหรับ SecOps"""
    hits_md = ""
    if report.threat_analysis.hits:
        for hit in report.threat_analysis.hits:
            hits_md += f"- **[{hit.category}]** Matched: `{hit.matched_text}` (Weight: {hit.weight})\n"
    else:
        hits_md = "- No suspicious intent patterns detected.\n"

    actions_md = ""
    if report.threat_analysis.containment_recommendations:
        for rec in report.threat_analysis.containment_recommendations:
            actions_md += f"- [ ] {rec}\n"
    else:
        actions_md = "- No immediate containment required.\n"

    acoustic_flags_md = ""
    if report.acoustic_analysis.acoustic_flags:
        for flag in report.acoustic_analysis.acoustic_flags:
            acoustic_flags_md += f"- 🚩 `{flag}`\n"
    else:
        acoustic_flags_md = "- None (Standard telephony acoustic profile)\n"

    segments_md = ""
    for seg in report.transcription.segments:
        role_label = f"[{seg.speaker_role}] {seg.speaker}"
        threat_tag = f" (Triggers: {', '.join(seg.matched_threats)})" if seg.matched_threats else ""
        segments_md += f"- `[{seg.start:05.2f}s - {seg.end:05.2f}s]` **{role_label}:** {seg.text}{threat_tag}\n"

    md_content = f"""# 🛡️ Forensic Incident Report: {report.incident_id}
**Analyzed At:** {report.analyzed_at.strftime("%Y-%m-%d %H:%M:%S UTC")}  
**Audio Target:** `{report.audio_file_name}` ({report.duration_seconds}s)  
**Triage Status:** {'🚨 MALICIOUS / VISHING ATTACK' if report.is_malicious else '✅ BENIGN / LOW RISK'}  

---

## 1. Executive Summary
- **Forensic Verdict:** 
{report.summary_verdict}
- **Combined Threat Score:** 
{report.combined_risk_score} / 100
- **Intent Risk Level:** 
{report.threat_analysis.risk_level} (Score: {report.threat_analysis.threat_score}/100)
- **Synthetic Voice Suspicion:** 
{report.acoustic_analysis.synthetic_suspicion_score} / 100

---

## 2. Acoustic & Signal Integrity
- **Cutoff Frequency:** 
{report.acoustic_analysis.cutoff_frequency_hz} Hz
- **High-Frequency Energy Ratio:** 
{report.acoustic_analysis.high_frequency_energy_ratio:.4f}
- **Telephony Profile Match:** 
{'Yes (Standard Bandwidth)' if report.acoustic_analysis.is_telephony_bandwidth else 'No (Wideband / Synthetic Audio)'}
- **Acoustic Flags:**
{acoustic_flags_md}

---

## 3. Social Engineering & Intent Indicators (NZ Vectors)
{hits_md}

---

## 4. Transcription Timeline
**Full Transcript:**  
> "{report.transcription.full_text}"

**Segment Details:**
{segments_md}

---

## 5. Containment & Remediation Checklist
{actions_md}
"""
    return md_content

def render_acoustic_plots(audio_bytes: bytes, file_suffix: str = ".wav"):
    """ฟังก์ชันวาด Time-Domain Waveform และ Frequency-Domain Spectrogram"""
    if not file_suffix.startswith("."):
        file_suffix = f".{file_suffix}"

    with tempfile.NamedTemporaryFile(delete=False, suffix=file_suffix) as tmp_plot:
        tmp_plot.write(audio_bytes)
        plot_path = tmp_plot.name

    converted_plot_path = None
    try:
        # แปลงเป็น .wav เสมอหากต้นฉบับไม่ใช่ .wav เพื่อป้องกัน libsndfile อ่านไม่ออก
        if not plot_path.lower().endswith(".wav"):
            wav_tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
            converted_plot_path = wav_tmp.name
            wav_tmp.close()
            
            subprocess.run([
                "afconvert", "-f", "WAVE", "-d", "LEI16@16000", "-c", "1",
                plot_path, converted_plot_path
            ], check=True)
            read_target = converted_plot_path
        else:
            read_target = plot_path

        data, sr = sf.read(read_target, dtype="float32")
        if data.ndim > 1:
            data = data.mean(axis=1)

        time_axis = np.linspace(0, len(data) / sr, num=len(data))

        fig, (ax_wave, ax_spec) = plt.subplots(2, 1, figsize=(10, 5), sharex=True)
        plt.subplots_adjust(hspace=0.35)

        # 1. Waveform Plot
        ax_wave.plot(time_axis, data, color="#1f77b4", linewidth=0.8)
        ax_wave.set_title("Time-Domain Waveform (Amplitude)")
        ax_wave.set_ylabel("Amplitude")
        ax_wave.grid(True, linestyle="--", alpha=0.5)

        # 2. Spectrogram Plot
        Pxx, freqs, bins, im = ax_spec.specgram(
            data,
            Fs=sr,
            NFFT=512,
            noverlap=256,
            cmap="inferno"
        )
        ax_spec.set_title("Frequency Spectrogram (Acoustic Density)")
        ax_spec.set_xlabel("Time (seconds)")
        ax_spec.set_ylabel("Frequency (Hz)")
        ax_spec.axhline(y=7500, color="cyan", linestyle="--", linewidth=1, label="PSTN/Telephony Cutoff (7.5kHz)")
        ax_spec.legend(loc="upper right", fontsize=8)

        st.pyplot(fig)
        plt.close(fig)
    finally:
        if os.path.exists(plot_path):
            os.remove(plot_path)
        if converted_plot_path and os.path.exists(converted_plot_path):
            os.remove(converted_plot_path)

uploaded_file = st.file_uploader(
    "Upload Call Recording or Voice Message (.wav, .mp3, .aiff)",
    type=["wav", "mp3", "aiff", "ogg", "m4a"]
)

if uploaded_file is not None:
    audio_bytes = uploaded_file.read()
    st.audio(audio_bytes, format="audio/wav")

    suffix = Path(uploaded_file.name).suffix

    if st.button("Run Threat Triage", type="primary"):
        progress_bar = st.progress(0, text="Initializing Forensics Pipeline...")
        
        def update_ui_progress(ratio: float, message: str):
            progress_bar.progress(min(max(ratio, 0.0), 1.0), text=message)

        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
            tmp_file.write(audio_bytes)
            tmp_path = Path(tmp_file.name)

        try:
            st.session_state["report"] = pipeline.run(
                tmp_path,
                progress_callback=update_ui_progress
            )
            st.session_state["audio_bytes"] = audio_bytes
            st.session_state["file_suffix"] = suffix
        finally:
            if tmp_path.exists():
                os.remove(tmp_path)
            progress_bar.empty()

    if "report" in st.session_state:
        report = st.session_state["report"]
        cached_audio = st.session_state.get("audio_bytes", audio_bytes)
        cached_suffix = st.session_state.get("file_suffix", suffix)

        st.divider()

        # Summary Metrics
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Incident ID", report.incident_id)
        col2.metric("Duration", f"{report.duration_seconds}s")
        col3.metric("Combined Threat Score", f"{report.combined_risk_score}/100")
        
        risk_color = "red" if report.is_malicious else "green"
        col4.markdown(f"**Status:** :{risk_color}[{'MALICIOUS' if report.is_malicious else 'BENIGN'}]")

        st.subheader("Forensic Verdict")
        if report.is_malicious:
            st.error(report.summary_verdict)
        else:
            st.success(report.summary_verdict)

        # Export Report Section
        md_report = generate_markdown_report(report)
        st.download_button(
            label="📥 Export SecOps Markdown Ticket (.md)",
            data=md_report,
            file_name=f"{report.incident_id}_forensic_ticket.md",
            mime="text/markdown",
            type="secondary"
        )

        # Tabs for Dual-Track Forensics
        tab_transcript, tab_acoustic, tab_indicators, tab_actions = st.tabs([
            "Transcript Timeline",
            "Acoustic & Signal Forensics",
            "Detected Intent Indicators",
            "Containment Steps"
        ])

        with tab_transcript:
            st.markdown("#### Full Transcript")
            st.info(report.transcription.full_text)

            # Attribution Banner
            scammer_tag = report.transcription.scammer_speaker_id
            if scammer_tag:
                st.error(f"🚨 **Threat Actor Identified:** `{scammer_tag}` exhibits high-confidence social engineering behavior.")
            else:
                st.success("✅ **Speaker Roles:** No clear malicious threat actor detected among speakers.")

            st.markdown("#### Diarized Timeline & Intent Attribution")
            for seg in report.transcription.segments:
                if seg.speaker_role == "SCAMMER":
                    role_badge = "🚨 **[SCAMMER / CALLER]**"
                    container_style = st.error
                elif seg.speaker_role == "VICTIM":
                    role_badge = "👤 **[TARGET / RECEIVER]**"
                    container_style = st.info
                else:
                    role_badge = f"🗣️ **[{seg.speaker}]**"
                    container_style = st.write

                time_str = f"`[{seg.start:05.2f}s - {seg.end:05.2f}s]` {role_badge} ({seg.speaker}): {seg.text}"
                
                # แสดงข้อความพร้อมแนบแท็กภัยคุกคามถ้ามี
                if seg.matched_threats:
                    st.markdown(time_str)
                    for threat in seg.matched_threats:
                        st.caption(f"&nbsp;&nbsp;&nbsp;&nbsp;⚠️ *Matched Trigger:* `{threat}`")
                else:
                    st.markdown(time_str)

        with tab_acoustic:
            st.markdown("#### Audio Spectrum & Synthesis Markers")
            c1, c2, c3 = st.columns(3)
            c1.metric("Cutoff Frequency", f"{report.acoustic_analysis.cutoff_frequency_hz} Hz")
            c2.metric("High-Frequency Ratio", f"{report.acoustic_analysis.high_frequency_energy_ratio:.4f}")
            c3.metric("Synthetic Voice Score", f"{report.acoustic_analysis.synthetic_suspicion_score}/100")

            if report.acoustic_analysis.acoustic_flags:
                st.markdown("##### 🚩 Acoustic Anomalies Detected:")
                for flag in report.acoustic_analysis.acoustic_flags:
                    st.warning(flag)
            else:
                st.success("Bandwidth matches standard PSTN/VoIP telephony profile.")

            st.markdown("#### Visual Forensics (Waveform & Spectrogram)")
            render_acoustic_plots(cached_audio, file_suffix=cached_suffix)

        with tab_indicators:
            if report.threat_analysis.hits:
                for hit in report.threat_analysis.hits:
                    st.warning(f"**[{hit.category}]** Matched phrase: '{hit.matched_text}' (Weight: {hit.weight})")
            else:
                st.write("No malicious indicators or scam patterns detected.")

        with tab_actions:
            if report.threat_analysis.containment_recommendations:
                for rec in report.threat_analysis.containment_recommendations:
                    st.markdown(f"- ⚠️ {rec}")
            else:
                st.write("No incident response actions required.")