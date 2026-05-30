import uuid
import secrets
from django.db import models
from django.utils import timezone


class Session(models.Model):
    """Represents an experiment session for a group."""
    STAGE_CHOICES = [
        (0, 'Waiting'),
        (1, 'Consent'),
        (2, 'Demographics Questionnaire'),
        (3, 'Initial Question Set'),
        (4, 'Prediction Feedback Task'),
        (5, 'Post-Study Questionnaire'),
        (6, 'Personality Questionnaire'),
        (7, 'Debrief'),
    ]
    SIDE_CHOICES = [
        ('L', 'Left'),
        ('R', 'Right'),
    ]
    
    group_id = models.CharField(max_length=50, unique=True, db_index=True)
    yes_side = models.CharField(max_length=1, choices=SIDE_CHOICES, default='L')
    no_side = models.CharField(max_length=1, choices=SIDE_CHOICES, default='R')
    stage = models.IntegerField(choices=STAGE_CHOICES, default=0)
    notes = models.TextField(blank=True, default='')
    debrief_unlocked = models.BooleanField(default=False)
    ouija_x = models.FloatField(default=0.5)
    ouija_y = models.FloatField(default=0.5)
    ouija_last_actor = models.CharField(max_length=1, blank=True, default='')
    ouija_round = models.PositiveIntegerField(default=1)
    ouija_updated_at = models.DateTimeField(null=True, blank=True)
    verbal_play_trial_number = models.IntegerField(null=True, blank=True)
    verbal_play_nonce = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Session {self.group_id} (Stage {self.stage})"
    
    def get_stage_display_name(self):
        return dict(self.STAGE_CHOICES).get(self.stage, 'Unknown')


class SessionMember(models.Model):
    """Represents a participant in a session with a specific role."""
    ROLE_CHOICES = [
        ('R', 'Researcher'),
        ('P', 'Participant'),
    ]
    
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='members')
    role = models.CharField(max_length=1, choices=ROLE_CHOICES)
    session_token = models.CharField(max_length=64, unique=True, db_index=True)
    last_seen = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['session', 'role']
    
    def __str__(self):
        return f"{self.get_role_display()} in {self.session.group_id}"
    
    @classmethod
    def generate_token(cls):
        return secrets.token_urlsafe(48)


class Question72(models.Model):
    """72 yes/no questions for stage 3."""
    number = models.IntegerField(unique=True)
    text = models.TextField()
    
    class Meta:
        ordering = ['number']
    
    def __str__(self):
        return f"Q{self.number}: {self.text[:50]}"


class Response72(models.Model):
    """Response to a Question72 by a participant."""
    ANSWER_CHOICES = [
        ('Y', 'Yes'),
        ('N', 'No'),
    ]
    CONFIDENCE_CHOICES = [
        ('G', 'Guess'),
        ('S', 'Sure'),
    ]
    
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='responses72')
    member = models.ForeignKey(SessionMember, on_delete=models.CASCADE, related_name='responses72')
    question = models.ForeignKey(Question72, on_delete=models.CASCADE)
    answer = models.CharField(max_length=1, choices=ANSWER_CHOICES)
    confidence = models.CharField(max_length=1, choices=CONFIDENCE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['session', 'member', 'question']
    
    def __str__(self):
        return f"{self.member} - Q{self.question.number}: {self.answer}/{self.confidence}"


class Trial16(models.Model):
    """16 trial questions for prediction-feedback task."""
    number = models.IntegerField(unique=True)
    text = models.TextField()
    
    class Meta:
        ordering = ['number']
    
    def __str__(self):
        return f"Trial {self.number}: {self.text[:50]}"

    def get_verbal_code(self):
        pair = (self.number + 1) // 2
        return f"B'{pair}" if self.number % 2 == 1 else f"B''{pair}"


class VerbalResult(models.Model):
    """Legacy verbal-stage result recorded by researcher."""
    ANSWER_CHOICES = [
        ('Y', 'Yes'),
        ('N', 'No'),
    ]
    CONFIDENCE_CHOICES = [
        ('G', 'Guess'),
        ('S', 'Sure'),
    ]
    
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='verbal_results')
    trial = models.ForeignKey(Trial16, on_delete=models.CASCADE)
    answer = models.CharField(max_length=1, choices=ANSWER_CHOICES)
    confidence = models.CharField(max_length=1, choices=CONFIDENCE_CHOICES)
    recorded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['session', 'trial']
    
    def __str__(self):
        return f"Session {self.session.group_id} - Trial {self.trial.number}"


