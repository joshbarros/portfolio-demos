# Limitations

- The PDF is a demonstration document, not a fiscal invoice. It says so in the footer.
- Users are fictional and chosen in a dropdown; there is no authentication in the demo. In a real
  deployment the role and organization would come from the session, never from the request.
- Roles are simplified: a reviewer can also create tickets.
- No payments, OCR, digital signature, tax integration, email delivery or file storage beyond the
  generated PDF stream.
- Single Postgres instance; no queue or background worker is needed for this flow.
- Rejection reasons are stored but the UI does not yet ask for one.
