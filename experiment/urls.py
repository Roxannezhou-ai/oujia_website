from django.urls import path
from . import views

app_name = 'experiment'

urlpatterns = [
    # Main entry point
    path('', views.home, name='home'),
    path('join/', views.join, name='join'),
    
    # Role-specific dashboards
    path('dashboard/researcher/', views.researcher_dashboard, name='researcher_dashboard'),
    path('dashboard/participant/', views.participant_dashboard, name='participant_dashboard'),
    
    # Stage-specific pages
    path('consent/', views.consent_page, name='consent'),
    path('demographics/', views.demographics_page, name='demographics'),
    path('questions72/', views.questions72_page, name='questions72'),
    path('ouija/', views.ouija_page, name='ouija'),
    path('api/ouija/state/', views.ouija_state_api, name='ouija_state'),
    path('api/ouija/update/', views.ouija_update_api, name='ouija_update'),
    path('api/ouija/traces/', views.ouija_trace_api, name='ouija_traces'),
    path('post-survey/', views.post_survey_page, name='post_survey'),
    path('personality/', views.personality_page, name='personality'),
    path('verbal/', views.verbal_page, name='verbal'),
    path('debrief/', views.debrief_page, name='debrief'),
    
    # Researcher controls
    path('researcher/advance-stage/', views.advance_stage, name='advance_stage'),
    path('researcher/unlock-debrief/', views.unlock_debrief, name='unlock_debrief'),
    path('researcher/verbal-record/', views.verbal_record, name='verbal_record'),
    path('researcher/verbal-play/', views.verbal_play, name='verbal_play'),
    path('researcher/ouija-refresh/', views.ouija_refresh_api, name='ouija_refresh'),
    path('researcher/ouija-trace-image/<int:question_number>.svg', views.ouija_trace_image_svg, name='ouija_trace_image'),
    
    # API endpoints for polling
    path('api/session/<str:group_id>/status/', views.session_status_api, name='session_status'),
    
    # Export
    path('export/<str:group_id>.csv', views.export_csv, name='export_csv'),
    
    # Logout
    path('logout/', views.logout_view, name='logout'),
]
