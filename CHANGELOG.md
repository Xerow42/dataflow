# DataFlow Release Notes

## Corrected and shareable release — November 2026

- Strengthened validation of missing arrays, inconsistent array lengths,
  malformed dates, non-finite numbers, humidity bounds, and empty payloads.
- Restricted temperature imputation to genuinely isolated single-day gaps.
- Corrected seven-calendar-day rolling averages and refreshed them across
  the stored history after partial or overlapping database imports.
- Fixed the daily-chart date key, month-gap visualization, and the display of
  unavailable precipitation/temperature values.
- Added initial dashboard date filters based on actual stored data.
- Added API date validation, safer pagination, and modern FastAPI startup.
- Added a `--city` CLI option and nonzero exit status when any city fails.
- Improved database error rollback so a failed city does not contaminate
  subsequent pipeline runs.
- Updated the frontend to use a development proxy and an nginx reverse proxy
  in Docker; installed dependencies reproducibly using `npm ci`.
- Restricted direct DB/API host ports to localhost for safer local operation;
  made the pipeline service on-demand via a Compose profile.
- Added GitHub Actions CI, regression tests, and dependency security checks.
- Updated vulnerable Python and JavaScript dependency versions.
- Removed local-only files, installed dependencies, and database state from
  the shareable archive; `.env.example` contains placeholders only.

### Verification

- Python unit, API and offline integration test suite: executed successfully.
- React/Vite production build: executed successfully.
- One-city offline ETL run into a fresh SQLite database: executed successfully.
- npm and direct Python dependency audits: performed.

### Not verified here

The complete PostgreSQL + Docker Compose runtime was not executed because
Docker and PostgreSQL are not installed in the verification environment.
The project includes Docker/Compose files and instructions for running that
check locally or in a suitable CI environment.
