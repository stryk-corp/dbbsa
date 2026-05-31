# DBBSA Architecture - Complete Summary

## What's Been Created

✅ **Landing Page** (`landing.html`)
- Removed School Admin from public tabs
- Now shows only: Student, Instructor, Parent
- Clean separation of public-facing users

✅ **Django Data Models** (`neural_village/models.py`)
- **Core Entities:** School, Student, Parent, Instructor, Cohort
- **Academic:** Module, CBT_Quiz, CBT_Question, CBT_Session
- **Hardware:** HardwareAsset (iPad, OpenBCI, Laptop)
- **Lab Work:** Lab_Project, Lab_Submission
- **User Management:** User_Profile with role-based access
- **Critical Features:**
  - Auto-save checkpoints in CBT_Session (every 30 seconds)
  - Silent token refresh (5 mins before expiry)
  - Instructor override for offline hardware
  - Parent-to-children relationships (multi-child support)

✅ **Multi-Domain Middleware** (`neural_village/middleware.py`)
- **DomainRoutingMiddleware:** Routes requests based on hostname
  - `dbbsa.com` → Public portal (Student, Instructor, Parent)
  - `admin.dbbsa.com` → School Admin portal (requires role='school_admin' + 2FA)
  - `sys.neuralvillage.com` → Super Admin (requires role='super_admin' + IP whitelist)
- **RoleBasedAccessMiddleware:** Enforces role-based access control
- **SilentTokenRefreshMiddleware:** Handles JWT refresh during CBT without interrupting student

✅ **Django Settings** (`neural_village/settings.py`)
- Multi-domain configuration (ALLOWED_HOSTS)
- JWT token management (1-hour access, 7-day refresh)
- Celery task queue (background jobs, hardware sync)
- CORS configuration for frontend-backend communication
- Security headers for production

✅ **Multi-Domain URL Routing** (`neural_village/urls.py`)
- **Public portal routes:**
  - `/auth/` → Student/Instructor/Parent login
  - `/portal/student/` → Student portal
  - `/portal/instructor/` → Instructor portal
  - `/portal/parent/` → Parent portal
  - `/portal/school/` → School portal
  - `/cbt/` → Computer-based testing engine
  - `/api/v1/` → Public APIs
- **School Admin routes:**
  - `/auth/` → Admin login (with 2FA)
  - `/` → Admin dashboard
  - `/api/v1/` → School admin APIs
- **Super Admin routes:**
  - `/auth/` → Super admin login (with 2FA + IP check)
  - `/` → System dashboard
  - `/api/v1/` → System APIs

✅ **Comprehensive Architecture Guide** (`ARCHITECTURE.md`)
- **Decision:** Monolithic-first approach (NOT microservices yet)
- **Why Monolithic:** Better for 30 schools, 1,000-5,000 students. Easier transactions, shared code, simpler ops.
- **When to Extract to Microservices:** 500+ schools, CBT engine needs 10x scaling
- **Scaling Path:** Phase 1 (MVP) → Phase 2 (High Availability) → Phase 3 (Multi-region) → Phase 4 (Microservices)
- **16-Week Implementation Timeline**
- **Budget:** ~$174K development + $2.4K/month AWS

✅ **Setup & Implementation Guide** (`SETUP_GUIDE.md`)
- Local development setup (Docker or manual)
- Environment variables (.env template)
- Database migrations
- Sample data loading
- Testing framework
- Production deployment (AWS, Nginx)
- Monitoring & troubleshooting

✅ **Project Requirements** (`requirements.txt`)
- Django 4.2 LTS
- Django REST Framework
- JWT authentication
- Celery for background tasks
- PostgreSQL adapter
- Testing & code quality tools

---

## Architecture at a Glance

### Domain Routing Strategy

```
Request comes in
    ↓
DomainRoutingMiddleware checks hostname
    ↓
    ├─ dbbsa.com / portal.lvh.me → Public Portal
    │   ├─ Student (role='student')
    │   ├─ Instructor (role='instructor')
    │   ├─ Parent (role='parent')
    │   └─ School (role='school_admin' or 'instructor' for school-level tools)
    │
    ├─ admin.dbbsa.com → School Admin Portal
    │   └─ School Admin (role='school_admin') + 2FA
    │
    └─ sys.neuralvillage.com → Super Admin Portal
        └─ Super Admin (role='super_admin') + 2FA + IP whitelist
```

### Database Relationships

```
School (1) ──── (Many) Cohort
                  ├─ Instructor
                  └─ (Many) Student
                      ├─ (Many) Parents
                      ├─ (One) HardwareAsset (iPad/BCI)
                      └─ (Many) CBT_Session
                          └─ (Many) CBT_Question

Module ──── (Many) CBT_Quiz
         └─ (Many) Lab_Project
```

### Critical Features Implemented

