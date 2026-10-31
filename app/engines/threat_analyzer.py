import re
from typing import Any, Dict, List, Tuple 
from pydantic import BaseModel, Field


class ThreatHit(BaseModel):
    category: str
    indicator: str
    weight: int
    matched_text: str


class ThreatAnalysisReport(BaseModel):
    threat_score: int = Field(ge=0, le=100)
    risk_level: str  # LOW, MEDIUM, HIGH, CRITICAL
    detected_vectors: List[str]
    hits: List[ThreatHit]
    indicators_summary: Dict[str, int]
    containment_recommendations: List[str]


class NZVishingThreatAnalyzer:
    def __init__(self):
        # โครงสร้าง Ruleset สำหรับบริบท New Zealand พร้อมกำหนดค่าน้ำหนัก (Weights)
        self.rules: Dict[str, Dict[str, Any]] = {
            "NZ_BANK_IMPERSONATION": {
                "weight": 35,
                "patterns": [
                    r"\b(anz|asb|bnz|westpac|kiwibank|co-operative bank)\b",
                    r"\b(fraud (department|team|division)|suspicious activity detected)\b",
                    r"\b(safe (account|custody account|holding account)|transfer your funds)\b",
                    r"\b(freeze your account|compromised (card|account))\b",
                ],
                "description": "แอบอ้างสถาบันการเงินหลักในนิวซีแลนด์ หรือสั่งให้โอนเงินเข้า Safe Account",
            },
            "NZ_GOV_LAW_ENFORCEMENT": {
                "weight": 40,
                "patterns": [
                    r"\b(inland revenue|ird|tax return|tax audit|unpaid tax)\b",
                    r"\b(nz police|new zealand police|police national headquarters)\b",
                    r"\b(customs service|auckland airport customs|border clearance)\b",
                    r"\b(arrest warrant|court order|prosecution|legal action)\b",
                ],
                "description": "แอบอ้างหน่วยงานรัฐหรือตำรวจนิวซีแลนด์ (IRD / Police / Customs)",
            },
            "CREDENTIAL_AND_ACCESS_HARVEST": {
                "weight": 30,
                "patterns": [
                    r"\b(netcode|one[- ]time password|otp|verification code|security code)\b",
                    r"\b(internet banking (password|pin|login)|online banking details)\b",
                    r"\b(anydesk|teamviewer|remote support|quicksupport|screen share)\b",
                ],
                "description": "หลอกลวงขอรหัสยืนยันตัวตน (NetCode/OTP) หรือสั่งติดตั้งโปรแกรมรีโมต",
            },
            "COERCION_AND_URGENCY": {
                "weight": 20,
                "patterns": [
                    r"\b(immediately|right now|within (\d+|one|two) hours?|urgent)\b",
                    r"\b(do not hang up|stay on the line|keep this confidential)\b",
                    r"\b(do not tell (anyone|family|your bank)|keep quiet)\b",
                ],
                "description": "การสร้างภาวะฉุกเฉิน บังคับให้อยู่ในสาย และห้ามปรึกษาบุคคลภายนอก",
            },
        }

    def analyze(self, transcript: str) -> ThreatAnalysisReport:
        """วิเคราะห์ข้อความ Transcript และคำนวณคะแนนภัยคุกคาม"""
        normalized_text = transcript.lower()
        hits: List[ThreatHit] = []
        detected_categories: set = set()
        total_raw_score = 0
        category_counts: Dict[str, int] = {}

        for category, rule_data in self.rules.items():
            category_weight = rule_data["weight"]
            matched_in_category = False

            for pattern in rule_data["patterns"]:
                matches = re.finditer(pattern, normalized_text, re.IGNORECASE)
                for match in matches:
                    matched_str = match.group(0)
                    hits.append(
                        ThreatHit(
                            category=category,
                            indicator=pattern,
                            weight=category_weight,
                            matched_text=matched_str,
                        )
                    )
                    matched_in_category = True
                    category_counts[category] = category_counts.get(category, 0) + 1

            if matched_in_category:
                detected_categories.add(category)
                total_raw_score += category_weight

        # ปรับคะแนนให้อยู่ในช่วง 0 - 100
        threat_score = min(total_raw_score, 100)

        # การประเมินระดับความเสี่ยง
        risk_level = self._evaluate_risk_level(threat_score, detected_categories)
        recommendations = self._generate_recommendations(detected_categories, risk_level)

        return ThreatAnalysisReport(
            threat_score=threat_score,
            risk_level=risk_level,
            detected_vectors=list(detected_categories),
            hits=hits,
            indicators_summary=category_counts,
            containment_recommendations=recommendations,
        )

    @staticmethod
    def _evaluate_risk_level(score: int, categories: set) -> str:
        # หากมีการขอ NetCode/OTP ควบคู่กับแอบอ้างธนาคาร/หน่วยงานรัฐ ให้ปรับเป็น CRITICAL ทันที
        has_harvest = "CREDENTIAL_AND_ACCESS_HARVEST" in categories
        has_authority = ("NZ_BANK_IMPERSONATION" in categories) or ("NZ_GOV_LAW_ENFORCEMENT" in categories)

        if has_harvest and has_authority:
            return "CRITICAL"
        if score >= 70:
            return "HIGH"
        if score >= 35:
            return "MEDIUM"
        return "LOW"

    @staticmethod
    def _generate_recommendations(categories: set, risk_level: str) -> List[str]:
        recs = []
        if risk_level in ["HIGH", "CRITICAL"]:
            recs.append("ตัดสายทันที ห้ามปฏิบัติตามคำสั่งการโอนเงินหรือให้ข้อมูลใดๆ เพิ่มเติม")

        if "CREDENTIAL_AND_ACCESS_HARVEST" in categories:
            recs.append("หากเผลอให้ NetCode/Password ไปแล้ว ให้ระงับบัตรและติดต่อธนาคารผ่านเบอร์ทางการทันที")
            recs.append("หากติดตั้ง AnyDesk/TeamViewer ให้ตัดการเชื่อมต่ออินเทอร์เน็ต (Wi-Fi/LAN) ของอุปกรณ์ทันที")

        if "NZ_BANK_IMPERSONATION" in categories:
            recs.append("ติดต่อฝ่าย Fraud ของธนาคารโดยตรง (ใช้เบอร์ทางการหลังบัตร หรือ 0800 ประจำธนาคาร ห้ามโทรกลับเบอร์เดิม)")

        if "NZ_GOV_LAW_ENFORCEMENT" in categories:
            recs.append("IRD และ NZ Police จะไม่มีนโยบายโทรข่มขู่หรือสั่งให้โอนเงินเข้าบัญชีส่วนบุคคล รายงานเคสนี้ต่อ Netsafe หรือ CERT NZ")

        return recs