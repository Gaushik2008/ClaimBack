# n8n Statutory Escalation Deadline Tracker

This workflow receives a policyholder grievance submission event, tracks the IRDAI 15-day statutory insurer turnaround deadline, and dispatches automated reminder notifications 7 days and 1 day before expiry.

## Workflow Structure
- **Webhook Node**: Receives POST `/webhook/claim-deadline` with payload:
  ```json
  {
    "claim_no": "CLM-12345",
    "user_email": "user@example.com",
    "gro_submission_date": "2026-11-24"
  }
  ```
- **Wait Node (8 Days)**: Pauses execution until 7 days remain before the 15-day statutory deadline.
- **Email Reminder (7 Days)**: Alerts the policyholder to follow up with the insurer's Grievance Redressal Officer.
- **Wait Node (6 Days)**: Pauses execution until 1 day remains.
- **Final Escalation Notice (1 Day)**: Alerts the policyholder to escalate the complaint to the Insurance Ombudsman under Rule 14(1) if the insurer has not resolved the claim.

## Setup & Import
1. In your n8n workspace, navigate to **Workflows** -> **Import from File**.
2. Select `n8n/deadline-tracker.json`.
3. Configure your SMTP / Email credentials on the email nodes (replace placeholder values with your production mail provider or WhatsApp provider).
4. Activate the workflow and configure the webhook URL in ClaimBack backend settings.
