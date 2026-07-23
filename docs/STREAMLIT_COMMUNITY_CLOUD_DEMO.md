# Streamlit Community Cloud Demo

## Purpose

The public demo uses synthetic recovery data. Do not enter real names, health
records, HRV/sleep measurements, Polar credentials, or screenshots containing
personal information.

## Deployment settings

- Repository: the GitHub repository containing this project
- Branch: `main` (or the branch used for the demo)
- Main file path: `src/cloud_app.py`
- Python dependencies: `requirements.txt`
- Secrets: none required for the synthetic-data demo

## Local check

```bash
.venv/bin/streamlit run src/cloud_app.py
```

## Community Cloud steps

1. Push this repository to GitHub.
2. Sign in to Streamlit Community Cloud with GitHub.
3. Select **New app**.
4. Choose the repository, branch, and `src/cloud_app.py`.
5. Deploy and open the generated `streamlit.app` URL.

## Before sharing

Replace the feedback placeholder in `src/cloud_app.py` with the final survey
URL, then redeploy. Keep the demo label and privacy warning visible.

This demo is for product feedback only. A production version needs user
authentication, a persistent database, explicit consent, and a hosting/privacy
arrangement suitable for health data.
