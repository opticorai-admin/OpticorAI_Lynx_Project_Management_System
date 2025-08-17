## OpticorAI Project Management System

End‑to‑end task management with role‑based access, automatic task evaluation, KPI weighting, employee progress analytics, in‑app notifications, and optional email 2FA.

### Key Features
- Email login with optional email OTP 2FA
- Roles: Admin, Manager, Employee with strict permissions
- Tasks: creation, edit, approval, evaluation, file upload/download
- Automatic evaluation with configurable formula and penalties/bonuses
- KPI, Quality Type, Priority Type management
- Employee progress scoring and reports (Excel/PDF)
- In‑app notifications with best‑effort email

### Architecture
- Django 5.1 project with a single domain app `core`
- Custom user model `core.CustomUser`
- Views: class‑based (CBVs) throughout
- Services: pure functions for evaluation and progress
- Context processors for user and notifications
- Template tags for permissions and visual badges

## Data Model (ER Diagram)

```mermaid
erDiagram
  CUSTOMUSER ||--o{ CUSTOMUSER : created_users
  CUSTOMUSER ||--o{ CUSTOMUSER : supervised_users
  CUSTOMUSER ||--o{ TASK : responsible
  CUSTOMUSER ||--o{ TASK : created_by
  CUSTOMUSER ||--o{ TASK : evaluated_by
  CUSTOMUSER ||--o{ NOTIFICATION : recipient
  CUSTOMUSER ||--o{ NOTIFICATION : sender
  CUSTOMUSER ||--o{ KPI : created_by
  CUSTOMUSER ||--o{ EMPLOYEEPROGRESS : employee
  CUSTOMUSER ||--o{ EMPLOYEEPROGRESS : manager
  CUSTOMUSER ||--o{ EMPLOYEEPROGRESS : calculated_by

  TASKPRIORITYTYPE ||--o{ TASK : priority
  KPI ||--o{ TASK : kpi
  QUALITYTYPE ||--o{ TASK : quality

  TASKEVALUATIONSETTINGS {
    string formula_name
    boolean use_quality_score
    boolean use_priority_multiplier
    boolean use_time_bonus_penalty
    boolean use_manager_closure_penalty
    float early_completion_bonus_per_day
    float max_early_completion_bonus
    float late_completion_penalty_per_day
    float max_late_completion_penalty
    float manager_closure_penalty
    string evaluation_formula
  }

  CUSTOMUSER {
    int id
    string email
    string username
    string user_type
    string designation
    int created_by_id
    int under_supervision_id
    string avatar
    date created_date
    time created_time
  }

  KPI {
    int id
    string name
    float weight
    string description
    boolean is_active
    int sort_order
    int created_by_id
  }

  QUALITYTYPE {
    int id
    string name
    float percentage
    string description
    boolean is_active
    int sort_order
    int created_by_id
  }

  TASKPRIORITYTYPE {
    int id
    string name
    string code
    float multiplier
    string description
    boolean is_active
    int sort_order
  }

  TASK {
    int id
    string issue_action
    int responsible_id
    int priority_id
    int kpi_id
    int quality_id
    date start_date
    date target_date
    date close_date
    int created_by_id
    string status
    float percentage_completion
    string comments
    string approval_status
    string file_upload
    string evaluation_status
    int quality_score
    string evaluation_comments
    int evaluated_by_id
    datetime evaluated_date
    datetime completion_date
    float final_score
    float quality_score_calculated
    float priority_multiplier
    float time_bonus_penalty
    boolean manager_closure_penalty_applied
    datetime created_date
    datetime updated_date
  }

  EMPLOYEEPROGRESS {
    int id
    int employee_id
    int manager_id
    date period_start
    date period_end
    float total_progress_score
    json progress_breakdown
    datetime calculation_date
    int calculated_by_id
    text notes
    datetime created_at
    datetime updated_at
  }

  NOTIFICATION {
    int id
    int recipient_id
    int sender_id
    text message
    datetime created_at
    boolean read
    string link
  }
```

## Permission Matrix

