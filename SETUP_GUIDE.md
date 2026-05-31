# DBBSA Setup & Implementation Guide

## Project Structure Overview

```
David Bedford/
├── landing.html                    # Updated landing page (School Admin removed from public)
├── manage.py                       # Django management script
├── requirements.txt                # Python dependencies
├── ARCHITECTURE.md                 # Monolithic vs microservices analysis
├── README.md                       # This file (after initial setup)
│
├── neural_village/
│   ├── __init__.py
│   ├── models.py                   # Core data models (School, Student, Parent, CBT_Session, etc.)
│   ├── middleware.py               # Domain routing, role-based access, token refresh
│   ├── settings.py                 # Multi-domain Django configuration
│   ├── urls.py                     # Multi-domain URL routing
│   ├── wsgi.py                     # Production WSGI entry
│   │
│   ├── auth/                       # Authentication app
│   │   ├── views.py               # Login, logout, 2FA verification
│   │   ├── urls.py
│   │   └── serializers.py
│   │
│   ├── student/                    # Student portal (/portal/student)
│   │   ├── views.py               # Dashboard, labs, progress
│   │   ├── urls.py
│   │   └── serializers.py
│   │
│   ├── instructor/                 # Instructor portal (/portal/instructor)
│   │   ├── views.py               # Grading, quiz deployment
│   │   ├── urls.py
│   │   └── serializers.py
│   │
│   ├── parent/                     # Parent portal (/portal/parent)
│   │   ├── views.py               # Child progress, payments
│   │   └── urls.py
│   │
│   ├── school_admin/               # School admin portal (admin.dbbsa.com)
│   │   ├── views.py               # Student/staff/hardware management
│   │   ├── middleware.py          # 2FA enforcement, domain check
│   │   ├── urls.py
│   │   └── serializers.py
│   │
│   ├── super_admin/                # Super admin portal (sys.neuralvillage.com)
│   │   ├── views.py               # Manage schools, global analytics
│   │   ├── middleware.py          # Extra security (IP whitelist)
│   │   ├── urls.py
│   │   └── serializers.py
│   │
│   ├── cbt/                        # Computer-Based Testing Engine
│   │   ├── views.py               # Test sessions, auto-save, token refresh
│   │   ├── tasks.py               # Celery background tasks
│   │   ├── urls.py
│   │   ├── models.py              # CBT_Session, CBT_Question, CBT_Quiz
│   │   └── serializers.py
│   │
│   ├── hardware/                   # Hardware sync & management
│   │   ├── views.py               # iPad/OpenBCI sync endpoints
│   │   ├── tasks.py               # Background sync, health checks
│   │   ├── urls.py
│   │   └── middleware.py
│   │
│   ├── api/                        # REST API endpoints
│   │   ├── public_urls.py         # Student/Instructor/Parent APIs
│   │   ├── school_admin_urls.py
│   │   ├── super_admin_urls.py
│   │   ├── permissions.py         # Custom DRF permissions
│   │   └── serializers.py
│   │
│   ├── core/                       # Shared utilities
│   │   ├── utils.py               # Helpers, validators
│   │   ├── constants.py           # Enums, choices
│   │   └── decorators.py          # @require_role, @require_domain
│   │
│   ├── templates/
│   │   ├── landing.html
│   │   ├── auth/
│   │   ├── student/
│   │   ├── instructor/
│   │   ├── school_admin/
│   │   └── super_admin/
│   │
│   └── static/
│       ├── css/
│       ├── js/
│       └── images/
│
├── tests/                          # Test suite
│   ├── test_models.py
│   ├── test_auth.py
│   ├── test_cbt.py
│   ├── test_permissions.py
│   └── conftest.py
│
├── docker-compose.yml              # Local development stack
├── .env.example                    # Environment variables template
└── logs/                           # Application logs
    └── neural_village.log
```

---

## Quick Start (Local Development)

### Prerequisites
- Python 3.13+
- PostgreSQL 14+
- Redis 7+
- Docker & Docker Compose (optional, for containerized setup)

### Option A: Docker Compose (Easiest)

```bash
# 1. Copy environment file
cp .env.example .env

# 2. Start containers
docker-compose up -d

# 3. Run migrations
docker exec neural-village python manage.py migrate

# 4. Create superuser
docker exec neural-village python manage.py createsuperuser

# 5. Load sample data
docker exec neural-village python manage.py loaddata sample_schools

# 6. Access
# Landing page: http://localhost:8000
# Admin: http://localhost:8000/admin
```

### Option B: Manual Setup

```bash
# 1. Create virtual environment
python -m venv .venv
source .venv/Scripts/activate  # On Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create PostgreSQL database
createdb neural_village

# 4. Set up environment
cp .env.example .env
# Edit .env with your database credentials

# 5. Run migrations
python manage.py migrate

# 6. Create superuser
python manage.py createsuperuser

# 7. Load sample data (schools, cohorts, students)
python manage.py loaddata sample_schools

# 8. Start development server
python manage.py runserver

# 9. Start Celery (in separate terminal)
celery -A neural_village worker -l info

# 10. Access
# Landing page: http://localhost:8000
# Admin: http://localhost:8000/admin
# Instructor portal: http://localhost:8000/portal/instructor
```

---

## Environment Variables (.env)

