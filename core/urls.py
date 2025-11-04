from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),
    # Registration and onboarding
    path('role-selection/', views.role_selection, name='role_selection'),
    path('signup/', views.signup, name='signup'),
    path('team-setup/coach/', views.team_setup_coach, name='team_setup_coach'),
    path('athlete-setup/', views.athlete_setup, name='athlete_setup'),
    path('join/<str:code>/', views.join_team_link, name='join_team_link'),
    path('get-started/', views.get_started, name='get_started'),
    path('get-started/<int:step>/', views.get_started, name='get_started'),
    # Existing routes
    path('submit-report/', views.submit_readiness_report, name='submit_report'),
    path('coach-dashboard/', views.coach_dashboard, name='coach_dashboard'),
    path('coach-dashboard/player-metrics/<int:athlete_id>/', views.player_metrics_ajax, name='player_metrics_ajax'),
    path('player-dashboard/', views.player_dashboard, name='player_dashboard'),
    path('player-dashboard/metrics/', views.player_metrics_self_ajax, name='player_metrics_self_ajax'),
    path('player-dashboard/status/', views.player_status, name='player_status'),
    path('player-dashboard/status/set/', views.player_set_status, name='player_set_status'),
    path('player-dashboard/weekly/', views.player_week_partial, name='player_week_partial'),
    path('player-dashboard/monthly/', views.player_month_partial, name='player_month_partial'),
    # Coach view of a specific athlete's dashboard + partials
    path('coach/player/<int:athlete_id>/', views.coach_player_dashboard, name='coach_player_dashboard'),
    path('coach/player/<int:athlete_id>/weekly/', views.coach_player_week_partial, name='coach_player_week_partial'),
    path('coach/player/<int:athlete_id>/monthly/', views.coach_player_month_partial, name='coach_player_month_partial'),
    path('athlete/<int:athlete_id>/', views.athlete_detail, name='athlete_detail'),
    path('team-schedule/', views.team_schedule_settings, name='team_schedule_settings'),
    path('team-schedule/monthly/', views.team_schedule_month_partial, name='team_schedule_month_partial'),
    path('team-tags/', views.team_tag_management, name='team_tag_management'),
    path('team-tags/create/', views.team_tag_create, name='team_tag_create'),
    path('team-tags/edit/<int:tag_id>/', views.team_tag_edit, name='team_tag_edit'),
    path('team-tags/delete/<int:tag_id>/', views.team_tag_delete, name='team_tag_delete'),
    # Team Administration
    path('team-admin/', views.team_admin, name='team_admin'),
]