| Capability | Admin | Manager | Employee |
| --- | --- | --- | --- |
| View tasks | No | Yes (self and subordinates) | Yes (self) |
| Create tasks | No | Yes (self or subordinates; requires manager to be supervised to self‑assign) | Yes (self only) |
| Edit tasks | No | Yes (subordinates only; not own) | No |
| Delete tasks | No | Yes (subordinates only; not own) | No |
| Upload file | No | Yes (own or subordinates; task not closed for employee) | Yes (own; not closed) |
| Download file | No | Yes (own or subordinates) | Yes (own) |
| Approve tasks | No | Yes (subordinates only; not own) | No |
| Evaluate tasks | No | Yes (subordinates only; not own) | No |
| Manage KPIs | No | Yes (own KPIs) | No |
| Manage Quality Types | Yes | No | No |
| Manage Priority Types | Yes | No | No |
| View users | Yes (all except self-filtered) | Yes (subordinates) | No |
| Create users | Yes (any role) | Yes (employees under self) | No |
| Edit users | Yes (any) | Yes (subordinates) | Yes (self profile only) |
| Delete users | Yes | Yes (subordinates) | No |
| Set user password | Yes | No | No |
| Settings dashboard | No | Yes | No |
| Update task statuses | No | Yes (subordinates) | No |
| Progress report (export) | No | Yes (subordinates) | No |
| Employee progress pages | No | Yes (subordinates) | No |

Notes:
- Managers cannot approve/evaluate/edit/delete tasks assigned to themselves; only their supervisor can.
- Employees can upload only to their own tasks and only if the task is not closed.

## Evaluation Logic (Summary)
Final Score = (Quality Percentage × Priority Multiplier) + Time Bonus/Penalty ± Manager Closure Penalty
- Early completion: +bonus_per_day up to max
- Late completion: −penalty_per_day up to max
- Manager closure penalty applies when closing incomplete tasks

## Project Layout (Highlights)
- App: `core/`
  - Models: users, tasks, KPIs, quality types, priorities, notifications, progress, evaluation settings
  - Views: CBVs for auth, dashboard, users, tasks, settings, notifications, progress, reports
  - Forms: role‑aware forms for each entity and evaluation/settings
  - Services: `services/task_service.py`, `services/progress_service.py`
  - Template tags: `evaluation_filters`, `score_tags`, `task_permissions`
  - Context processors: logged user, notifications, debug flag
  - Management commands: `setup_evaluation_system`, `fix_priorities`, `test_task_evaluation`

## Setup
1) Install dependencies
```
pip install -r requirements.txt
```
2) Configure environment (examples below). On dev, default settings are fine.
3) Apply migrations and create a superuser
```
python manage.py migrate
python manage.py createsuperuser
```
4) (Optional) Seed evaluation system and defaults
```
python manage.py setup_evaluation_system
python manage.py fix_priorities
```
5) Run server
```
python manage.py runserver
```

## Configuration
Minimum variables (dev example):
```
DJANGO_SETTINGS_MODULE=OpticorAI_project_management_system.settings.dev
DJANGO_SECRET_KEY=change-me
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
ENABLE_EMAIL_2FA=true
```
Email (SMTP example):
```
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
EMAIL_USE_TLS=true
DEFAULT_FROM_EMAIL=no-reply@example.com
```
Production extras:
```
DJANGO_SETTINGS_MODULE=OpticorAI_project_management_system.settings.prod
DATABASE_URL=postgres://user:password@host:5432/dbname
REDIS_URL=redis://host:6379/0
CONN_MAX_AGE=60
```
Evaluation defaults (optional overrides for seeding):
```
PRIORITY_MULTIPLIER_LOW=1.0
PRIORITY_MULTIPLIER_MEDIUM=1.05
PRIORITY_MULTIPLIER_HIGH=1.2
QUALITY_POOR_PERCENTAGE=40.0
QUALITY_AVERAGE_PERCENTAGE=60.0
QUALITY_GOOD_PERCENTAGE=80.0
QUALITY_EXCEED_PERCENTAGE=90.0
QUALITY_EXCEPTIONAL_PERCENTAGE=100.0
```

## Static Files
- App static: `core/static/`
- Project static: `static/`
- Collected static: `staticfiles/` (via `python manage.py collectstatic`)
WhiteNoise is enabled in production to serve static files.

Local vendor assets (replace CDN):
- Chart.js 4.4.3 (UMD) → `static/vendor/chart.js`
- chartjs-plugin-datalabels 2.2.0 → `static/vendor/chartjs-plugin-datalabels.js`

Windows PowerShell example:
```
iwr -Uri https://cdn.jsdelivr.net/npm/chart.js@4.4.3/dist/chart.umd.min.js -OutFile static\vendor\chart.js
iwr -Uri https://cdn.jsdelivr.net/npm/chartjs-plugin-datalabels@2.2.0/dist/chartjs-plugin-datalabels.min.js -OutFile static\vendor\chartjs-plugin-datalabels.js
```

