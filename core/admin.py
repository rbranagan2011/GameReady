from django.contrib import admin
from .models import Team, Profile, ReadinessReport, TeamTag, EmailVerification, PlayerPersonalLabel


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ['name', 'logo_display_mode', 'target_readiness']
    search_fields = ['name']
    fields = ['name', 'target_readiness', 'join_code', 'logo', 'logo_display_mode', 
              'background_opacity', 'background_position']
    readonly_fields = ['join_code']


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'team', 'timezone']
    list_filter = ['role', 'team', 'timezone']
    search_fields = ['user__username', 'user__first_name', 'user__last_name']
    list_select_related = ['user', 'team']
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'role', 'team')
        }),
        ('Player Status', {
            'fields': ('current_status', 'status_note', 'status_updated_at')
        }),
        ('Reminder Settings', {
            'fields': ('timezone',),
            'description': 'Timezone for daily reminder emails (e.g., America/New_York, Europe/London)'
        }),
    )


@admin.register(ReadinessReport)
class ReadinessReportAdmin(admin.ModelAdmin):
    list_display = ['athlete', 'date_created', 'readiness_score', 'sleep_quality', 'energy_fatigue', 'muscle_soreness', 'mood_stress', 'motivation', 'nutrition_quality', 'hydration']
    list_filter = ['date_created', 'athlete__profile__team']
    search_fields = ['athlete__username', 'athlete__first_name', 'athlete__last_name']
    list_select_related = ['athlete', 'athlete__profile']
    date_hierarchy = 'date_created'
    readonly_fields = ['readiness_score']
    
    fieldsets = (
        ('Athlete & Date', {
            'fields': ('athlete', 'date_created')
        }),
        ('Wellness Metrics', {
            'fields': ('sleep_quality', 'energy_fatigue', 'muscle_soreness', 'mood_stress', 'motivation', 'nutrition_quality', 'hydration')
        }),
        ('Calculated Score', {
            'fields': ('readiness_score',),
            'classes': ('collapse',)
        }),
        ('Additional Info', {
            'fields': ('comments',)
        }),
    )


@admin.register(TeamTag)
class TeamTagAdmin(admin.ModelAdmin):
    list_display = ['name', 'team', 'target_min', 'target_max', 'color']
    list_filter = ['team']
    search_fields = ['name', 'team__name']


@admin.register(EmailVerification)
class EmailVerificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'verified', 'created_at', 'expires_at', 'is_expired']
    list_filter = ['verified', 'created_at']
    search_fields = ['user__email', 'user__username', 'token']
    readonly_fields = ['token', 'created_at', 'expires_at', 'is_expired']
    list_select_related = ['user']


@admin.register(PlayerPersonalLabel)
class PlayerPersonalLabelAdmin(admin.ModelAdmin):
    list_display = ['athlete', 'date', 'label', 'created_at', 'updated_at']
    list_filter = ['date', 'created_at']
    search_fields = ['athlete__username', 'athlete__first_name', 'athlete__last_name', 'label']
    list_select_related = ['athlete']
    date_hierarchy = 'date'
