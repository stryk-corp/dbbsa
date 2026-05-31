# DBBSA Architecture: Monolithic-First Strategy

## Executive Summary

For the DBBSA ecosystem, **recommend a monolithic-first approach** with clear internal separation of concerns. This provides the right balance of scalability, maintainability, and operational simplicity for a growing EdTech platform.

> Note: `ARCHITECTURE_PRECISE.md` is the authoritative source of truth for portal routing, domain mapping, role-based UX, and deployment topology.

---

## Architecture Decision Matrix

### Monolithic-First (RECOMMENDED)

**When to Choose:**
- Starting with 30 schools, 600-900 students
- Most code sharing needed between portals
- Strong need for consistency across data models
- Development team 5-15 engineers

**Pros:**
✅ Simpler deployment & operations (one codebase)
✅ Easier database transactions (no distributed transaction complexity)
✅ Better code reuse between portals
✅ Easier debugging & monitoring
✅ Suitable for current scale (3 × 30 schools = 90 schools max in 5 years)

**Cons:**
❌ Single point of failure (but mitigated with load balancing & replicas)
❌ Harder to scale specific components independently
❌ Requires clear app separation to avoid spaghetti code

**Implementation Cost:** ~$50K initial dev + $5K/month ops
**Development Timeline:** 12-16 weeks for full MVP

---

### Full Microservices (NOT RECOMMENDED YET)

**When to Choose:**
- 500+ schools, 50K+ students
- Each microservice has different scaling needs
- Separate teams managing different services
- Need to deploy services independently