## Management Commands
- `setup_evaluation_system`: seeds priority types, quality types, and evaluation settings
- `fix_priorities`: updates priority multipliers from env
- `test_task_evaluation`: runs example evaluations against real model instances

## Production Notes
- Set `DJANGO_SETTINGS_MODULE=OpticorAI_project_management_system.settings.prod` and required env vars (`DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, email, DB)
- Run `python manage.py collectstatic --noinput`
- Ensure SSL termination so security settings (HSTS, secure cookies, redirect) apply



## Local Network (LAN) Installation

Use this to run the app on one machine inside your office network while multiple computers access it via the server's LAN IP (e.g., `http://192.168.1.50:8000`).

### Prerequisites
- Python 3.11.x and pip (virtual environment recommended)
- One machine acts as the server; others will access it via a browser
- Open the chosen port (default 8000) in the server firewall

### Environment (.env)
Create a `.env` file in the project root (same folder as `manage.py`). For LAN, prefer development settings to avoid production‑only requirements (Cloudinary, SSL redirect).

```env
DJANGO_SETTINGS_MODULE=OpticorAI_project_management_system.settings.dev
DJANGO_SECRET_KEY=change-me
DJANGO_ALLOWED_HOSTS=*,localhost,127.0.0.1,192.168.1.50
ENABLE_EMAIL_2FA=false
SITE_BASE_URL=http://192.168.1.50:8000
# Optional SMTP if you want real emails in LAN
# EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
# EMAIL_HOST=smtp.example.com
# EMAIL_PORT=587
# EMAIL_HOST_USER=
# EMAIL_HOST_PASSWORD=
# EMAIL_USE_TLS=true
# DEFAULT_FROM_EMAIL=no-reply@example.com
```

Replace `192.168.1.50` with your server machine's LAN IP.

### First‑time setup (run on the server machine)
```bash
python -m venv .venv
.\.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # Linux/macOS

pip install -r requirements.txt

python manage.py migrate
python manage.py createsuperuser

# Optional seed data
python manage.py setup_evaluation_system
python manage.py fix_priorities
```

### Run options

#### Option A — Quick LAN test (development server)
Suitable for demos/small teams; not a hardening substitute.
```bash
python manage.py runserver 0.0.0.0:8000
```

#### Option B — Windows production‑like (Waitress)
```powershell
set DJANGO_SETTINGS_MODULE=OpticorAI_project_management_system.settings.dev
waitress-serve --listen=0.0.0.0:8000 OpticorAI_project_management_system.wsgi:application
```

#### Option C — Linux production‑like (Gunicorn)
```bash
export DJANGO_SETTINGS_MODULE=OpticorAI_project_management_system.settings.dev
gunicorn OpticorAI_project_management_system.wsgi:application --bind 0.0.0.0:8000 --workers 3
```

#### Option D — Windows IIS (FastCGI)
An IIS `web.config` is provided. If you choose IIS:
- Update the `scriptProcessor`, `PYTHONHOME`, and `PYTHONPATH` to your venv paths
- Either switch to dev settings or fully configure prod (Cloudinary, SSL)

```xml
<!-- OpticorAI_project_management_system/web.config snippet -->
<environmentVariable name="DJANGO_SETTINGS_MODULE" value="OpticorAI_project_management_system.settings.dev" />
<environmentVariable name="DJANGO_ALLOWED_HOSTS" value="localhost,127.0.0.1,192.168.1.50" />
```

### Client access (other computers)
- Ensure the server firewall allows inbound on the chosen port (e.g., 8000)
- On client machines, open a browser to: `http://SERVER_LAN_IP:8000`
- Log in using the superuser you created

### Firewall quick tips (Windows)
Run PowerShell as Administrator:
```powershell
New-NetFirewallRule -DisplayName "Django LAN 8000" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow
```

### Troubleshooting
- 403/Bad Request host errors: include your LAN IP/hostname in `DJANGO_ALLOWED_HOSTS`
- Redirects to HTTPS or 403 with CSRF in LAN: you are likely using prod settings; switch to dev (`DJANGO_SETTINGS_MODULE=...settings.dev`)
- Static files missing in prod settings: run `python manage.py collectstatic --noinput` and configure a proper server/static middleware (dev mode serves static automatically)
- Email OTP not arriving: either disable `ENABLE_EMAIL_2FA` or set valid SMTP settings
- Port in use: change to another port, e.g., `0.0.0.0:8080`