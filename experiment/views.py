import re
import csv
import json
from functools import wraps
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse, HttpResponseForbidden, HttpResponseNotFound
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.utils import timezone
from django.templatetags.static import static

from .models import (
    Session, SessionMember, Question72, Response72, 
    Trial16, VerbalResult, PredictionResponse, ConsentInfo, DemographicInfo,
    PostSurvey, PersonalitySurvey, AuditLog, OuijaTrace
)


PERSONALITY_ITEMS = [
    "I tend to leave my belongings around",
    "I don't like to draw attention to myself",
    "I like to start conversations with people",
    "I get overwhelmed by emotions",
    "I take time out for others",
    "I make plans and stick to them",
    "I am not easily bothered by things",
    "I will not probe deeply into a subject",
    "I am not interested in other people's problems",
    "I love to think up new ways of doing something",
    "I am always prepared",
    "I have difficulty understanding abstract ideas",
    "I pay attention to details",
    "I get chores done right away",
    "I am quiet around strangers",
    "I have a vivid imagination",
    "I am quick to understand things",
    "I follow a schedule",
    "I often neglect my duties",
    "I feel others emotions",
    "I like order",
    "I worry about things",
]

PERSONALITY_CHOICES = [
    ("strongly_disagree", "Strongly Disagree"),
    ("disagree", "Disagree"),
    ("agree", "Agree"),
    ("strongly_agree", "Strongly Agree"),
]


def get_member_from_request(request, allowed_roles=None):
    """Retrieve a SessionMember from role-specific cookies."""
    roles_to_check = list(allowed_roles or ['R', 'P'])
    tokens = []

    for role in roles_to_check:
        token = request.COOKIES.get(f'session_token_{role}')
        if token:
            tokens.append(token)

    legacy_token = request.COOKIES.get('session_token')
    if legacy_token:
        tokens.append(legacy_token)

    for token in tokens:
        try:
            member = SessionMember.objects.select_related('session').get(session_token=token)
        except SessionMember.DoesNotExist:
            continue

        if member.role not in {'R', 'P'}:
            continue
        if allowed_roles and member.role not in allowed_roles:
            continue
        return member

    return None