**Pros:**
✅ Scale components independently (CBT engine gets more resources)
✅ Different services can use different tech stacks
✅ Fault isolation (CBT crash doesn't take down student portal)
✅ Future-proof for massive scale

**Cons:**
❌ Massive operational complexity (Docker, Kubernetes, service mesh)
❌ Distributed transaction challenges
❌ API versioning & coordination overhead
❌ Difficult to debug issues spanning multiple services
❌ Requires DevOps expertise

**Implementation Cost:** ~$150K initial + $20K/month ops
**Development Timeline:** 20-24 weeks for equivalent features

---

## Recommended: Monolithic with Strategic Separation

### Core Principle: "One Codebase, Multiple Apps"

```
neural_village/
├── core/                    # Shared models, middleware, utilities
│   ├── models.py           # School, Student, Parent, Instructor, Cohort, CBT_Session, etc.
│   ├── middleware.py       # Domain routing, role-based access, token refresh
│   ├── utils/              # Shared helpers
│   └── constants.py        # App-wide enums
│
├── auth/                   # Authentication (all roles)
│   ├── views.py           # Login, logout, 2FA for admins
│   ├── serializers.py     # User & Profile serialization
│   └── urls.py            # Auth endpoints
│
├── student/               # Student portal (portal.student/ or portal.lvh.me/portal/student)
│   ├── views.py          # Dashboard, labs, modules
│   ├── serializers.py    # Student-specific data
│   └── urls.py
│
├── instructor/            # Instructor portal (portal.lvh.me/portal/instructor)
│   ├── views.py          # Grade submissions, deploy quizzes
│   ├── serializers.py    # Cohort, grading data
│   └── urls.py
│
├── parent/                # Parent portal (portal.lvh.me/portal/parent)
│   ├── views.py          # View child progress, payments
│   └── urls.py
│
├── school_admin/          # School admin portal (admin.dbbsa.com)
│   ├── views.py          # Manage students, staff, hardware
│   ├── middleware.py     # School-specific auth (2FA required)
│   └── urls.py
│
├── super_admin/           # Super admin portal (sys.neuralvillage.com)
│   ├── views.py          # Manage schools, global settings, analytics
│   ├── middleware.py     # Extra security (IP whitelist, 2FA)
│   └── urls.py
│
├── cbt/                   # Computer-Based Testing Engine (isolated)
│   ├── views.py          # Test sessions, auto-save, token refresh
│   ├── tasks.py          # Async background tasks (Celery)
│   ├── models.py         # CBT_Session, CBT_Question, CBT_Quiz
│   └── urls.py
│
├── hardware/              # Hardware sync & management
│   ├── views.py          # iPad/OpenBCI sync endpoints
│   ├── tasks.py          # Background sync, status checks
│   └── urls.py
│
├── api/                   # REST API layer
│   ├── public_urls.py    # Public APIs
│   ├── school_admin_urls.py
│   ├── super_admin_urls.py
│   └── permissions.py     # Custom DRF permissions
│
├── settings.py            # Django settings (multi-domain)
├── urls.py               # Multi-domain routing
├── middleware.py         # Domain routing, role enforcement
└── wsgi.py              # WSGI entry point
```

---

## Critical Design Patterns

### 1. Domain-Based Routing (via Middleware)

```python
# Request comes in
request → DomainRoutingMiddleware
  ↓
If host == 'admin.dbbsa.com':
  → Requires role='school_admin' + 2FA
  → Routes to school_admin app
  
Else if host == 'sys.neuralvillage.com':
  → Requires role='super_admin' + 2FA + IP whitelist
  → Routes to super_admin app
  
Else (dbbsa.com):
  → Allows roles=['student', 'parent', 'instructor']
  → Routes to public portals
```

### 2. CBT Engine Isolation (Prevents Mid-Test Failures)

```python
class SilentTokenRefreshMiddleware:
    """
    Every request during CBT checks:
    - Is token expiring soon?
    - If yes → Silently refresh in background
    - Return new token in response headers
    - Student never knows token was refreshed
    """
```

**Key Feature:** Token refreshes BEFORE expiry, not after. Prevents "Your session expired" mid-submission.

### 3. Hardware Override for Instructors

```python
class HardwareAsset:
    # If iPad marked offline, student blocked from NeuroArt
    # BUT: Instructor can set override_active_until = now + 2 hours
    # Student can work around network glitch
    
    is_online: bool
    instructor_override_reason: str  # Audit trail
    override_active_until: datetime
```

### 4. Data Filtering at Database Level (Security)

```python
# BAD (Frontend-side filtering):
def get_students(request):
    all_students = Student.objects.all()
    # Frontend filters to show only cohort_a
    return Response(all_students)  # Data leak!

# GOOD (Database-level filtering):
def get_students(request):
    instructor = request.user.instructor_profile
    cohorts_taught = instructor.cohorts_taught.values_list('id')
    students = Student.objects.filter(cohort_id__in=cohorts_taught)
    return Response(StudentSerializer(students, many=True).data)
```

---

## Scaling Path

### Phase 1 (Months 1-6): MVP Monolithic
- Single Django server (t3.large on AWS)
- PostgreSQL database (t3.medium, RDS)
- Redis for caching & Celery (ElastiCache)
- Supports 30 schools, 1,000 students
- **Cost:** ~$800/month

### Phase 2 (Months 6-12): High Availability
- Load balancer (ALB)
- 2-3 Django application servers
- PostgreSQL with read replicas
- Separate Redis for Celery workers
- Supports 100 schools, 5,000 students
- **Cost:** ~$2,500/month

### Phase 3 (Months 12-24): Multi-Region
- API Gateway for domain routing
- Regional load balancers
- Cross-region database replication
- Supports 500+ schools, 50,000+ students
- **Cost:** ~$8,000/month

### Phase 4 (Year 2+): Strategic Microservices
**ONLY if:**
- CBT engine needs to scale 10x independently
- Hardware sync needs separate deployment
- Analytics requires separate processing

**Extract services incrementally:**
1. CBT Engine → Separate service (async job processor)
2. Hardware Sync → IoT/Webhook processor
3. Analytics → Data pipeline (Python + Kafka)

---

## Implementation Checklist (16-Week Timeline)

### Week 1-2: Foundation
- [ ] Django project scaffolding
- [ ] Models (School, Student, Parent, Instructor, Cohort, CBT_Session)
- [ ] Database migrations
- [ ] Settings for multi-domain

### Week 3-4: Authentication & Authorization
- [ ] User roles & permissions
- [ ] Domain routing middleware
- [ ] Role-based access decorators
- [ ] Landing page redirect logic

### Week 5-6: Student Portal MVP
- [ ] Dashboard (labs, modules, scores)
- [ ] Module enrollment
- [ ] Lab submission flow

### Week 7-8: CBT Engine
- [ ] Quiz creation & question management
- [ ] Test session start/end
- [ ] Auto-save every 30 seconds
- [ ] **CRITICAL:** Silent token refresh (5 mins before expiry)

### Week 9-10: Instructor Portal
- [ ] Cohort management
- [ ] Quiz deployment
- [ ] Grading interface
- [ ] Lab review

### Week 11-12: School Admin Portal
- [ ] Student management (add/remove/deactivate)
- [ ] Staff management
- [ ] Hardware inventory dashboard
- [ ] 2FA enforcement

### Week 13-14: Parent Portal
- [ ] Child progress view
- [ ] Payment collection
- [ ] Notification preferences

### Week 15-16: Super Admin & Polish
- [ ] Super admin dashboard (manage schools)
- [ ] Analytics & reporting
- [ ] Testing & bug fixes
- [ ] Deployment & documentation

---

## Tech Stack Recommendation

### Backend
- **Framework:** Django 4.2 LTS
- **Database:** PostgreSQL 14+
- **Cache:** Redis 7+ (via Django)
- **Task Queue:** Celery with Redis broker
- **API:** Django REST Framework + Token Auth (JWT)

### Frontend
- **Framework:** React 18 or Vue 3 (SPA per portal)
- **CSS:** Tailwind (already in landing page)
- **State Management:** Redux/Pinia for complex state

### Infrastructure
- **Hosting:** AWS (scalable, good for Nigeria latency)
- **Containers:** Docker + Docker Compose (local dev)
- **CI/CD:** GitHub Actions
- **Monitoring:** DataDog or New Relic

---

## Budget Estimate (16-Week Dev)

| Item | Cost |
|------|------|
| Lead Developer (16 wks @ $100/hr) | $64,000 |
| 2x Backend Engineers (16 wks @ $60/hr) | $76,800 |
| QA/Testing (16 wks @ $40/hr) | $25,600 |
| DevOps/Infra setup | $8,000 |
| **Total Development** | **$174,400** |
| AWS hosting (3 months) | $2,400 |
| Tools & Licenses | $1,200 |
| **Total MVP** | **~$178,000** |

**Team:** 4 engineers (1 lead + 2 backend + 1 QA)

---

## Why Monolithic First Wins

1. **Consistency:** All users share same data models (no versioning headaches)
2. **Transactions:** School admin can deactivate all students in 1 query
3. **Development Speed:** Share auth, utils, logging across apps
4. **Cost:** 1/3 the complexity, 1/2 the operational burden
5. **Maintainability:** Easier for Japhet's team to understand & iterate

**The monolithic approach doesn't lock you into monolithic forever.** You can extract services later when you hit actual scaling constraints, not theoretical ones.

---

## Next Steps

1. **Approval:** Confirm monolithic + multi-domain routing approach
2. **Database Setup:** PostgreSQL migration planning (school relationships, data seeding)
3. **Team Onboarding:** Set up Django project, database schema, dev environment
4. **User Flows:** Detailed wireframes per portal (Student, Instructor, School Admin)
5. **API Spec:** OpenAPI/Swagger for all endpoints

Would you like me to create:
- Database migration scripts?
- API endpoint specification (OpenAPI)?
- Detailed user flows for each portal?
