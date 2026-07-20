## ## Run python:

Always use the project's uv virtual environment. Activate it before running any Python commands:
```powershell
.venv\Scripts\activate
```

Or prefix commands directly:
```powershell
uv run python script.py
uv run pytest tests/
```


## Storage/Database data location:

data located here: ~/.tradingagents/data (or %USERPROFILE%\.tradingagents\data on Windows)

## GCP free-tier only

ALL GCP services used by this app MUST stay on the free tier (no credit-card charges).

**Before adding any new GCP service dependency:**
1. Verify it has a documented free tier that covers expected usage
2. Document the free tier limits and expected usage in the relevant spec file
3. Add a runtime guard if the service's free tier has operational limits (e.g. RTDB writes/day cap)
4. Never enable a paid plan (Blaze, Always-Free Tier with overages, etc.) without the user's explicit approval

**Before deploying changes that touch GCP:**
1. Check the billing console for unexpected charges from prior periods
2. Disable any API that isn't strictly required for the running service (deletes resources but costs nothing on its own)
3. Run `gcloud billing...` projections or read current costs from the Billing Reports page

