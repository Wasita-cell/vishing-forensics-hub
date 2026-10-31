# 🛡️ Audio & Vishing Forensics Hub (NZ Threat Context)

An automated dual-track acoustic and semantic forensics platform engineered to triage voice phishing (vishing), impersonation attacks, and synthetic audio threats targeting New Zealand telecommunications.

## 📌 Executive Overview
Vishing and authorized push payment (APP) fraud targeting New Zealand banking customers (ANZ, ASB, BNZ, Westpac) and government agencies (IRD, CERT NZ) continue to rise.

This platform bridges the gap between raw telecom audio recordings and SecOps incident response by implementing a Dual-Track Correlation Engine:
1. Acoustic Signal Forensics (Track A): Evaluates telephony frequency cutoffs (PSTN ~7.5 kHz boundaries) and high-frequency spectral ratios to flag potential voice cloning or synthetic audio.
2. Semantic & NLP Threat Analysis (Track B): Transcribes audio locally and evaluates social engineering vectors tailored to NZ banking heuristics (NetCode requests, urgent transfer coercion, remote access tools).
3. Lightweight Diarization & Threat Attribution (Track C): Clusters speakers based on spectral features and maps malicious triggers to identify the threat actor (SCAMMER) versus the target (VICTIM).

## 🚀 Quickstart Guide

### 1. Installation
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

### 2. Run the Dashboard
python3 -m streamlit run app/ui/dashboard.py

## 📂 Project Structure
- app/core/: Dual-track pipeline orchestration
- app/engines/: Acoustic, Diarizer, Threat Analyzer, Transcriber
- app/models/: Pydantic data schemas
- app/ui/: Streamlit forensic dashboard
