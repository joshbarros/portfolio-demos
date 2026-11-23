# Limitations

- At-least-once, not exactly-once. The reservation and catalog services accept an idempotency key;
  the notification service does not, so a retried notification can be delivered twice. The UI shows
  the `delivered_count` so the duplicate is visible instead of hidden.
- The idempotency store in the fake services is in memory. Restarting the fakes clears it.
- The demo flow is fixed in code. There is no visual flow editor and no arbitrary destination URL.
- Single Postgres instance, no queue broker, no horizontal workers in the deployed demo (the worker
  is a separate process, which is enough to prove the model).
- Signature secrets are per deployment; key rotation is out of scope.
- No authentication on the demo UI. The only writes it can perform are the five predefined scenarios
  and a replay of an existing execution.
