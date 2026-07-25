"""
AViD Journal — Email notifications.

Sends transactional emails: submission confirmations, status updates.
Uses SMTP with configurable settings via environment variables.
"""

from __future__ import annotations

import logging
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

logger = logging.getLogger(__name__)

# ── Config ─────────────────────────────────────────────────────────────────

SMTP_HOST = os.environ.get("AVID_SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("AVID_SMTP_PORT", "587"))
SMTP_USER = os.environ.get("AVID_SMTP_USER", "")
SMTP_PASS = os.environ.get("AVID_SMTP_PASS", "")
SMTP_FROM = os.environ.get("AVID_SMTP_FROM", "no-reply@avid-journal.org")

EMAIL_ENABLED = bool(SMTP_USER and SMTP_PASS)


# ── Templates ──────────────────────────────────────────────────────────────

SUBMISSION_CONFIRMATION = """\
Hi {name},

Your paper "{title}" has been received by AViD Journal and is now under review.

Submission ID: {submission_id}
LLM Model(s): {llm_model}
Theorems analyzed: {n_theorems}
Verdict: {verdict_summary}

Our editorial board will review your submission. You'll receive another
email when a decision is made — typically within 2 weeks.

You can track your submission at: {journal_url}/submissions/{submission_id}

Thank you for contributing to the first fully automated mathematics journal.

— AViD Journal Editorial Board
"""


# ── Send ───────────────────────────────────────────────────────────────────

def send_submission_confirmation(
    email: str,
    name: str,
    title: str,
    submission_id: str,
    llm_model: str = "",
    n_theorems: int = 0,
    verdict_summary: str = "",
    journal_url: str = "https://avid-journal.github.io",
) -> bool:
    """Send a confirmation email after a paper is submitted.

    Returns True if sent successfully, False otherwise.
    Silently skips if SMTP is not configured.
    """
    if not EMAIL_ENABLED:
        logger.info(f"Email skipped (SMTP not configured) — would send to {email}")
        return False

    body = SUBMISSION_CONFIRMATION.format(
        name=name,
        title=title,
        submission_id=submission_id,
        llm_model=llm_model or "Not specified",
        n_theorems=n_theorems,
        verdict_summary=verdict_summary,
        journal_url=journal_url,
    )

    msg = MIMEMultipart()
    msg["From"] = SMTP_FROM
    msg["To"] = email
    msg["Subject"] = f"[AViD Journal] Submission received: {title} ({submission_id})"
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_FROM, email, msg.as_string())
        logger.info(f"Confirmation email sent to {email} for {submission_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {email}: {e}")
        return False
