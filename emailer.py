"""
Email reminder system for monthly treasury bond purchases.

Sends a detailed email at the start of each month with:
- Which bond to buy
- Exact dollar amount
- TreasuryDirect.gov link and form instructions
"""

import os
import smtplib
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from planner import generate_investment_plan, format_plan_table
from bonds import get_next_purchase, URLS


def build_purchase_email(plan: dict) -> tuple[str, str] | None:
    """
    Build the email subject and HTML body for this month's purchase.
    Returns (subject, html_body) or None if no purchase is due.
    """
    details = get_next_purchase(plan)
    if not details:
        return None

    month_num = details["month"]
    subject = f"Treasury Bond Purchase Reminder — Batch #{month_num} ({details['purchase_date']})"

    steps_html = "\n".join(f"<li>{step}</li>" for step in details["form_fields"]["steps"])
    notes_html = "\n".join(f"<li>{note}</li>" for note in details["form_fields"]["notes"])

    html = f"""\
<html>
<body style="font-family: Arial, sans-serif; max-width: 700px; margin: 0 auto; padding: 20px;">
    <h1 style="color: #1a5276;">Treasury Bond Purchase Reminder</h1>
    <h2 style="color: #2e86c1;">Batch #{month_num} — {details['purchase_date']}</h2>

    <table style="border-collapse: collapse; width: 100%; margin: 20px 0;">
        <tr style="background: #1a5276; color: white;">
            <th style="padding: 12px; text-align: left;">Field</th>
            <th style="padding: 12px; text-align: left;">Value</th>
        </tr>
        <tr style="background: #f8f9fa;">
            <td style="padding: 10px; border-bottom: 1px solid #dee2e6;"><strong>Action</strong></td>
            <td style="padding: 10px; border-bottom: 1px solid #dee2e6;">{details['action']}</td>
        </tr>
        <tr>
            <td style="padding: 10px; border-bottom: 1px solid #dee2e6;"><strong>Security Type</strong></td>
            <td style="padding: 10px; border-bottom: 1px solid #dee2e6;">{details['form_fields']['security_type']}</td>
        </tr>
        <tr style="background: #f8f9fa;">
            <td style="padding: 10px; border-bottom: 1px solid #dee2e6;"><strong>Term</strong></td>
            <td style="padding: 10px; border-bottom: 1px solid #dee2e6;">{details['form_fields']['term']}</td>
        </tr>
        <tr>
            <td style="padding: 10px; border-bottom: 1px solid #dee2e6;"><strong>Face Value</strong></td>
            <td style="padding: 10px; border-bottom: 1px solid #dee2e6;"><strong>{details['face_value']}</strong></td>
        </tr>
        <tr style="background: #f8f9fa;">
            <td style="padding: 10px; border-bottom: 1px solid #dee2e6;"><strong>Est. Purchase Price</strong></td>
            <td style="padding: 10px; border-bottom: 1px solid #dee2e6;">{details['estimated_purchase_price']}</td>
        </tr>
        <tr>
            <td style="padding: 10px; border-bottom: 1px solid #dee2e6;"><strong>Est. Interest Earned</strong></td>
            <td style="padding: 10px; border-bottom: 1px solid #dee2e6;">{details['estimated_interest']}</td>
        </tr>
        <tr style="background: #f8f9fa;">
            <td style="padding: 10px; border-bottom: 1px solid #dee2e6;"><strong>Maturity Date</strong></td>
            <td style="padding: 10px; border-bottom: 1px solid #dee2e6;">{details['maturity_date']}</td>
        </tr>
        <tr>
            <td style="padding: 10px; border-bottom: 1px solid #dee2e6;"><strong>Reinvest?</strong></td>
            <td style="padding: 10px; border-bottom: 1px solid #dee2e6;">{details['form_fields']['reinvestment']}</td>
        </tr>
    </table>

    <h3 style="color: #1a5276;">Step-by-Step Purchase Instructions</h3>
    <ol style="line-height: 1.8;">
        {steps_html}
    </ol>

    <div style="background: #d4efdf; padding: 15px; border-radius: 8px; margin: 20px 0;">
        <strong>Quick Links:</strong><br>
        <a href="{details['login_url']}" style="color: #1a5276;">Log in to TreasuryDirect</a> |
        <a href="{details['treasury_direct_url']}" style="color: #1a5276;">BuyDirect Page</a> |
        <a href="{details['upcoming_auctions_url']}" style="color: #1a5276;">Upcoming Auctions</a>
    </div>

    <h3 style="color: #1a5276;">Important Notes</h3>
    <ul style="line-height: 1.8;">
        {notes_html}
    </ul>

    <hr style="margin: 30px 0;">
    <p style="color: #888; font-size: 12px;">
        This is an automated reminder from your Treasury Bond Ladder Agent.
    </p>
</body>
</html>
"""
    return subject, html


def send_reminder_email(plan: dict, recipient_email: str | None = None) -> dict:
    """
    Send this month's purchase reminder email via SMTP.

    Required environment variables:
        SMTP_HOST: SMTP server hostname (e.g., smtp.gmail.com)
        SMTP_PORT: SMTP port (e.g., 587)
        SMTP_USER: SMTP username/email
        SMTP_PASSWORD: SMTP password or app-specific password
        RECIPIENT_EMAIL: Where to send reminders (can be overridden by parameter)
    """
    smtp_host = os.environ["SMTP_HOST"]
    smtp_port = int(os.environ["SMTP_PORT"])
    smtp_user = os.environ["SMTP_USER"]
    smtp_password = os.environ["SMTP_PASSWORD"]
    recipient = recipient_email or os.environ["RECIPIENT_EMAIL"]

    email_content = build_purchase_email(plan)
    if not email_content:
        return {"status": "skipped", "reason": "No purchase due this month."}

    subject, html_body = email_content

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = recipient
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_user, recipient, msg.as_string())

    return {
        "status": "sent",
        "to": recipient,
        "subject": subject,
        "timestamp": datetime.now().isoformat(),
    }


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    plan = generate_investment_plan()
    email = build_purchase_email(plan)
    if email:
        print(f"Subject: {email[0]}")
        print(f"\nPreview (first 500 chars):\n{email[1][:500]}...")
    else:
        print("No purchase due this month.")
