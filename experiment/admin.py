from django.contrib import admin
from .models import (
    Session, SessionMember, Question72, Response72,
    Trial16, VerbalResult, PredictionResponse, ConsentInfo, DemographicInfo,
    PostSurvey, PersonalitySurvey, AuditLog, OuijaTrace
)


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ['group_id', 'stage', 'yes_side', 'no_side', 'debrief_unlocked', 'ouija_round', 'ouija_x', 'ouija_y', 'created_at']
    list_filter = ['stage', 'debrief_unlocked']
    search_fields = ['group_id']
    readonly_fields = ['created_at', 'updated_at', 'ouija_updated_at']


@admin.register(SessionMember)
class SessionMemberAdmin(admin.ModelAdmin):
    list_display = ['session', 'role', 'last_seen', 'created_at']
    list_filter = ['role']
    search_fields = ['session__group_id']
    readonly_fields = ['session_token', 'created_at']


@admin.register(Question72)
class Question72Admin(admin.ModelAdmin):
    list_display = ['number', 'text']
    ordering = ['number']
    search_fields = ['text']


@admin.register(Response72)
class Response72Admin(admin.ModelAdmin):
    list_display = ['session', 'member', 'question', 'answer', 'confidence', 'created_at']
    list_filter = ['answer', 'confidence', 'member__role']
    search_fields = ['session__group_id']


@admin.register(Trial16)
class Trial16Admin(admin.ModelAdmin):
    list_display = ['number', 'text']
    ordering = ['number']
    search_fields = ['text']


@admin.register(VerbalResult)
class VerbalResultAdmin(admin.ModelAdmin):
    list_display = ['session', 'trial', 'answer', 'confidence', 'recorded_at']
    list_filter = ['answer', 'confidence']
    search_fields = ['session__group_id']


@admin.register(PredictionResponse)
class PredictionResponseAdmin(admin.ModelAdmin):
    list_display = ['session', 'member', 'trial', 'answer', 'confidence', 'reaction_time_ms', 'predicted_answer', 'matched', 'recorded_at']
    list_filter = ['answer', 'confidence', 'matched']
    search_fields = ['session__group_id', 'trial__text']


@admin.register(ConsentInfo)
class ConsentInfoAdmin(admin.ModelAdmin):
    list_display = ['session', 'consent_given', 'created_at']
    list_filter = ['consent_given']
    search_fields = ['session__group_id']


@admin.register(DemographicInfo)
class DemographicInfoAdmin(admin.ModelAdmin):
    list_display = [
        'session',
        'hsp_id',
        'heard_ouija',
        'played_ouija',
        'percent_life_in_north_america',
        'percent_life_outside_north_america',
        'primary_language',
        'attended_international_school',
        'on_exchange',
        'cultural_classification',
        'created_at',
    ]
    list_filter = ['heard_ouija', 'played_ouija', 'attended_international_school', 'on_exchange', 'cultural_classification']
    search_fields = ['session__group_id']


@admin.register(PostSurvey)
class PostSurveyAdmin(admin.ModelAdmin):
    list_display = ['session', 'yes_side_assigned', 'no_side_assigned', 'completed_study', 'created_at']
    list_filter = ['yes_side_assigned', 'no_side_assigned', 'completed_study']
    search_fields = ['session__group_id']


@admin.register(PersonalitySurvey)
class PersonalitySurveyAdmin(admin.ModelAdmin):
    list_display = ['session', 'created_at']
    search_fields = ['session__group_id']


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['session', 'action', 'actor_role', 'created_at']
    list_filter = ['action', 'actor_role']
    search_fields = ['session__group_id']
    readonly_fields = ['created_at']


@admin.register(OuijaTrace)
class OuijaTraceAdmin(admin.ModelAdmin):
    list_display = ['session', 'member', 'question_number', 'x', 'y', 'recorded_at']
    list_filter = ['member__role']
    search_fields = ['session__group_id']
    readonly_fields = ['recorded_at']
