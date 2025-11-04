from django.contrib import admin
from .models import Team, Profile, ReadinessReport, TeamTag


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'team']
    list_filter = ['role', 'team']
    search_fields = ['user__username', 'user__first_name', 'user__last_name']
    list_select_related = ['user', 'team']


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
