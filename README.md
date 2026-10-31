<div align="center">

# 🛡️ Dual-Track Audio & Vishing Forensics Hub
### Threat-Informed Incident Triage & Voice Biometrics for New Zealand Telecommunications

![Python Version](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-macOS%20Apple%20Silicon%20(M1%2FM2%2FM3)-000000?style=for-the-badge&logo=apple&logoColor=white)
![Engine](https://img.shields.io/badge/ASR-Faster--Whisper%20(CTranslate2)-00A67E?style=for-the-badge)
![UI Framework](https://img.shields.io/badge/Dashboard-Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)
![Jurisdiction](https://img.shields.io/badge/Context-New%20Zealand%20(NZ)-00247D?style=for-the-badge)
![Security Domain](https://img.shields.io/badge/SecOps-Tier--1%20SOC%20Forensics-critical?style=for-the-badge)

<p align="center">
  <b>A fully localized, zero-cloud triage platform designed to correlate acoustic physical layer anomalies with New Zealand social engineering vectors.</b>
</p>

</div>

---

---

## 📌 Executive Overview

Vishing and authorized push payment (APP) fraud targeting New Zealand banking customers (e.g., ANZ, ASB, BNZ, Westpac) and government agencies (IRD, NZTA, CERT NZ) continue to rise. 

This platform bridges the gap between raw telecom audio recordings and SecOps incident response by implementing a **Dual-Track Correlation Engine**:
1. **Acoustic Signal Forensics (Track A):** Evaluates telephony frequency cutoffs (PSTN ~7.5 kHz boundaries) and high-frequency spectral ratios to flag potential voice cloning, TTS engines, or high-bandwidth spoofing.
2. **Semantic & NLP Threat Analysis (Track B):** Transcribes audio locally and evaluates social engineering vectors tailored to NZ banking heuristics (NetCode requests, urgent fund transfer coercion, remote access tools).
3. **Lightweight Diarization & Threat Attribution (Track C):** Clusters speakers based on spectral features (RMS Energy, Zero-Crossing Rate, Spectral Centroid) and maps malicious triggers to identify the threat actor (`SCAMMER`) versus the target (`VICTIM`).

---

## 🏗️ Architecture
+----------------------------+
                   |   Raw Audio Ingest (.m4a)  |
                   +--------------+-------------+
                                  |
                           [afconvert]
                   (16kHz Mono 16-bit PCM WAV)
                                  |
             +--------------------+--------------------+
             |                                         |
             v                                         v
   [ Track A: Acoustic ]                     [ Track B: Semantic ]
 - SciPy Welch PSD                         - Faster-Whisper Local
 - Telephony Cutoff (7.5kHz)               - Real-time Progress Tracking
 - High-Frequency Energy Ratio             - NZ Threat Vector Heuristics
             |                                         |
             +--------------------+--------------------+
                                  |
                   [ Track C: Speaker Clustering ]
                 - Lightweight 2-Means Diarization
                 - Dynamic Threat Attribution
                                  |
                                  v
                    +---------------------------+
                    |  Dual-Track Correlation   |
                    |   Risk Score (0 - 100)    |
                    +-------------+-------------+
                                  |
             +--------------------+--------------------+
             |                                         |
             v                                         v
   [ Interactive Dashboard ]                 [ SecOps Ticket Export ]
 - Waveform & Spectrogram Plots            - Standardized .md Report
 - Diarized Timeline & Badges              - Incident Containment Steps

 ## ✨ Key Features

- **Local & Privacy-Preserving:** Operates 100% locally on Apple Silicon / CPU. No audio data leaves the local workstation.
- **Native macOS Audio Ingestion:** Leverages native `afconvert` pipelines to ingest Voice Memos (`.m4a`), compressed MP3s, and standard PCM formats without external dependencies.
- **NZ Banking Threat Profiles:** Detects domain-specific phrases including *NetCode*, *security department*, *AnyDesk/TeamViewer*, *unauthorized card charges*, and *IRD refund*.
- **Real-Time Forensic Feedback:** Features an integrated progress callback pipeline providing live feedback during lengthy call recordings (e.g., 30+ minute streams).
- **Incident Ticket Export:** Generates standardized Markdown reports compatible with SOC incident management workflows (Jira, ServiceNow, GitHub Security Advisories).

---

## 🚀 Quickstart Guide

### 1. Prerequisites
- macOS (Optimized for Apple Silicon M-Series) or Linux
- Python 3.10 or higher
- System audio tool (`afconvert` built into macOS)

### 2. Installation
Clone the repository and set up a virtual environment:

```bash
git clone [https://github.com/your-username/vishing-forensics-hub.git](https://github.com/your-username/vishing-forensics-hub.git)
cd vishing-forensics-hub

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt

3. Run the Dashboard
Launch the local forensics console:
    bush
        python3 -m streamlit run app/ui/dashboard.py
Open your browser at http://localhost:8501.

📂 Project Structure
    vishing-forensics-hub/
├── app/
│   ├── core/
│   │   └── pipeline.py           # Dual-track pipeline orchestration
│   ├── engines/
│   │   ├── acoustic_forensics.py # Spectral density & frequency cutoff analysis
│   │   ├── diarizer.py           # Lightweight 2-speaker clustering
│   │   ├── threat_analyzer.py    # NZ-specific heuristic threat engine
│   │   └── transcriber.py        # Faster-Whisper wrapper with callback support
│   ├── models/
│   │   ├── report.py             # Forensic report schemas
│   │   └── transcript.py         # Diarized segment models
│   └── ui/
│       └── dashboard.py          # Streamlit UI & visual forensics
├── requirements.txt
├── .gitignore
└── README.md

🔒 Security & Privacy Notice
    This platform is intended for defensive digital forensics, threat hunting, and educational research. Always ensure you have proper authorization or regulatory compliance before recording or analyzing telecommunication data.

