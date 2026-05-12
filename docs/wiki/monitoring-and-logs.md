# Monitoring & Logs

This page explains how to monitor backend health, background task failures, and basic system performance on Render.

## Daily Checkpoints

- Render backend service > Logs: live log stream and recent application logs.
- Render backend service > Metrics: CPU, memory, restart/deploy status, response time, and 5xx rates.
- Backend health endpoint: `/health`.
- Better Stack / Logtail source:
  - Production: `render-backend-prod`
  - Development, if available: `render-backend-dev`

## Render Log Stream Setup

1. Create a new Render log source in Better Stack.
2. Name the source `render-backend-prod` or `render-backend-dev`, depending on the environment.
3. Copy the syslog ingest host and source token provided by Better Stack.
4. In the Render Dashboard, go to `Integrations > Observability > Log Streams` from the workspace home page.
5. Add the Better Stack endpoint as the default destination.
6. Enter the endpoint in `HOST:6514` format.
7. Enter the Better Stack source token in the token field.
8. After saving, verify within a few minutes that backend logs are arriving in Better Stack.

If Papertrail is used instead, follow the same steps and use Papertrail's TLS syslog endpoint as the log endpoint.

## Alert Rules

Create alerts in Better Stack / Logtail for the following queries. Threshold: at least 1 error log within 15 minutes.

| Alarm | Query |
| --- | --- |
| Transcription failure | `Audio transcription failed for` |
| Transcript persistence failure | `Failed to persist transcript for media file` |
| AI tagging failure | `AI tagging failed for story` |

The notification target should be the team email address or the team Slack/Discord channel.

Warning to monitor during the first phase, without an alert:

```text
Whisper transcription for
```

## Health Check

Monitor the backend `/health` endpoint with Render or Better Stack uptime monitoring.

- Expected successful response: HTTP `200`, with `"status": "ok"` in the response body.
- Failure response: HTTP `503`, with `"status": "degraded"` in the response body.
- Alert condition: the endpoint fails or returns degraded status in 2 consecutive checks.

## Incident Checklist

1. Check CPU, memory, restarts, and 5xx rate in Render backend service > Metrics.
2. Check Render backend service > Logs for errors after the latest deploy.
3. Run the alert queries in Better Stack / Logtail.
4. Check the `/health` response to see whether `db` or `storage` is degraded.
5. Check the latest deploy time and the GitHub Actions deploy summary.

## Acceptance Criteria

- Backend logs are visible in the Render Logs screen.
- Logs coming from Render are visible in Better Stack / Logtail.
- The three background task error queries can filter the relevant logs.
- An alert is triggered when a test error log is generated.
- `/health` is monitored by the uptime monitor.
