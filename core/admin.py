from django.contrib import admin
from .models import Team, Profile, ReadinessReport, TeamTag, EmailVerification, PlayerPersonalLabel, FeatureRequest, FeatureRequestComment


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


@admin.register(FeatureRequest)
class FeatureRequestAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'request_type', 'status', 'upvote_count', 'created_at']
    list_filter = ['request_type', 'status', 'created_at']
    search_fields = ['title', 'description', 'user__username', 'user__email']
    list_select_related = ['user']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at', 'updated_at', 'upvote_count_display']
    filter_horizontal = ['upvoted_by']
    
    fieldsets = (
        ('Request Details', {
            'fields': ('user', 'title', 'description', 'request_type', 'status')
        }),
        ('Engagement', {
            'fields': ('upvoted_by', 'upvote_count_display')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def upvote_count_display(self, obj):
        return obj.upvote_count()
    upvote_count_display.short_description = 'Upvotes'


@admin.register(FeatureRequestComment)
class FeatureRequestCommentAdmin(admin.ModelAdmin):
    list_display = ['feature_request', 'user', 'created_at', 'comment_preview']
    list_filter = ['created_at']
    search_fields = ['comment', 'user__username', 'feature_request__title']
    list_select_related = ['user', 'feature_request']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at', 'updated_at']
    
    def comment_preview(self, obj):
        return obj.comment[:50] + '...' if len(obj.comment) > 50 else obj.comment
    comment_preview.short_description = 'Comment Preview'