def require_member(view_func):
    """Decorator requiring valid session member."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        member = get_member_from_request(request)
        if not member:
            return redirect('experiment:join')
        request.member = member
        request.session_obj = member.session
        return view_func(request, *args, **kwargs)
    return wrapper


def require_role(*roles):
    """Decorator requiring specific role(s)."""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            member = get_member_from_request(request, roles)
            if not member:
                return redirect('experiment:join')
            if member.role not in roles:
                return HttpResponseForbidden("Access denied for your role.")
            request.member = member
            request.session_obj = member.session
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def require_stage(min_stage, max_stage=None):
    """Decorator requiring session to be at specific stage."""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            member = getattr(request, 'member', None) or get_member_from_request(request)
            if not member:
                return redirect('experiment:join')
            session = member.session
            max_s = max_stage if max_stage is not None else min_stage
            if session.stage < min_stage or session.stage > max_s:
                messages.warning(request, f"This page is not available at the current stage.")
                return redirect_to_dashboard(member)
            request.member = member
            request.session_obj = session
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def redirect_to_dashboard(member):
    """Redirect to appropriate dashboard based on role."""
    if member.role == 'R':
        return redirect('experiment:researcher_dashboard')
    if member.role == 'P':
        return redirect('experiment:participant_dashboard')
    return redirect('experiment:join')


def home(request):
    """Home page with join form."""
    member = get_member_from_request(request)
    if member:
        return redirect_to_dashboard(member)
    return render(request, 'experiment/home.html')


def join(request):
    """Handle join code submission."""
    if request.method == 'GET':
        return render(request, 'experiment/join.html')
    
    code = request.POST.get('code', '').strip().upper()
    
    pattern = r'^([RP])\s*-\s*(\d{2})\s+(OVS|OVM)$'
    match = re.match(pattern, code)
    
    if not match:
        messages.error(request, "Invalid code format. Use R-XX OVS/OVM or P-XX OVS/OVM")
        return render(request, 'experiment/join.html')
    
    role = match.group(1)
    group_number = match.group(2)
    condition = match.group(3)
    group_id = f"{group_number}-{condition}"
    
    session, created = Session.objects.get_or_create(group_id=group_id)
    
    member, member_created = SessionMember.objects.get_or_create(
        session=session,
        role=role,
        defaults={'session_token': SessionMember.generate_token()}
    )
    
    if not member_created:
        member.session_token = SessionMember.generate_token()
        member.save()
    
    AuditLog.objects.create(
        session=session,
        action='JOIN',
        actor_role=role,
        details={'group_id': group_id, 'new_session': created}
    )
    
    response = redirect_to_dashboard(member)
    response.set_cookie(
        f'session_token_{role}',
        member.session_token,
        max_age=60*60*24*7,
        httponly=True,
        samesite='Lax'
    )
    response.set_cookie(
        'last_role',
        role,
        max_age=60*60*24*7,
        httponly=True,
        samesite='Lax'
    )
    return response


@require_role('R')
def researcher_dashboard(request):
    """Researcher control dashboard."""
    session = request.session_obj
    members = session.members.all()
    
    response72_count = Response72.objects.filter(session=session).count()
    demographics_count = DemographicInfo.objects.filter(session=session).count()
    prediction_count = PredictionResponse.objects.filter(session=session).count()
    
    context = {
        'session': session,
        'members': members,
        'response72_count': response72_count,
        'demographics_count': demographics_count,
        'prediction_count': prediction_count,
        'initial_verbal_play_nonce': session.verbal_play_nonce,
        'stage_choices': Session.STAGE_CHOICES,
    }
    return render(request, 'experiment/researcher_dashboard.html', context)


@require_role('P')
def participant_dashboard(request):
    """Participant dashboard."""
    session = request.session_obj
    member = request.member
    
    has_consent = ConsentInfo.objects.filter(session=session).exists()
    has_demographics = DemographicInfo.objects.filter(session=session).exists()
    has_completed_72 = Response72.objects.filter(
        session=session, member=member
    ).count() == 72
    has_post_survey = PostSurvey.objects.filter(session=session).exists()
    has_personality_survey = PersonalitySurvey.objects.filter(session=session).exists()
    has_prediction_task = PredictionResponse.objects.filter(
        session=session, member=member
    ).count() == 16

    if session.stage == 1 and not has_consent:
        return redirect('experiment:consent')

    if session.stage == 2 and not has_demographics:
        return redirect('experiment:demographics')

    if session.stage == 3 and not has_completed_72:
        return redirect('experiment:questions72')

    if session.stage == 6 and not has_personality_survey:
        return redirect('experiment:personality')
    
    context = {
        'session': session,
        'member': member,
        'has_consent': has_consent,
        'has_demographics': has_demographics,
        'has_completed_72': has_completed_72,
        'has_post_survey': has_post_survey,
        'has_personality_survey': has_personality_survey,
        'has_prediction_task': has_prediction_task,
        'initial_verbal_play_nonce': session.verbal_play_nonce,
    }
    return render(request, 'experiment/participant_dashboard.html', context)


@require_role('P')
@require_stage(1)
def consent_page(request):
    """Consent and basic info form."""
    session = request.session_obj
    member = request.member
    
    if ConsentInfo.objects.filter(session=session).exists():
        messages.info(request, "Consent already submitted.")
        return redirect('experiment:participant_dashboard')
    
    if request.method == 'POST':
        consent = request.POST.get('consent') == 'yes'
        
        if not consent:
            messages.error(request, "You must consent to participate.")
            return render(request, 'experiment/consent.html', {'session': session})
        
        ConsentInfo.objects.create(
            session=session,
            member=member,
            consent_given=consent,
        )
        
        AuditLog.objects.create(
            session=session,
            action='RESPONSE',
            actor_role='P',
            details={'type': 'consent'}
        )
        
        messages.success(request, "Consent recorded. Please wait for the next stage.")
        return redirect('experiment:participant_dashboard')
    
    return render(request, 'experiment/consent.html', {'session': session})


@require_role('P')
@require_stage(2)
def demographics_page(request):
    """Demographics questionnaire."""
    session = request.session_obj
    member = request.member

    if DemographicInfo.objects.filter(session=session).exists():
        messages.info(request, "Demographics already submitted.")
        return redirect('experiment:participant_dashboard')

    if request.method == 'POST':
        hsp_id = request.POST.get('hsp_id', '').strip()
        heard_ouija = request.POST.get('heard_ouija', '')
        played_ouija = request.POST.get('played_ouija', '')
        planchette_explanation = request.POST.get('planchette_explanation', '').strip()
        birth_city_country = request.POST.get('birth_city_country', '').strip()
        mother_birth_city_country = request.POST.get('mother_birth_city_country', '').strip()
        father_birth_city_country = request.POST.get('father_birth_city_country', '').strip()
        primary_language = request.POST.get('primary_language', '').strip()
        other_languages = request.POST.get('other_languages', '').strip()
        countries_over_one_month = request.POST.get('countries_over_one_month', '').strip()
        high_school_location = request.POST.get('high_school_location', '').strip()
        attended_international_school = request.POST.get('attended_international_school', '')
        on_exchange = request.POST.get('on_exchange', '')
        cultural_classification = request.POST.get('cultural_classification', '')

        def parse_percent(field_name):
            try:
                return max(0, min(100, int(request.POST.get(field_name, 0))))
            except (TypeError, ValueError):
                return 0

        DemographicInfo.objects.create(
            session=session,
            member=member,
            hsp_id=hsp_id,
            heard_ouija=heard_ouija,
            played_ouija=played_ouija,
            planchette_explanation=planchette_explanation,
            percent_life_in_north_america=parse_percent('percent_life_in_north_america'),
            percent_life_outside_north_america=parse_percent('percent_life_outside_north_america'),
            birth_city_country=birth_city_country,
            mother_birth_city_country=mother_birth_city_country,
            father_birth_city_country=father_birth_city_country,
            primary_language=primary_language,
            other_languages=other_languages,
            countries_over_one_month=countries_over_one_month,
            high_school_location=high_school_location,
            attended_international_school=attended_international_school,
            on_exchange=on_exchange,
            cultural_classification=cultural_classification
        )

        AuditLog.objects.create(
            session=session,
            action='RESPONSE',
            actor_role='P',
            details={'type': 'demographics'}
        )

        messages.success(request, "Demographics submitted. Please wait for the next stage.")
        return redirect('experiment:participant_dashboard')

    return render(request, 'experiment/demographics.html', {'session': session})


@require_role('P')
@require_stage(3)
def questions72_page(request):
    """72 yes/no questions page."""
    session = request.session_obj
    member = request.member
    
    existing_responses = {
        r.question_id: r for r in Response72.objects.filter(session=session, member=member)
    }
    
    if len(existing_responses) == 72:
        messages.info(request, "You have already completed all 72 questions.")
        return redirect_to_dashboard(member)
    
    questions = Question72.objects.all()
    
    if request.method == 'POST':
        for q in questions:
            answer = request.POST.get(f'answer_{q.number}')
            confidence = request.POST.get(f'confidence_{q.number}')
            
            if answer and confidence:
                Response72.objects.update_or_create(
                    session=session,
                    member=member,
                    question=q,
                    defaults={'answer': answer, 'confidence': confidence}
                )
        
        AuditLog.objects.create(
            session=session,
            action='RESPONSE',
            actor_role=member.role,
            details={'type': 'questions72', 'count': 72}
        )
        
        messages.success(request, "All responses saved!")
        return redirect_to_dashboard(member)
    
    context = {
        'session': session,
        'questions': questions,
        'existing_responses': existing_responses,
    }
    return render(request, 'experiment/questions72.html', context)


@require_role('P')
@require_stage(4)
def ouija_page(request):
    """Timed deceptive prediction-feedback task."""
    session = request.session_obj
    member = request.member

    trials = Trial16.objects.all()
    existing_responses = {
        response.trial_id: response
        for response in PredictionResponse.objects.filter(session=session, member=member)
    }

    if len(existing_responses) == 16:
        messages.info(request, "You have already completed the prediction-feedback task.")
        return redirect_to_dashboard(member)

    if request.method == 'POST':
        saved = 0
        for trial in trials:
            answer = request.POST.get(f'answer_{trial.number}')
            confidence = request.POST.get(f'confidence_{trial.number}')
            rt = request.POST.get(f'rt_{trial.number}')
            predicted = request.POST.get(f'predicted_{trial.number}')
            matched = request.POST.get(f'matched_{trial.number}') == '1'

            if not all([answer, confidence, rt, predicted]):
                continue

            try:
                reaction_time_ms = max(0, int(float(rt)))
            except (TypeError, ValueError):
                continue

            if answer not in {'Y', 'N'} or predicted not in {'Y', 'N'} or confidence not in {'G', 'S'}:
                continue

            PredictionResponse.objects.update_or_create(
                session=session,
                member=member,
                trial=trial,
                defaults={
                    'answer': answer,
                    'confidence': confidence,
                    'reaction_time_ms': reaction_time_ms,
                    'predicted_answer': predicted,
                    'matched': matched,
                }
            )
            saved += 1

        AuditLog.objects.create(
            session=session,
            action='RESPONSE',
            actor_role=member.role,
            details={'type': 'prediction_task', 'count': saved}
        )

        messages.success(request, "Prediction-feedback task saved. Please wait for the next stage.")
        return redirect_to_dashboard(member)

    context = {
        'session': session,
        'member': member,
        'trials': trials,
        'trials_json': json.dumps([
            {'number': trial.number, 'text': trial.text}
            for trial in trials
        ]),
    }
    return render(request, 'experiment/prediction_task.html', context)


@require_GET
@require_role('P', 'R')
@require_stage(4)
def ouija_state_api(request):
    """Return shared planchette state for the current session."""
    session = request.session_obj
    return JsonResponse({
        'x': session.ouija_x,
        'y': session.ouija_y,
        'last_actor': session.ouija_last_actor,
        'question_number': session.ouija_round,
        'updated_at': session.ouija_updated_at.isoformat() if session.ouija_updated_at else None,
    })


@require_POST
@require_role('P')
@require_stage(4)
def ouija_update_api(request):
    """Update shared planchette position and persist trace points."""
    session = request.session_obj
    member = request.member

    try:
        payload = json.loads(request.body.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({'success': False, 'error': 'Invalid JSON payload'}, status=400)

    def clamp(value):
        return max(0.0, min(1.0, float(value)))

    try:
        x = clamp(payload.get('x', session.ouija_x))
        y = clamp(payload.get('y', session.ouija_y))
    except (TypeError, ValueError):
        return JsonResponse({'success': False, 'error': 'Invalid coordinates'}, status=400)

    session.ouija_x = x
    session.ouija_y = y
    session.ouija_last_actor = member.role
    session.ouija_updated_at = timezone.now()
    session.save(update_fields=['ouija_x', 'ouija_y', 'ouija_last_actor', 'ouija_updated_at', 'updated_at'])

    trace_points = payload.get('trace', [])
    if isinstance(trace_points, list) and trace_points:
        traces_to_create = []
        for point in trace_points[:200]:
            if not isinstance(point, dict):
                continue
            try:
                px = clamp(point.get('x'))
                py = clamp(point.get('y'))
            except (TypeError, ValueError):
                continue
            traces_to_create.append(
                OuijaTrace(
                    session=session,
                    member=member,
                    question_number=session.ouija_round,
                    x=px,
                    y=py,
                )
            )

        if traces_to_create:
            OuijaTrace.objects.bulk_create(traces_to_create, batch_size=200)

    return JsonResponse({'success': True})


@require_GET
@require_role('R')
def ouija_trace_api(request):
    """Return Ouija trace points for researcher monitoring."""
    session = request.session_obj

    try:
        after_id = int(request.GET.get('after_id', '0'))
    except ValueError:
        after_id = 0

    traces = (
        OuijaTrace.objects
        .filter(session=session, id__gt=after_id)
        .select_related('member')
        .order_by('id')[:1000]
    )

    points = [
        {
            'id': t.id,
            'x': t.x,
            'y': t.y,
            'role': t.member.role,
            'question_number': t.question_number,
            'recorded_at': t.recorded_at.isoformat(),
        }
        for t in traces
    ]
    return JsonResponse({'points': points})


@require_GET
@require_role('R')
def ouija_trace_image_svg(request, question_number):
    """Render researcher-only SVG image for a question's Ouija trace."""
    session = request.session_obj
    traces = list(
        OuijaTrace.objects.filter(session=session, question_number=question_number)
        .select_related('member')
        .order_by('id')
    )
    if not traces:
        return HttpResponseNotFound("No trace points found for this question.")

    width = 1200
    height = 675
    points = [(max(0.0, min(1.0, t.x)) * width, max(0.0, min(1.0, t.y)) * height, t.member.role) for t in traces]

    def role_color(role):
        if role == 'P':
            return '#15803d'
        return '#1d4ed8'

    line_elems = []
    for i in range(1, len(points)):
        x1, y1, _ = points[i - 1]
        x2, y2, role = points[i]
        line_elems.append(
            f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
            f'stroke="{role_color(role)}" stroke-opacity="0.62" stroke-width="2.8" />'
        )

    x_last, y_last, _ = points[-1]
    yes_left = session.yes_side == 'L'
    yes_text = 'YES' if yes_left else 'NO'
    no_text = 'NO' if yes_left else 'YES'

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <defs>
    <radialGradient id="wood" cx="50%" cy="50%" r="65%">
      <stop offset="0%" stop-color="#f3d8a1"/>
      <stop offset="48%" stop-color="#c99f67"/>
      <stop offset="100%" stop-color="#8a5a3a"/>
    </radialGradient>
  </defs>
  <rect x="0" y="0" width="{width}" height="{height}" rx="24" fill="url(#wood)"/>
  <text x="40" y="52" font-family="Space Grotesk, Arial, sans-serif" font-size="34" font-weight="700" fill="#3a2514">{yes_text}</text>
  <text x="{width - 120}" y="52" font-family="Space Grotesk, Arial, sans-serif" font-size="34" font-weight="700" fill="#3a2514">{no_text}</text>
  <text x="{width/2:.0f}" y="{height/2:.0f}" text-anchor="middle" font-family="Space Grotesk, Arial, sans-serif" font-size="56" font-weight="700" fill="#3a2514" opacity="0.35">SPIRIT BOARD</text>
  {''.join(line_elems)}
  <circle cx="{x_last:.2f}" cy="{y_last:.2f}" r="11" fill="#111827" fill-opacity="0.88"/>
  <text x="30" y="{height - 40}" font-family="Arial, sans-serif" font-size="24" fill="#111827">Session {session.group_id} | question {question_number} | points {len(points)}</text>
  <text x="30" y="{height - 12}" font-family="Arial, sans-serif" font-size="18" fill="#111827">Green = Participant</text>
