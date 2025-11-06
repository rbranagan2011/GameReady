"""
Context processors for GameReady app.
"""


def coach_active_team(request):
    """
    Context processor to make the active team available in all templates.
    For coaches: Uses session-based active team or falls back to primary team.
    For athletes: Uses their primary team or first team from ManyToMany.
    
    This makes team branding (logo) available to both coaches and athletes.
    """
    context = {}
    
    if request.user.is_authenticated:
        try:
            profile = request.user.profile
            from .models import Team
            
            if profile.role == 'COACH':
                # Get all teams the coach belongs to (primary + ManyToMany)
                coach_teams = profile.get_teams()
                
                if coach_teams:
                    # Check session for active team
                    active_team_id = request.session.get('active_team_id')
                    active_team = None
                    
                    if active_team_id:
                        try:
                            active_team = Team.objects.get(id=active_team_id)
                            # Verify coach is still a member of this team
                            if active_team not in coach_teams:
                                active_team = None
                        except Team.DoesNotExist:
                            active_team = None
                    
                    # Fall back to primary team or first team
                    if not active_team:
                        if profile.team and profile.team in coach_teams:
                            active_team = profile.team
                        elif coach_teams:
                            active_team = coach_teams[0]
                    
                    context['coach_active_team'] = active_team
                    context['coach_teams'] = coach_teams
                    context['has_multiple_teams'] = len(coach_teams) > 1
            elif profile.role == 'ATHLETE':
                # For athletes, use their primary team or first team
                if profile.team:
                    context['coach_active_team'] = profile.team
                elif profile.teams.exists():
                    context['coach_active_team'] = profile.teams.first()
        except Exception:
            # If profile doesn't exist or any error, just pass empty context
            pass
    
    return context