```bash
# Django
DEBUG=True
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=localhost,127.0.0.1,dbbsa.com,portal.lvh.me,portal.neuralvillage.com,admin.dbbsa.com,sys.neuralvillage.com

# Database
DB_ENGINE=django.db.backends.postgresql
DB_NAME=neural_village
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432

# Redis (Caching & Celery)
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1

# JWT
JWT_SECRET=your-jwt-secret
JWT_ALGORITHM=HS256

# Email (for notifications & password resets)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend  # Dev
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# Sentry (Error tracking)
SENTRY_DSN=https://...@sentry.io/...

# AWS (for static files, media storage)
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_STORAGE_BUCKET_NAME=neural-village-storage
```

---

## Database Migrations

```bash
# Create migrations after model changes
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Check migration status
python manage.py showmigrations

# Rollback last migration
python manage.py migrate neural_village 0001
```

---

## Loading Sample Data

```bash
# Create fixture with sample schools, students, cohorts
python manage.py shell

# In shell:
from django.contrib.auth.models import User
from neural_village.models import School, Student, Cohort, Instructor

# Create school
school = School.objects.create(
    name="Shehu Giwa Academy",
    location="Kaduna, Nigeria",
    primary_contact_email="principal@shehugiawaacademy.edu.ng",
    tracks_offered="both",
    subeb_verified=True
)

# Create instructor
user = User.objects.create_user("dr_bedford", password="demo123")
instructor = Instructor.objects.create(
    user=user,
    school=school,
    first_name="David",
    last_name="Bedford",
    specialization="Neurobiology"
)

# Create cohort
cohort = Cohort.objects.create(
    school=school,
    name="KNSB Pilot 2026",
    track="secondary",
    instructor=instructor,
    start_date="2026-01-15",
    end_date="2026-06-30"
)
```

---

## Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_cbt.py

# Run with coverage report
pytest --cov=neural_village

# Run tests matching pattern
pytest -k "test_token_refresh"
```

---

## Deployment to Production

### AWS Deployment (Recommended)

```bash
# 1. Create RDS PostgreSQL instance
# 2. Create ElastiCache Redis cluster
# 3. Create Application Load Balancer
# 4. Push code to GitHub
# 5. Set up GitHub Actions for CI/CD
# 6. Deploy to EC2 or ECS with Docker

# Environment variables in AWS Secrets Manager
aws secretsmanager create-secret --name neural-village/prod --secret-string file://prod.env
```

### Nginx Configuration (for multiple domains)

```nginx
# /etc/nginx/sites-available/dbbsa.conf

# Public portal (dbbsa.com)
server {
    server_name dbbsa.com www.dbbsa.com;
    location / {
        proxy_pass http://django-app:8000;
        proxy_set_header Host $host;
    }
}

# School Admin (admin.dbbsa.com)
server {
    server_name admin.dbbsa.com;
    location / {
        proxy_pass http://django-app:8000;
        proxy_set_header Host $host;
    }
}

# Super Admin (sys.neuralvillage.com)
server {
    server_name sys.neuralvillage.com;
    # IP whitelist for extra security
    allow 203.0.113.0/24;  # Your office IP
    deny all;
    
    location / {
        proxy_pass http://django-app:8000;
        proxy_set_header Host $host;
    }
}
```

---

## Key Implementation Notes

### 1. Silent Token Refresh (Critical for CBT)

The `SilentTokenRefreshMiddleware` prevents "Your session expired" mid-test:

```python
# Every CBT request checks:
if session_has_active_cbt and token_expires_in_less_than_5_minutes:
    refresh_token_silently()
    attach_new_token_to_response_header()
```

### 2. Hardware State Mismatch (Instructor Override)

If an iPad shows offline but student has it:

```python
# Instructor can create override
HardwareAsset.override_active_until = now + 2_hours
# Student can proceed with lab work
# System logs: "Override by Dr. Bedford - Network glitch"
```

### 3. Data Security (Database-Level Filtering)

NEVER rely on frontend filtering:

```python
# BAD: Frontend gets all students
students = Student.objects.all()

# GOOD: Backend filters by role
if user.role == 'instructor':
    students = Student.objects.filter(cohort__instructor=user.instructor_profile)
elif user.role == 'school_admin':
    students = Student.objects.filter(school=user.profile.school)
```

---

## Monitoring & Logging

### Application Logs
```bash
tail -f logs/neural_village.log
```

### Database Monitoring
```bash
# Connect to PostgreSQL and check slow queries
psql -U postgres neural_village
neural_village=# SELECT query, mean_time FROM pg_stat_statements ORDER BY mean_time DESC;
```

### Celery Task Monitoring
```bash
# Monitor Celery tasks in real-time
celery -A neural_village inspect active
```

---

## Troubleshooting

### CBT Session Not Saving
```bash
# Check Celery worker is running
celery -A neural_village worker -l info

# Check Redis connection
redis-cli ping  # Should return PONG
```

### Hardware Offline Blocking Students
```python
# Create instructor override (Django shell)
from neural_village.models import HardwareAsset
from datetime import timedelta
from django.utils import timezone

asset = HardwareAsset.objects.get(mac_address="aa:bb:cc:dd:ee:ff")
asset.override_active_until = timezone.now() + timedelta(hours=2)
asset.instructor_override_reason = "Network glitch - student has device"
asset.save()
```

### Migration Errors
```bash
# If migrations are stuck
python manage.py migrate --fake-initial
python manage.py migrate
```

---

## Support & Contact

- **Lead Developer:** Japhet Kineze
- **Documentation:** This file + ARCHITECTURE.md
- **Issues:** GitHub Issues / Jira
- **Monitoring:** Sentry + DataDog dashboards