</svg>"""

    response = HttpResponse(svg, content_type='image/svg+xml')
    response['Content-Disposition'] = (
        f'inline; filename="session_{session.group_id}_question_{question_number}_trace.svg"'
    )
    return response


@require_POST
@require_role('R')
@require_stage(4)
def ouija_refresh_api(request):
    """Reset planchette to center and advance Ouija question round."""
    session = request.session_obj
    keep_data = True

    try:
        if request.body:
            payload = json.loads(request.body.decode('utf-8'))
            keep_data = bool(payload.get('keep_data', True))
    except (json.JSONDecodeError, UnicodeDecodeError):
        keep_data = True

    discarded_count = 0
    if not keep_data:
        discarded_count, _ = OuijaTrace.objects.filter(
            session=session,
            question_number=session.ouija_round
        ).delete()

    session.ouija_x = 0.5
    session.ouija_y = 0.5
    session.ouija_last_actor = 'R'
    session.ouija_round += 1
    session.ouija_updated_at = timezone.now()
    session.save(update_fields=[
        'ouija_x', 'ouija_y', 'ouija_last_actor',
        'ouija_round', 'ouija_updated_at', 'updated_at'
    ])

    AuditLog.objects.create(
        session=session,
        action='STAGE_CHANGE',
        actor_role='R',
        details={
            'type': 'ouija_refresh',
            'keep_data': keep_data,
            'discarded_count': discarded_count,
            'new_question_number': session.ouija_round,
        }
    )

    last_trace = OuijaTrace.objects.filter(session=session).order_by('-id').values_list('id', flat=True).first() or 0

    return JsonResponse({
        'success': True,
        'keep_data': keep_data,
        'discarded_count': discarded_count,
        'question_number': session.ouija_round,
        'x': session.ouija_x,
        'y': session.ouija_y,
        'last_trace_id': last_trace,
    })


@require_role('P')
@require_stage(5)
def post_survey_page(request):
    """Post-study questionnaire."""
    session = request.session_obj
    member = request.member
    
    if PostSurvey.objects.filter(session=session).exists():
        messages.info(request, "Survey already completed.")
        return redirect('experiment:participant_dashboard')
    
    if request.method == 'POST':
        yes_side_assigned = request.POST.get('yes_side_assigned', '')
        no_side_assigned = request.POST.get('no_side_assigned', '')
        completed_study = request.POST.get('completed_study', '')
        
        PostSurvey.objects.create(
            session=session,
            member=member,
            yes_side_assigned=yes_side_assigned,
            no_side_assigned=no_side_assigned,
            completed_study=completed_study
        )
        
        AuditLog.objects.create(
            session=session,
            action='RESPONSE',
            actor_role='P',
            details={'type': 'post_survey'}
        )
        
        messages.success(request, "Survey submitted!")
        return redirect('experiment:participant_dashboard')
    
    return render(request, 'experiment/post_survey.html', {'session': session})


@require_role('R')
@require_stage(6)
def verbal_page(request):
    """Stage 6 is reserved for the optional personality questionnaire."""
    messages.info(request, "Stage 6 is reserved for the optional personality questionnaire.")
    return redirect('experiment:researcher_dashboard')


@require_role('P')
@require_stage(6)
def personality_page(request):
    """Personality questionnaire."""
    session = request.session_obj
    member = request.member

    if PersonalitySurvey.objects.filter(session=session).exists():
        messages.info(request, "Personality questionnaire already completed.")
        return redirect('experiment:participant_dashboard')

    items = [
        {'number': index + 1, 'text': text}
        for index, text in enumerate(PERSONALITY_ITEMS)
    ]

    if request.method == 'POST':
        responses = {}
        valid_values = {value for value, _ in PERSONALITY_CHOICES}

        for item in items:
            field_name = f"personality_{item['number']}"
            value = request.POST.get(field_name, '')
            if value not in valid_values:
                messages.error(request, "Please answer every personality statement.")
                return render(request, 'experiment/personality.html', {
                    'session': session,
                    'items': items,
                    'choices': PERSONALITY_CHOICES,
                })
            responses[str(item['number'])] = {
                'statement': item['text'],
                'response': value,
            }

        PersonalitySurvey.objects.create(
            session=session,
            member=member,
            responses=responses
        )

        AuditLog.objects.create(
            session=session,
            action='RESPONSE',
            actor_role='P',
            details={'type': 'personality_survey', 'count': len(responses)}
        )

        messages.success(request, "Personality questionnaire submitted.")
        return redirect('experiment:participant_dashboard')

    return render(request, 'experiment/personality.html', {
        'session': session,
        'items': items,
        'choices': PERSONALITY_CHOICES,
    })


@require_role('P')
@require_stage(7)
def debrief_page(request):
    """Debrief page for participant."""
    session = request.session_obj
    
    if not session.debrief_unlocked:
        messages.warning(request, "Debrief is not yet available.")
        return redirect('experiment:participant_dashboard')
    
    return render(request, 'experiment/debrief.html', {'session': session})


@require_POST
@require_role('R')
def advance_stage(request):
    """Researcher advances the session stage."""
    session = request.session_obj
    new_stage = request.POST.get('stage')
    
    try:
        new_stage = int(new_stage)
        if 0 <= new_stage <= 7:
            old_stage = session.stage
            session.stage = new_stage
            session.save()
            
            AuditLog.objects.create(
                session=session,
                action='STAGE_CHANGE',
                actor_role='R',
                details={'old_stage': old_stage, 'new_stage': new_stage}
            )
            
            messages.success(request, f"Stage changed to {session.get_stage_display_name()}")
        else:
            messages.error(request, "Invalid stage number.")
    except (ValueError, TypeError):
        messages.error(request, "Invalid stage value.")
    
    return redirect('experiment:researcher_dashboard')


@require_POST
@require_role('R')
def unlock_debrief(request):
    """Researcher unlocks debrief for participant."""
    session = request.session_obj
    session.debrief_unlocked = True
    session.save()
    
    AuditLog.objects.create(
        session=session,
        action='DEBRIEF_UNLOCK',
        actor_role='R',
        details={}
    )
    
    messages.success(request, "Debrief unlocked for participant.")
    return redirect('experiment:researcher_dashboard')


@require_POST
@require_role('R')
def verbal_record(request):
    """Record verbal stage response."""
    session = request.session_obj
    trial_id = request.POST.get('trial_id')
    answer = request.POST.get('answer')
    confidence = request.POST.get('confidence')
    
    try:
        trial = Trial16.objects.get(id=trial_id)
        VerbalResult.objects.update_or_create(
            session=session,
            trial=trial,
            defaults={'answer': answer, 'confidence': confidence}
        )
        return JsonResponse({'success': True})
    except Trial16.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Trial not found'})


@require_POST
@require_role('R')
@require_stage(6)
def verbal_play(request):
    """Trigger synchronized verbal question audio playback for all roles."""
    session = request.session_obj
    trial_id = request.POST.get('trial_id')

    try:
        trial = Trial16.objects.get(id=trial_id)
    except Trial16.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Trial not found'}, status=404)

    session.verbal_play_trial_number = trial.number
    session.verbal_play_nonce += 1
    session.save(update_fields=['verbal_play_trial_number', 'verbal_play_nonce', 'updated_at'])

    return JsonResponse({
        'success': True,
        'trial_number': trial.number,
        'nonce': session.verbal_play_nonce,
        'audio_url': static(f'experiment/audio/verbal_q{trial.number}.wav'),
    })


@csrf_exempt
@require_GET
def session_status_api(request, group_id):
    """API endpoint for polling session status."""
    try:
        session = Session.objects.get(group_id=group_id)
        
        tokens = [
            request.COOKIES.get('session_token_R'),
            request.COOKIES.get('session_token_P'),
            request.COOKIES.get('session_token'),
        ]
        for token in {token for token in tokens if token}:
            try:
                member = SessionMember.objects.get(session_token=token, session=session)
                member.last_seen = timezone.now()
                member.save(update_fields=['last_seen'])
            except SessionMember.DoesNotExist:
                pass
        
        members_info = []
        for m in session.members.all():
            members_info.append({
                'role': m.get_role_display(),
                'last_seen': m.last_seen.isoformat() if m.last_seen else None,
            })
        
        return JsonResponse({
            'stage': session.stage,
            'stage_name': session.get_stage_display_name(),
            'debrief_unlocked': session.debrief_unlocked,
            'verbal_play_trial_number': session.verbal_play_trial_number,
            'verbal_play_nonce': session.verbal_play_nonce,
            'members': members_info,
        })
    except Session.DoesNotExist:
        return JsonResponse({'error': 'Session not found'}, status=404)


@require_role('R')
def export_csv(request, group_id):
    """Export session data as CSV."""
    session = request.session_obj
    
    if session.group_id != group_id:
        return HttpResponseForbidden("Access denied.")
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="session_{group_id}.csv"'
    
    writer = csv.writer(response)
    
    writer.writerow(['Session Info'])
    writer.writerow(['Group ID', 'Stage', 'Yes Side', 'No Side', 'Created'])
    writer.writerow([session.group_id, session.stage, session.yes_side, session.no_side, session.created_at])
    writer.writerow([])
    
    consent = ConsentInfo.objects.filter(session=session).first()
    if consent:
        writer.writerow(['Consent Info'])
        writer.writerow(['Consent Given'])
        writer.writerow([consent.consent_given])
        writer.writerow([])

    demographics = DemographicInfo.objects.filter(session=session).first()
    if demographics:
        writer.writerow(['Demographics'])
        writer.writerow([
            'HSP ID',
            'Heard About Ouija Board',
            'Played With Ouija Board',
            'Planchette Movement Explanation',
            'Percent Life In North America',
            'Percent Life Outside North America',
            'Birth City/Country',
            "Mother's Birth City/Country",
            "Father's Birth City/Country",
            'Primary Language',
            'Other Languages',
            'Countries Over One Month',
            'High School Location',
            'Attended International School',
            'On Exchange',
            'Cultural Classification',
        ])
        writer.writerow([
            demographics.hsp_id,
            demographics.heard_ouija,
            demographics.played_ouija,
            demographics.planchette_explanation,
            demographics.percent_life_in_north_america,
            demographics.percent_life_outside_north_america,
            demographics.birth_city_country,
            demographics.mother_birth_city_country,
            demographics.father_birth_city_country,
            demographics.primary_language,
            demographics.other_languages,
            demographics.countries_over_one_month,
            demographics.high_school_location,
            demographics.attended_international_school,
            demographics.on_exchange,
            demographics.cultural_classification,
        ])
        writer.writerow([])
    
    writer.writerow(['72 Questions Responses'])
    writer.writerow(['Question #', 'Question Text', 'Participant Answer', 'Participant Confidence'])
    
    questions = Question72.objects.all()
    p_responses = {r.question_id: r for r in Response72.objects.filter(session=session, member__role='P')}
    for q in questions:
        p_r = p_responses.get(q.id)
        writer.writerow([
            q.number,
            q.text,
            p_r.answer if p_r else '',
            p_r.confidence if p_r else '',
        ])
    writer.writerow([])
    
    survey = PostSurvey.objects.filter(session=session).first()
    if survey:
        writer.writerow(['Post Survey'])
        writer.writerow(['YES Side Assigned', 'NO Side Assigned', 'Completed Study'])
        writer.writerow([survey.yes_side_assigned, survey.no_side_assigned, survey.completed_study])
        writer.writerow([])

    personality = PersonalitySurvey.objects.filter(session=session).first()
    if personality:
        writer.writerow(['Personality Questionnaire'])
        writer.writerow(['Item #', 'Statement', 'Response'])
        for item_number in sorted(personality.responses.keys(), key=lambda value: int(value)):
            item = personality.responses[item_number]
            writer.writerow([
                item_number,
                item.get('statement', ''),
                item.get('response', ''),
            ])
        writer.writerow([])
    
    trials = Trial16.objects.all()
    writer.writerow(['Prediction Feedback Task'])
    writer.writerow(['Trial #', 'Question Text', 'Answer', 'Confidence', 'Reaction Time ms', 'Predicted Answer', 'Matched'])
    prediction_results = {
        pr.trial_id: pr
        for pr in PredictionResponse.objects.filter(session=session, member__role='P').select_related('trial')
    }
    for t in trials:
        pr = prediction_results.get(t.id)
        writer.writerow([
            t.number,
            t.text,
            pr.answer if pr else '',
            pr.confidence if pr else '',
            pr.reaction_time_ms if pr else '',
            pr.predicted_answer if pr else '',
            pr.matched if pr else '',
        ])

    AuditLog.objects.create(
        session=session,
        action='EXPORT',
        actor_role='R',
        details={'format': 'csv'}
    )
    
    return response


def logout_view(request):
    """Clear session and redirect to home."""
    response = redirect('experiment:home')
    role = request.GET.get('role', '').upper()
    if role in {'R', 'P'}:
        response.delete_cookie(f'session_token_{role}')
        if request.COOKIES.get('last_role') == role:
            response.delete_cookie('last_role')
    else:
        response.delete_cookie('session_token_R')
        response.delete_cookie('session_token_P')
        response.delete_cookie('last_role')
    response.delete_cookie('session_token')
    return response