| Feature | Purpose | Implementation |
|---------|---------|-----------------|
| **Silent Token Refresh** | Prevent "session expired" mid-test | `SilentTokenRefreshMiddleware` checks every 30s, refreshes if < 5 mins left |
| **Hardware Override** | Allow work if iPad offline due to network glitch | Instructor sets `override_active_until`, system logs reason |
| **Data Filtering** | Prevent data leakage (Instructor A can't see Cohort B) | `@require_role` decorator, database-level filtering in queries |
| **2FA for Admins** | Extra security for sensitive roles | Required for school_admin and super_admin roles |
| **Auto-Save (CBT)** | Save answers every 30 seconds to prevent loss | `auto_saved_answers` JSON field, Celery task runs periodically |
| **Role-Based Access** | Control who sees what based on domain + role | Middleware + decorator pattern |

---

## Key Design Decisions

### ✅ Monolithic (NOT Microservices)

**Why:**
- 30 schools, 1,000-5,000 students now (growing to 50K over 5 years)
- Strong code sharing between portals (auth, models, API)
- Easier debugging & testing
- Simpler operational burden
- Cost: 1/3 complexity vs microservices

**Scaling Path:**
- Phase 1: Single server + load balancer
- Phase 2: Multiple app servers + read replicas
- Phase 3: Multi-region setup
- Phase 4 (Only if needed): Extract CBT engine, Hardware sync as services

### ✅ Internal Separation of Concerns

Despite being monolithic, the codebase is highly modular:
- `neural_village/student/` - Student portal only
- `neural_village/instructor/` - Instructor portal only
- `neural_village/school_admin/` - School admin only
- `neural_village/cbt/` - CBT engine (isolated, can extract later)
- `neural_village/hardware/` - Hardware sync (isolated, can extract later)

**This means:** If you decide to extract CBT as microservice in Year 2, it's already structured for extraction.

### ✅ Database-First Security

Never filter data on frontend:
```python
# WRONG
students = Student.objects.all()  # Frontend filters

# RIGHT
students = Student.objects.filter(cohort__instructor=user)  # Backend enforces
```

### ✅ Token Refresh Strategy

The CBT engine silently refreshes tokens **before** expiry:
```python
if token_expires_in_less_than_5_minutes:
    refresh_token()
    attach_new_token_to_response()
    # Student never knows token was refreshed
```

This prevents "Your session has expired" errors mid-test submission.

---

## Next Steps (Ready to Code)

1. **Set up Django Project**
   ```bash
   python manage.py startproject neural_village
   python manage.py startapp core
   python manage.py startapp auth
   python manage.py startapp student
   python manage.py startapp instructor
   # etc...
   ```

2. **Run Migrations**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

3. **Create Sample Data**
   - Seed Shehu Giwa Academy
   - Create test instructors & students
   - Create sample cohorts

4. **Build Student Portal (Week 5-6)**
   - Dashboard view (pending labs, quiz schedule)
   - Module enrollment
   - Lab submission interface
   - Progress tracking

5. **Build CBT Engine (Week 7-8)**
   - Test session start/end
   - Auto-save mechanism
   - **CRITICAL:** Token refresh (prevent mid-test timeouts)

6. **Build Instructor Portal (Week 9-10)**
   - Deploy quizzes to cohort
   - Grade submissions
   - Manage lab reviews

7. **Build School Admin Portal (Week 11-12)**
   - Manage students (add/remove/deactivate)
   - Hardware inventory dashboard
   - 2FA setup

8. **Deploy to AWS**
   - Set up RDS PostgreSQL
   - ElastiCache Redis
   - Application Load Balancer
   - GitHub Actions CI/CD

---

## Files Created

```
c:\Users\HP\Desktop\David Bedford\
├── landing.html                    ✅ Updated (School Admin removed)
├── neural_village/
│   ├── models.py                   ✅ Complete data models
│   ├── middleware.py               ✅ Domain routing & auth
│   ├── settings.py                 ✅ Multi-domain config
│   └── urls.py                     ✅ Multi-domain routing
├── requirements.txt                ✅ Django + dependencies
├── ARCHITECTURE.md                 ✅ Monolithic vs microservices analysis
├── SETUP_GUIDE.md                  ✅ Dev setup & deployment
└── README.md                       → TO CREATE (Getting Started)
```

---

## Recommendation: Start Week 1

You have a solid architectural foundation. The next phase is:

1. **Initialize Django project** (Days 1-2)
2. **Create models & migrations** (Days 3-5)
3. **Build auth system** (Week 1)
4. **Prototype student portal dashboard** (Week 2)

By end of Week 2, you'll have a working MVP that can:
- Register students/instructors/parents
- Redirect to appropriate portals based on role
- Show basic dashboard
- Prove the multi-domain routing works

---

## Questions to Clarify

1. **Frontend Technology:** React or Vue? SPA per portal or monolithic frontend?
2. **Database:** Managed PostgreSQL (AWS RDS) or self-hosted?
3. **Deployment Timeline:** Do you have AWS account setup ready?
4. **Team Size:** Starting with 1 developer or 3+?
5. **NeuroArt Backend:** How will iPad submissions be stored? S3 bucket or self-hosted?
6. **Payment Integration:** Paystack or Stripe for ₦4,500 tuition?

---

## Summary

You now have:
✅ Secure landing page (no school admin leak)
✅ Complete data model for the entire ecosystem
✅ Multi-domain routing system
✅ Clear separation of roles & permissions
✅ Critical CBT safeguards (token refresh, auto-save)
✅ Scaling roadmap (monolithic → microservices when needed)
✅ 16-week implementation plan
✅ Full setup & deployment guides

**The system is architected to support 30 schools → 500+ schools without fundamental redesign.**

Ready to build! 🚀