class PredictionResponse(models.Model):
    """Timed response from the deceptive prediction-feedback task."""
    ANSWER_CHOICES = [
        ('Y', 'Yes'),
        ('N', 'No'),
    ]
    CONFIDENCE_CHOICES = [
        ('G', 'Guess'),
        ('S', 'Sure'),
    ]

    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='prediction_responses')
    member = models.ForeignKey(SessionMember, on_delete=models.CASCADE, related_name='prediction_responses')
    trial = models.ForeignKey(Trial16, on_delete=models.CASCADE)
    answer = models.CharField(max_length=1, choices=ANSWER_CHOICES)
    confidence = models.CharField(max_length=1, choices=CONFIDENCE_CHOICES)
    reaction_time_ms = models.PositiveIntegerField()
    predicted_answer = models.CharField(max_length=1, choices=ANSWER_CHOICES)
    matched = models.BooleanField()
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['session', 'member', 'trial']
        ordering = ['trial__number']

    def __str__(self):
        return f"Session {self.session.group_id} - prediction trial {self.trial.number}"


class ConsentInfo(models.Model):
    """Consent from participant (Stage 1)."""
    session = models.OneToOneField(Session, on_delete=models.CASCADE, related_name='consent_info')
    member = models.ForeignKey(SessionMember, on_delete=models.CASCADE)
    consent_given = models.BooleanField(default=False)
    age = models.IntegerField(null=True, blank=True)
    gender = models.CharField(max_length=50, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Consent for {self.session.group_id}"


class DemographicInfo(models.Model):
    """Demographic questionnaire responses (Stage 2)."""
    session = models.OneToOneField(Session, on_delete=models.CASCADE, related_name='demographic_info')
    member = models.ForeignKey(SessionMember, on_delete=models.CASCADE)
    hsp_id = models.CharField(max_length=100, blank=True, default='')
    heard_ouija = models.CharField(max_length=20, blank=True, default='')
    played_ouija = models.CharField(max_length=10, blank=True, default='')
    planchette_explanation = models.TextField(blank=True, default='')
    percent_life_in_north_america = models.PositiveIntegerField(default=0)
    percent_life_outside_north_america = models.PositiveIntegerField(default=0)
    birth_city_country = models.CharField(max_length=200, blank=True, default='')
    mother_birth_city_country = models.CharField(max_length=200, blank=True, default='')
    father_birth_city_country = models.CharField(max_length=200, blank=True, default='')
    primary_language = models.CharField(max_length=100, blank=True, default='')
    other_languages = models.TextField(blank=True, default='')
    countries_over_one_month = models.TextField(blank=True, default='')
    high_school_location = models.CharField(max_length=200, blank=True, default='')
    attended_international_school = models.CharField(max_length=10, blank=True, default='')
    on_exchange = models.CharField(max_length=10, blank=True, default='')
    cultural_classification = models.CharField(max_length=20, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Demographics for {self.session.group_id}"


class PostSurvey(models.Model):
    """Post-study questionnaire responses (Stage 5)."""
    session = models.OneToOneField(Session, on_delete=models.CASCADE, related_name='post_survey')
    member = models.ForeignKey(SessionMember, on_delete=models.CASCADE)
    yes_side_assigned = models.CharField(max_length=10, blank=True, default='')
    no_side_assigned = models.CharField(max_length=10, blank=True, default='')
    completed_study = models.CharField(max_length=10, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"PostSurvey for {self.session.group_id}"


class PersonalitySurvey(models.Model):
    """Personality questionnaire responses (Stage 6)."""
    session = models.OneToOneField(Session, on_delete=models.CASCADE, related_name='personality_survey')
    member = models.ForeignKey(SessionMember, on_delete=models.CASCADE)
    responses = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"PersonalitySurvey for {self.session.group_id}"


class AuditLog(models.Model):
    """Audit log for tracking important actions."""
    ACTION_TYPES = [
        ('JOIN', 'Member Joined'),
        ('STAGE_CHANGE', 'Stage Changed'),
        ('RESPONSE', 'Response Submitted'),
        ('EXPORT', 'Data Exported'),
        ('DEBRIEF_UNLOCK', 'Debrief Unlocked'),
    ]
    
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='audit_logs', null=True)
    action = models.CharField(max_length=20, choices=ACTION_TYPES)
    actor_role = models.CharField(max_length=1, blank=True, default='')
    details = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.action} at {self.created_at}"


class OuijaTrace(models.Model):
    """Mouse trace point captured during Ouija stage."""
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='ouija_traces')
    member = models.ForeignKey(SessionMember, on_delete=models.CASCADE, related_name='ouija_traces')
    question_number = models.PositiveIntegerField(default=1)
    x = models.FloatField(help_text="Normalized x position (0..1)")
    y = models.FloatField(help_text="Normalized y position (0..1)")
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['recorded_at']

    def __str__(self):
        return f"Trace {self.session.group_id} {self.member.role} ({self.x:.3f}, {self.y:.3f})"
