# Ideo Project Online Study

A Django web application for running the Ideomotor Effect online study with role-based session control for Researcher and Participant.

## Features

- **No user accounts required** - Join via codes (R-XX OVS/OVM or P-XX OVS/OVM)
- **6 experiment stages** aligned with the approved online procedure
- **Timed prediction-feedback task** with answer, confidence, reaction-time, and predetermined feedback capture
- **Real-time status polling** (5-second intervals)
- **CSV export** for data analysis
- **Admin interface** for data management

## Quick Start

```bash
# Activate your conda environment
conda activate coco

# Navigate to project directory
cd /root/test_oujia

# Run migrations (already done)
python manage.py migrate

# Load seed data (already done)
python manage.py loaddata questions trials

# Start the development server
python manage.py runserver 0.0.0.0:8000
```

## Join Codes

- **R-XX OVS/OVM** - Researcher (e.g., R-12 OVS)
- **P-XX OVS/OVM** - Participant (e.g., P-12 OVS)

The number plus condition (for example, `12-OVS`) defines the group. Same number and same condition = same experiment session.

## Experiment Stages

| Stage | Name | Participant | Researcher |
|-------|------|-------------|------------|
| 0 | Waiting | Wait | Control |
| 1 | Consent | Fill form | Control |
| 2 | Demographics Questionnaire | Answer | Monitor |
| 3 | Initial Question Set | Answer | Monitor |
| 4 | Prediction Feedback Task | Timed task | Monitor |
| 5 | Post-Study Questionnaire | Fill survey | Monitor |
| 6 | Personality Questionnaire | Follow researcher instruction | Monitor |
| 7 | Debrief | View (when unlocked) | Unlock |

## Admin Access

- URL: `/admin/`
- Username: `admin`
- Password: `admin123`

## API Endpoints

- `GET /api/session/<group_id>/status/` - Poll session status (used for auto-refresh)
- `GET /export/<group_id>.csv` - Download all session data as CSV (Researcher only)

## Project Structure

```
test_oujia/
├── experiment/
│   ├── models.py        # Database models
│   ├── views.py         # View functions
│   ├── urls.py          # URL routing
│   ├── admin.py         # Admin configuration
│   ├── fixtures/        # Seed data (questions, trials)
│   └── templatetags/    # Custom template filters
├── templates/
│   ├── base.html        # Base template
│   └── experiment/      # All experiment templates
├── oujia_lab/
│   ├── settings.py      # Django settings
│   └── urls.py          # Root URL config
└── manage.py
```

## Models

- **Session** - Experiment session with group_id, stage, settings
- **SessionMember** - User in a session with role and token
- **Question72** - 72 yes/no questions for stage 3
- **Response72** - Responses to Question72
- **Trial16** - 16 prediction-feedback task questions
- **PredictionResponse** - Timed task answers, confidence, reaction time, and feedback outcome
- **ConsentInfo** - Participant consent
- **DemographicInfo** - Demographic questionnaire responses
- **PostSurvey** - Post-study agency, system influence, belief, and comments
- **AuditLog** - Action logging for audit trail
