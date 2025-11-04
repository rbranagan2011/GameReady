from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth import login
from django.utils import timezone
from django.contrib import messages
from django.db.models import Avg, Count, Max, Min
from django.http import JsonResponse
from datetime import timedelta, datetime
from .models import ReadinessReport, Profile, TeamTag, TeamSchedule, ReadinessStatus, Team
from .forms import ReadinessReportForm, TeamScheduleForm, TeamTagForm, TeamNameForm, UserSignupForm, TeamCreationForm, JoinTeamForm
from django.template.loader import render_to_string
from django.urls import reverse


@login_required
def submit_readiness_report(request):
    """
    View for an athlete to submit their daily readiness report.
    """
    # First, check if the user is an athlete.
    # We assume a Profile object is created for every user.
    try:
        if request.user.profile.role != Profile.Role.ATHLETE:
            # If not an athlete, redirect them to the (future) coach dashboard
            messages.warning(request, "You are not an athlete. Redirecting to dashboard.")
            return redirect('coach_dashboard')  # We will create this URL later
    except Profile.DoesNotExist:
        # Handle case where user has no profile
        messages.error(request, "Your profile is not set up. Please contact your coach.")
        return redirect('logout')  # Or some other appropriate page

    # Check if the athlete has already submitted a report today
    today = timezone.now().date()
    try:
        existing_report = ReadinessReport.objects.get(athlete=request.user, date_created=today)
    except ReadinessReport.DoesNotExist:
        existing_report = None

    if existing_report:
        # If a report already exists today, go straight to the dashboard (no message)
        return redirect('core:player_dashboard')

    # If this is a POST request, they are submitting the form
    if request.method == 'POST':
        form = ReadinessReportForm(request.POST)

        if form.is_valid():
            # Form is valid, but don't save to database just yet
            report = form.save(commit=False)

            # Set the 'athlete' field to the currently logged-in user
            report.athlete = request.user

            # The 'date_created' is already set by default in the model

            # Now save the report to the database (this will also trigger
            # the 'calculate_readiness_score' method in your model)
            report.save()

            # Redirect to Player Dashboard after submission (no confirmation message)
            return redirect('core:player_dashboard')
        else:
            # Form was invalid, show errors
            messages.error(request, "Please correct the errors below.")

    else:
        # This is a GET request, so create an empty form
        form = ReadinessReportForm()

    # Prepare the context to pass to the template
    context = {
        'form': form
    }

    # Render the HTML template with the form
    return render(request, 'core/submit_report.html', context)


def home(request):
    """
    Home page that redirects users based on their role.
    For first-time visitors (not authenticated), redirect to role selection.
    """
    if request.user.is_authenticated:
        try:
            if request.user.profile.role == Profile.Role.ATHLETE:
                return redirect('core:player_dashboard')
            elif request.user.profile.role == Profile.Role.COACH:
                return redirect('core:coach_dashboard')
        except Profile.DoesNotExist:
            messages.error(request, "Your profile is not set up. Please contact your administrator.")
            return redirect('logout')
    
    # If not authenticated, check if this is a first-time visit
    # Simple check: if no users exist or session indicates first visit
    from django.contrib.auth.models import User
    user_count = User.objects.count()
    
    # Redirect to role selection for first-time setup, otherwise login
    if user_count == 0 or request.session.get('first_visit', True):
        request.session['first_visit'] = False
        return redirect('core:role_selection')
    
    # If not authenticated and users exist, redirect to login
    return redirect('login')


@login_required
def coach_dashboard(request):
    """
    Simplified coach dashboard exactly as specified.
    """
    # Check if user is a coach
    try:
        if request.user.profile.role != Profile.Role.COACH:
            messages.warning(request, "Access denied. Coach access required.")
            return redirect('core:home')
    except Profile.DoesNotExist:
        messages.error(request, "Your profile is not set up. Please contact your administrator.")
        return redirect('logout')
    
    # Get coach's team
    coach_team = request.user.profile.team
    if not coach_team:
        messages.warning(request, "You are not assigned to a team.")
        return render(request, 'core/coach_dashboard.html', {'team': None})
    
    # Get date from URL parameter (default to today)
    from datetime import datetime, timedelta
    date_str = request.GET.get('date')
    if date_str:
        try:
            selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            selected_date = timezone.now().date()
    else:
        selected_date = timezone.now().date()
    
    # Calculate previous and next dates for navigation
    prev_date = selected_date - timedelta(days=1)
    next_date = selected_date + timedelta(days=1)
    
    # Handle target update
    if request.method == 'POST' and 'target_readiness' in request.POST:
        try:
            new_target = int(request.POST.get('target_readiness'))
            if 0 <= new_target <= 100:
                coach_team.target_readiness = new_target
                coach_team.save()
                messages.success(request, f"Target updated to {new_target}%")
            else:
                messages.error(request, "Target must be between 0 and 100")
        except ValueError:
            messages.error(request, "Invalid target value")
        return redirect(f'core:coach_dashboard?date={selected_date.strftime("%Y-%m-%d")}')
    
    # Determine day tag for selected date from team schedule
    try:
        team_schedule = TeamSchedule.objects.get(team=coach_team)
        # Fix: Clear auto-populated weekly schedule if it exists (same fix as Step 4)
        # Only clear if: all days have same tag AND schedule appears unedited (created within 1 second of updated) AND no date overrides
        if team_schedule.weekly_schedule:
            weekday_values = [team_schedule.weekly_schedule.get(day) for day in ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'] if team_schedule.weekly_schedule.get(day) is not None]
            time_diff = (team_schedule.updated_at - team_schedule.created_at).total_seconds()
            # Only clear if all 7 days have the same tag, schedule was never manually edited (within 1 second), and no custom date overrides
            if (len(set(weekday_values)) == 1 and len(weekday_values) == 7 and 
                time_diff < 1.0 and 
                not team_schedule.date_overrides):
                # This matches the pattern of auto-population - clear it
                team_schedule.weekly_schedule = {}
                team_schedule.save()
    except TeamSchedule.DoesNotExist:
        team_schedule = TeamSchedule.objects.create(team=coach_team)
    tag_obj = team_schedule.get_day_tag(selected_date)
    day_tag_display = tag_obj.name if tag_obj else None

    # Get team athletes
    team_athletes = User.objects.filter(profile__team=coach_team, profile__role=Profile.Role.ATHLETE)
    
    # Get reports for selected date
    selected_date_reports = ReadinessReport.objects.filter(
        athlete__in=team_athletes,
        date_created=selected_date
    ).select_related('athlete')
    
    # Get last 7 days for historic average
    week_ago = selected_date - timedelta(days=6)
    week_reports = ReadinessReport.objects.filter(
        athlete__in=team_athletes,
        date_created__gte=week_ago,
        date_created__lte=selected_date
    ).select_related('athlete')
    
    # Calculate today's team average
    today_avg = selected_date_reports.aggregate(avg=Avg('readiness_score'))['avg']
    today_team_avg = round(today_avg or 0)
    
    # Calculate historic 7-day average
    historic_avg = week_reports.aggregate(avg=Avg('readiness_score'))['avg']
    historic_team_avg = round(historic_avg or 0)
    
    # Compute summary counts using a true target range when available
    # If the day tag defines target_min/target_max, use that; otherwise fall back to team target ±5
    if tag_obj and hasattr(tag_obj, 'target_min') and hasattr(tag_obj, 'target_max') and tag_obj.target_min is not None and tag_obj.target_max is not None:
        range_min = int(tag_obj.target_min)
        range_max = int(tag_obj.target_max)
    else:
        midpoint = int(coach_team.target_readiness)
        range_min = max(0, midpoint - 5)
        range_max = min(100, midpoint + 5)
    target_range_display = f"{range_min}\u2013{range_max}%"

    num_above_target = 0
    num_in_target = 0
    num_below_target = 0
    for r in selected_date_reports:
        if r.readiness_score is None:
            continue
        if r.readiness_score > range_max:
            num_above_target += 1
        elif range_min <= r.readiness_score <= range_max:
            num_in_target += 1
        else:
            num_below_target += 1

    # Determine class for today's average relative to the target range
    if today_team_avg > range_max:
        avg_status_class = 'value-warn'  # dark blue for above
    elif today_team_avg < range_min:
        avg_status_class = 'value-orange'   # orange for below
    else:
        avg_status_class = 'value-good'  # green for in range

    # Prepare squad list data (sorted by readiness ascending)
    squad_data = []
    for athlete in team_athletes:
        try:
            report = selected_date_reports.get(athlete=athlete)
            readiness = report.readiness_score
            
            # Compute simple info pill: 'risk', 'rest', 'non-compliant'
            pill = None
            # 1) REST: high soreness (low score) and low energy today
            try:
                if report.muscle_soreness <= 3 and report.energy_fatigue <= 4:
                    pill = 'rest'
            except Exception:
                pass

            # 2) RISK: below target range for 3 consecutive days (including today)
            if pill is None:
                try:
                    from datetime import timedelta
                    last3 = [selected_date - timedelta(days=i) for i in range(3)]
                    below_count = 0
                    # need schedule for per-day range
                    try:
                        schedule = TeamSchedule.objects.get(team=coach_team)
                    except TeamSchedule.DoesNotExist:
                        schedule = TeamSchedule.objects.create(team=coach_team)
                    for d in last3:
                        r = ReadinessReport.objects.filter(athlete=athlete, date_created=d).first()
                        if not r:
                            below_count = 0
                            break
                        tag_obj = schedule.get_day_tag(d)
                        if tag_obj and hasattr(tag_obj, 'target_min') and hasattr(tag_obj, 'target_max') and tag_obj.target_min is not None and tag_obj.target_max is not None:
                            rmin = int(tag_obj.target_min)
                            rmax = int(tag_obj.target_max)
                        else:
                            midpoint = int(coach_team.target_readiness)
                            rmin = max(0, midpoint - 5)
                            rmax = min(100, midpoint + 5)
                        if r.readiness_score < rmin:
                            below_count += 1
                        else:
                            below_count = 0
                            break
                    if below_count == 3:
                        pill = 'risk'
                except Exception:
                    pass

            # 3) NON-COMPLIANT: missed >= 2 of last 3 days
            if pill is None:
                try:
                    from datetime import timedelta
                    last3 = [selected_date - timedelta(days=i) for i in range(3)]
                    submitted = 0
                    for d in last3:
                        if ReadinessReport.objects.filter(athlete=athlete, date_created=d).exists():
                            submitted += 1
                    if (3 - submitted) >= 2:
                        pill = 'non'
                except Exception:
                    pass
            
            squad_data.append({
                'athlete': athlete,
                'readiness': readiness,
                'pill': pill,
                'submitted': True,
                'comment': (report.comments or '').strip() if hasattr(report, 'comments') else '',
                'has_comment': bool(getattr(report, 'comments', '').strip())
            })
        except ReadinessReport.DoesNotExist:
            squad_data.append({
                'athlete': athlete,
                'readiness': None,
                'pill': 'non' if ReadinessReport.objects.filter(athlete=athlete, date_created=selected_date).exists() is False else None,
                'submitted': False,
                'comment': '',
                'has_comment': False
            })
    
    # Sort by readiness ascending (lowest first), with non-submitted at end
    squad_data.sort(key=lambda x: (x['readiness'] is None, x['readiness'] or 0))
    
    # Calculate insights - lowest and best scored categories
    insights = {}
    if selected_date_reports.exists():
        # Calculate team averages for each metric
        metric_averages = {
            'sleep_quality': selected_date_reports.aggregate(avg=Avg('sleep_quality'))['avg'] or 0,
            'energy_fatigue': selected_date_reports.aggregate(avg=Avg('energy_fatigue'))['avg'] or 0,
            'muscle_soreness': selected_date_reports.aggregate(avg=Avg('muscle_soreness'))['avg'] or 0,
            'mood_stress': selected_date_reports.aggregate(avg=Avg('mood_stress'))['avg'] or 0,
            'motivation': selected_date_reports.aggregate(avg=Avg('motivation'))['avg'] or 0,
            'nutrition_quality': selected_date_reports.aggregate(avg=Avg('nutrition_quality'))['avg'] or 0,
            'hydration': selected_date_reports.aggregate(avg=Avg('hydration'))['avg'] or 0,
        }
        
        # Find lowest and best categories
        metric_names = {
            'sleep_quality': 'Sleep',
            'energy_fatigue': 'Energy',
            'muscle_soreness': 'Soreness',
            'mood_stress': 'Mood',
            'motivation': 'Motivation',
            'nutrition_quality': 'Nutrition',
            'hydration': 'Hydration'
        }
        
        lowest_metric = min(metric_averages.items(), key=lambda x: x[1])
        best_metric = max(metric_averages.items(), key=lambda x: x[1])
        
        # Prepare all metric averages for insights
        insights = {
            'metrics': [
                {
                    'name': 'Sleep',
                    'score': round(metric_averages['sleep_quality']),
                    'key': 'sleep_quality'
                },
                {
                    'name': 'Energy',
                    'score': round(metric_averages['energy_fatigue']),
                    'key': 'energy_fatigue'
                },
                {
                    'name': 'Soreness',
                    'score': round(metric_averages['muscle_soreness']),
                    'key': 'muscle_soreness'
                },
                {
                    'name': 'Mood',
                    'score': round(metric_averages['mood_stress']),
                    'key': 'mood_stress'
                },
                {
                    'name': 'Motivation',
                    'score': round(metric_averages['motivation']),
                    'key': 'motivation'
                },
                {
                    'name': 'Nutrition',
                    'score': round(metric_averages['nutrition_quality']),
                    'key': 'nutrition_quality'
                },
                {
                    'name': 'Hydration',
                    'score': round(metric_averages['hydration']),
                    'key': 'hydration'
                }
            ]
        }
    else:
        insights = {
            'metrics': []
        }
    
    # Compute simple compliance: % of athletes who submitted today
    total_athletes = team_athletes.count()
    submitted_count = selected_date_reports.count()
    compliance_pct = round((submitted_count / total_athletes) * 100) if total_athletes > 0 else 0

    context = {
        'team': coach_team,
        'selected_date': selected_date,
        'prev_date': prev_date,
        'next_date': next_date,
        'day_tag': (tag_obj.id if tag_obj else None),
        'day_tag_display': day_tag_display,
        'squad_data': squad_data,
        'today_team_avg': today_team_avg,
        'historic_team_avg': historic_team_avg,
        'target_readiness': coach_team.target_readiness,
        'insights': insights,
        'has_data': selected_date_reports.exists(),
        # summary chips
        'target_range_display': target_range_display,
        'range_min': range_min,
        'range_max': range_max,
        'num_above_target': num_above_target,
        'num_in_target': num_in_target,
        'num_below_target': num_below_target,
        'compliance_pct': compliance_pct,
        'avg_status_class': avg_status_class,
    }
    
    return render(request, 'core/coach_dashboard.html', context)


@login_required
def athlete_detail(request, athlete_id):
    """
    Detailed view of an individual athlete's readiness history.
    """
    # Check if user is a coach
    try:
        if request.user.profile.role != Profile.Role.COACH:
            messages.warning(request, "Access denied. Coach access required.")
            return redirect('core:home')
    except Profile.DoesNotExist:
        messages.error(request, "Your profile is not set up. Please contact your administrator.")
        return redirect('logout')
    
    # Get the athlete
    athlete = get_object_or_404(User, id=athlete_id, profile__role=Profile.Role.ATHLETE)
    
    # Check if athlete is on the same team as coach
    if athlete.profile.team != request.user.profile.team:
        messages.warning(request, "Access denied. You can only view athletes from your team.")
        return redirect('core:coach_dashboard')
    
    # Get athlete's reports (last 30 days)
    thirty_days_ago = timezone.now().date() - timedelta(days=29)
    reports = ReadinessReport.objects.filter(
        athlete=athlete,
        date_created__gte=thirty_days_ago
    ).order_by('-date_created')
    
    # Calculate averages for each metric
    if reports.exists():
        metric_averages = {
            'sleep_quality': round(reports.aggregate(avg=Avg('sleep_quality'))['avg'] or 0, 1),
            'energy_fatigue': round(reports.aggregate(avg=Avg('energy_fatigue'))['avg'] or 0, 1),
            'muscle_soreness': round(reports.aggregate(avg=Avg('muscle_soreness'))['avg'] or 0, 1),
            'mood_stress': round(reports.aggregate(avg=Avg('mood_stress'))['avg'] or 0, 1),
            'motivation': round(reports.aggregate(avg=Avg('motivation'))['avg'] or 0, 1),
            'nutrition_quality': round(reports.aggregate(avg=Avg('nutrition_quality'))['avg'] or 0, 1),
            'hydration': round(reports.aggregate(avg=Avg('hydration'))['avg'] or 0, 1),
            'readiness_score': round(reports.aggregate(avg=Avg('readiness_score'))['avg'] or 0, 1),
        }
    else:
        metric_averages = None
    
    context = {
        'athlete': athlete,
        'reports': reports,
        'metric_averages': metric_averages,
    }
    
    return render(request, 'core/athlete_detail.html', context)


@login_required
def team_schedule_settings(request):
    """
    View for coaches to set their team's weekly schedule using a calendar interface.
    """
    # Check if user is a coach
    try:
        if request.user.profile.role != Profile.Role.COACH:
            messages.warning(request, "Access denied. Coach access required.")
            return redirect('core:home')
    except Profile.DoesNotExist:
        messages.error(request, "Your profile is not set up. Please contact your administrator.")
        return redirect('logout')
    
    # Get coach's team
    coach_team = request.user.profile.team
    if not coach_team:
        messages.warning(request, "You are not assigned to a team.")
        return redirect('core:coach_dashboard')
    
    # Get or create team schedule
    team_schedule, created = TeamSchedule.objects.get_or_create(team=coach_team)
    
    # Handle AJAX requests for updating individual days and quick actions
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        import json
        data = json.loads(request.body)
        date_str = data.get('date')
        day_tag = data.get('day_tag')
        action = data.get('action')
        month_param = data.get('month')
        
        if action == 'set_all_weekdays':
            # Set all weekdays to the same tag
            weekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
            for weekday in weekdays:
                team_schedule.set_day_tag(weekday, int(day_tag))
            return JsonResponse({'success': True, 'message': f'All weekdays set to {day_tag}'})
        
        elif action == 'copy_last_month':
            # Copy previous month's tags into the current month
            from datetime import datetime, timedelta
            import calendar
            try:
                if month_param:
                    current_year, current_month = map(int, month_param.split('-'))
                else:
                    today = timezone.now().date()
                    current_year = today.year
                    current_month = today.month
                first_day = datetime(current_year, current_month, 1).date()
                prev_month_year = current_year if current_month > 1 else current_year - 1
                prev_month = current_month - 1 if current_month > 1 else 12
                prev_first = datetime(prev_month_year, prev_month, 1).date()
                prev_last = datetime(prev_month_year, prev_month, calendar.monthrange(prev_month_year, prev_month)[1]).date()
                # Build mapping of (weekday, occurrence_index) -> tag_id from previous month
                # Also keep track of last occurrence per weekday for fallback
                prev_map = {}
                weekday_counts = {w: 0 for w in ['Mon','Tue','Wed','Thu','Fri','Sat','Sun']}
                last_occ_by_weekday = {w: 0 for w in ['Mon','Tue','Wed','Thu','Fri','Sat','Sun']}
                d = prev_first
                while d <= prev_last:
                    weekday = d.strftime('%a')
                    weekday_counts[weekday] += 1
                    occ = weekday_counts[weekday]
                    prev_tag = team_schedule.get_day_tag(d)
                    prev_map[(weekday, occ)] = prev_tag.id if prev_tag else None
                    last_occ_by_weekday[weekday] = occ
                    d += timedelta(days=1)

                # Apply mapping to current month using weekday occurrence alignment
                current_last = datetime(current_year, current_month, calendar.monthrange(current_year, current_month)[1]).date()
                cur_counts = {w: 0 for w in ['Mon','Tue','Wed','Thu','Fri','Sat','Sun']}
                d = first_day
                while d <= current_last:
                    weekday = d.strftime('%a')
                    cur_counts[weekday] += 1
                    occ = cur_counts[weekday]
                    tag_id = prev_map.get((weekday, occ))
                    if tag_id is None:
                        # Fallback: use the last available occurrence from previous month for this weekday
                        last_occ = last_occ_by_weekday.get(weekday, 0)
                        if last_occ:
                            tag_id = prev_map.get((weekday, last_occ))
                    team_schedule.set_day_tag(d, tag_id)
                    d += timedelta(days=1)
                return JsonResponse({'success': True, 'message': 'Copied last month\'s schedule.'})
            except Exception as e:
                return JsonResponse({'success': False, 'message': str(e)})

        elif action == 'clear_month':
            from datetime import datetime, timedelta
            import calendar
            try:
                if month_param:
                    current_year, current_month = map(int, month_param.split('-'))
                else:
                    today = timezone.now().date()
                    current_year = today.year
                    current_month = today.month
                first_day = datetime(current_year, current_month, 1).date()
                last_day = datetime(current_year, current_month, calendar.monthrange(current_year, current_month)[1]).date()
                d = first_day
                while d <= last_day:
                    team_schedule.set_day_tag(d, None)
                    d += timedelta(days=1)
                return JsonResponse({'success': True, 'message': 'Cleared all tags for this month.'})
            except Exception as e:
                return JsonResponse({'success': False, 'message': str(e)})

        elif date_str is not None:
            # Set a specific date
            from datetime import datetime
            try:
                date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                # Allow clearing with empty/None values
                value = None
                if day_tag not in (None, "", "null", "None"):
                    value = int(day_tag)
                team_schedule.set_day_tag(date_obj, value)
                return JsonResponse({'success': True, 'message': f'{date_str} updated'})
            except ValueError:
                return JsonResponse({'success': False, 'message': 'Invalid date format'})
        else:
            return JsonResponse({'success': False, 'message': 'Invalid data'})
    
    # Get available day tags (team-owned)
    day_tags = TeamTag.objects.filter(team=coach_team)
    
    # Generate calendar data for selected month (supports ?month=YYYY-MM)
    from datetime import datetime, timedelta
    import calendar
    
    today = timezone.now().date()
    month_param = request.GET.get('month')
    if month_param:
        try:
            current_year, current_month = map(int, month_param.split('-'))
        except (ValueError, TypeError):
            current_month = today.month
            current_year = today.year
    else:
        current_month = today.month
        current_year = today.year
    
    # Get the first day of the month and number of days
    first_day = datetime(current_year, current_month, 1).date()
    last_day = datetime(current_year, current_month, calendar.monthrange(current_year, current_month)[1]).date()
    
    # Pre-compute team daily average readiness for the month
    team_athletes = User.objects.filter(profile__team=coach_team, profile__role=Profile.Role.ATHLETE)
    daily_avgs_qs = ReadinessReport.objects.filter(
        athlete__in=team_athletes,
        date_created__gte=first_day,
        date_created__lte=last_day
    ).values('date_created').annotate(avg_score=Avg('readiness_score'))
    date_to_avg = {entry['date_created']: round(entry['avg_score']) for entry in daily_avgs_qs}

    # Generate calendar grid
    calendar_data = []
    current_date = first_day
    
    # Add empty cells for days before the first day of the month
    start_weekday = first_day.weekday()  # 0 = Monday, 6 = Sunday
    for i in range(start_weekday):
        calendar_data.append({'date': None, 'day': None, 'tag': None, 'is_current_month': False})
    
    # Add all days of the month
    while current_date <= last_day:
        weekday = current_date.strftime('%a')
        tag = team_schedule.get_day_tag(current_date)  # Use date object to check for overrides
        avg_score = date_to_avg.get(current_date)
        calendar_data.append({
            'date': current_date,
            'day': current_date.day,
            'weekday': weekday,
            'tag_id': tag.id if tag else None,
            'tag_name': tag.name if tag else None,
            'tag_color': tag.color if tag else '#6c757d',
            'range_min': int(tag.target_min) if getattr(tag, 'target_min', None) is not None else None,
            'range_max': int(tag.target_max) if getattr(tag, 'target_max', None) is not None else None,
            'is_current_month': True,
            'is_today': current_date == today,
            'date_str': current_date.strftime('%Y-%m-%d'),
            'avg_score': avg_score
        })
        current_date += timedelta(days=1)
    
    # Pad the end of the month to complete the last week
    while len(calendar_data) % 7 != 0:
        calendar_data.append({'date': None, 'day': None, 'tag_id': None, 'is_current_month': False})
    
    # Prev/next month for navigation
    if current_month == 1:
        prev_month_date = datetime(current_year - 1, 12, 1).date()
    else:
        prev_month_date = datetime(current_year, current_month - 1, 1).date()
    if current_month == 12:
        next_month_date = datetime(current_year + 1, 1, 1).date()
    else:
        next_month_date = datetime(current_year, current_month + 1, 1).date()

    context = {
        'team': coach_team,
        'team_schedule': team_schedule,
        'day_tags': day_tags,
        'calendar_data': calendar_data,
        'current_month': current_month,
        'current_year': current_year,
        'month_name': calendar.month_name[current_month],
        'prev_month': prev_month_date,
        'next_month': next_month_date,
    }
    
    return render(request, 'core/team_schedule_calendar.html', context)


@login_required
def player_metrics_ajax(request, athlete_id):
    """
    AJAX endpoint to fetch individual player metrics for a specific date.
    """
    # Check if user is a coach
    try:
        if request.user.profile.role != Profile.Role.COACH:
            return JsonResponse({'success': False, 'message': 'Access denied'})
    except Profile.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Profile not found'})
    
    # Get the athlete
    try:
        athlete = User.objects.get(id=athlete_id, profile__role=Profile.Role.ATHLETE)
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Athlete not found'})
    
    # Check if athlete is on the same team as coach
    if athlete.profile.team != request.user.profile.team:
        return JsonResponse({'success': False, 'message': 'Access denied'})
    
    # Get date from URL parameter (default to today)
    date_str = request.GET.get('date')
    if date_str:
        try:
            selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            selected_date = timezone.now().date()
    else:
        selected_date = timezone.now().date()
    
    # Get athlete's report for the selected date
    try:
        report = ReadinessReport.objects.get(athlete=athlete, date_created=selected_date)
        
        # Prepare metrics data
        metrics = [
            {
                'name': 'Sleep',
                'score': round(report.sleep_quality),
                'key': 'sleep_quality'
            },
            {
                'name': 'Energy',
                'score': round(report.energy_fatigue),
                'key': 'energy_fatigue'
            },
            {
                'name': 'Soreness',
                'score': round(report.muscle_soreness),
                'key': 'muscle_soreness'
            },
            {
                'name': 'Mood',
                'score': round(report.mood_stress),
                'key': 'mood_stress'
            },
            {
                'name': 'Motivation',
                'score': round(report.motivation),
                'key': 'motivation'
            },
            {
                'name': 'Nutrition',
                'score': round(report.nutrition_quality),
                'key': 'nutrition_quality'
            },
            {
                'name': 'Hydration',
                'score': round(report.hydration),
                'key': 'hydration'
            }
        ]
        
        return JsonResponse({
            'success': True,
            'metrics': metrics,
            'date': selected_date.strftime('%Y-%m-%d')
        })
        
    except ReadinessReport.DoesNotExist:
        return JsonResponse({
            'success': False, 
            'message': f'No data available for {athlete.get_full_name() or athlete.username} on {selected_date.strftime("%B %d, %Y")}'
        })


@login_required
def player_dashboard(request):
    """
    Minimal, mobile-first Player Overview: today circle, 7-day sparkline, streak, and two insight chips.
    """
    # Only athletes
    try:
        if request.user.profile.role != Profile.Role.ATHLETE:
            messages.warning(request, "Access denied. Athlete only.")
            return redirect('core:home')
    except Profile.DoesNotExist:
        messages.error(request, "Your profile is not set up. Please contact your administrator.")
        return redirect('logout')

    today = timezone.now().date()

    # Weekly range handling (Mon-Sun)
    from datetime import timedelta
    week_start_param = request.GET.get('week_start')
    if week_start_param:
        try:
            selected_week_start = datetime.strptime(week_start_param, '%Y-%m-%d').date()
        except ValueError:
            # fallback to current week start
            selected_week_start = today - timedelta(days=today.weekday())
    else:
        # default to current week start (Monday)
        selected_week_start = today - timedelta(days=today.weekday())
    selected_week_end = selected_week_start + timedelta(days=6)

    prev_week_start = selected_week_start - timedelta(days=7)
    next_week_start = selected_week_start + timedelta(days=7)

    # Label like "Oct 20 – Oct 26, 2025" (include year on end only)
    week_label = f"{selected_week_start.strftime('%b %d')} – {selected_week_end.strftime('%b %d, %Y')}"

    # Build series for selected week (oldest→newest)
    start = selected_week_start
    reports = ReadinessReport.objects.filter(
        athlete=request.user,
        date_created__gte=start,
        date_created__lte=selected_week_end
    ).values('date_created', 'readiness_score')
    date_to_score = {r['date_created']: r['readiness_score'] for r in reports}
    series = []
    for i in range(7):
        d = start + timedelta(days=i)
        series.append({
            'date': d,
            'label': d.strftime('%a'),
            'score': date_to_score.get(d)
        })

    # Today
    today_report = ReadinessReport.objects.filter(athlete=request.user, date_created=today).first()
    today_score = today_report.readiness_score if today_report else None

    # 7-day stats
    valid_scores = [s['score'] for s in series if s['score'] is not None]
    seven_day_avg = round(sum(valid_scores) / len(valid_scores)) if valid_scores else 0
    seven_day_min = min(valid_scores) if valid_scores else None
    seven_day_max = max(valid_scores) if valid_scores else None

    # Streak (consecutive days with a report up to today)
    streak = 0
    for i in range(30):
        d = today - timedelta(days=i)
        if ReadinessReport.objects.filter(athlete=request.user, date_created=d).exists():
            streak += 1
        else:
            break

    # Insights chips (best and needs attention) from today if available
    best_metric = None
    attention_metric = None
    if today_report:
        metric_map = {
            'Sleep': today_report.sleep_quality,
            'Energy': today_report.energy_fatigue,
            'Soreness': today_report.muscle_soreness,
            'Mood': today_report.mood_stress,
            'Motivation': today_report.motivation,
            'Nutrition': today_report.nutrition_quality,
            'Hydration': today_report.hydration,
        }
        items = list(metric_map.items())
        best_metric = max(items, key=lambda x: x[1])
        attention_metric = min(items, key=lambda x: x[1])

    # Recent days table (selected week)
    recent_rows = []
    # Try to read player's team schedule and day tags for target midpoint
    team = getattr(getattr(request.user, 'profile', None), 'team', None)
    schedule = None
    if team:
        try:
            schedule = TeamSchedule.objects.get(team=team)
        except TeamSchedule.DoesNotExist:
            schedule = TeamSchedule.objects.create(team=team)

    # Helper to get tag target (returns midpoint of range)
    def target_for_tag(tag_obj) -> int:
        if not tag_obj:
            return 70
        if hasattr(tag_obj, 'target') and tag_obj.target is not None:
            return int(tag_obj.target)
        if hasattr(tag_obj, 'target_min') and hasattr(tag_obj, 'target_max'):
            try:
                return round((int(tag_obj.target_min) + int(tag_obj.target_max)) / 2)
            except Exception:
                return 70
        return 70

    def target_range_for_tag(tag_obj, default_midpoint: int = 70) -> tuple[int, int]:
        try:
            if tag_obj and getattr(tag_obj, 'target_min', None) is not None and getattr(tag_obj, 'target_max', None) is not None:
                return int(tag_obj.target_min), int(tag_obj.target_max)
        except Exception:
            pass
        midpoint = default_midpoint
        return max(0, midpoint - 5), min(100, midpoint + 5)

    # Performance: prefetch TeamTag objects referenced in the week to avoid per-day queries
    tag_map = {}
    if schedule:
        from datetime import timedelta as _td
        needed_ids = set()
        for i in range(7):
            d = start + _td(days=i)
            tag_id = schedule.get_day_tag_id(d)
            if tag_id:
                needed_ids.add(int(tag_id))
        if needed_ids:
            tag_map = {t.id: t for t in TeamTag.objects.filter(team=team, id__in=list(needed_ids))}

    for i in range(7):
        d = start + timedelta(days=i)
        # day type
        if schedule:
            tag_id = schedule.get_day_tag_id(d)
            tag_obj = tag_map.get(int(tag_id)) if tag_id else None
        else:
            tag_obj = None
        tag_display = tag_obj.name if tag_obj else '—'
        score = date_to_score.get(d)
        target = target_for_tag(tag_obj)
        team_target = int(getattr(team, 'target_readiness', 70) or 70)
        rmin, rmax = target_range_for_tag(tag_obj, default_midpoint=team_target)
        status = None
        if score is not None:
            status = 'above' if score > rmax else ('in' if rmin <= score <= rmax else 'below')

        recent_rows.append({
            'date': d,
            'day_label': d.strftime('%a %d'),
            'date_str': d.strftime('%Y-%m-%d'),
            'type': tag_display,
            'score': score,
            'target': target,
            'range_min': rmin,
            'range_max': rmax,
            'status': status,
        })

    # Today's tag for actions header
    today_tag_obj = schedule.get_day_tag(today) if schedule else None
    today_tag_name = today_tag_obj.name if today_tag_obj else '—'

    # Monthly overview for selected month
    import calendar
    month_param = request.GET.get('month')  # format YYYY-MM
    if month_param:
        try:
            current_year, current_month = map(int, month_param.split('-'))
        except (ValueError, TypeError):
            current_year = today.year
            current_month = today.month
    else:
        current_year = today.year
        current_month = today.month
    first_day = datetime(current_year, current_month, 1).date()
    days_in_month = calendar.monthrange(current_year, current_month)[1]
    month_cells = []  # list of dicts with optional date
    # leading blanks (0=Mon)
    start_weekday = first_day.weekday()
    for _ in range(start_weekday):
        month_cells.append({'date': None})
    # fill days
    for day in range(1, days_in_month + 1):
        d = datetime(current_year, current_month, day).date()
        score = ReadinessReport.objects.filter(athlete=request.user, date_created=d).values_list('readiness_score', flat=True).first()
        # compute range/status if schedule present
        if schedule:
            tag_obj = schedule.get_day_tag(d)
        else:
            tag_obj = None
        team_target = int(getattr(team, 'target_readiness', 70) or 70)
        rmin, rmax = target_range_for_tag(tag_obj, default_midpoint=team_target)
        status = None
        if score is not None:
            status = 'above' if score > rmax else ('in' if rmin <= score <= rmax else 'below')

        month_cells.append({
            'date': d,
            'day': day,
            'date_str': d.strftime('%Y-%m-%d'),
            'score': score,
            'range_min': rmin,
            'range_max': rmax,
            'status': status,
        })
    # trailing blanks to complete last week
    while len(month_cells) % 7 != 0:
        month_cells.append({'date': None})

    # Compute prev/next months as date objects (use day=1)
    if current_month == 1:
        prev_month_date = datetime(current_year - 1, 12, 1).date()
    else:
        prev_month_date = datetime(current_year, current_month - 1, 1).date()
    if current_month == 12:
        next_month_date = datetime(current_year + 1, 1, 1).date()
    else:
        next_month_date = datetime(current_year, current_month + 1, 1).date()

    # Quick-jump anchors
    current_week_start = today - timedelta(days=today.weekday())
    current_month_str = today.strftime('%Y-%m')

    context = {
        'today_score': today_score,
        'seven_day_avg': seven_day_avg,
        'seven_day_min': seven_day_min,
        'seven_day_max': seven_day_max,
        'series': series,
        'streak': streak,
        'best_metric': best_metric,      # tuple (name, score) or None
        'attention_metric': attention_metric,
        'has_today': today_report is not None,
        # Actions header
        'today_has_report': today_report is not None,
        'today_date_str': today.strftime('%Y-%m-%d'),
        'today_tag_name': today_tag_name,
        'current_status': getattr(request.user.profile, 'current_status', None),
        'status_note': getattr(request.user.profile, 'status_note', ''),
        'status_updated_at': getattr(request.user.profile, 'status_updated_at', None),
        'recent_rows': recent_rows,
        'month_cells': month_cells,
        'current_month_name': calendar.month_name[current_month],
        'current_year': current_year,
        # Weekly nav
        'week_label': week_label,
        'prev_week_start': prev_week_start,
        'next_week_start': next_week_start,
        'current_week_start': current_week_start,
        # Monthly nav
        'prev_month': prev_month_date,
        'next_month': next_month_date,
        'current_month_str': current_month_str,
        # Empty states
        'has_schedule': schedule is not None,
        'has_week_data': any(v is not None for v in date_to_score.values()),
    }

    return render(request, 'core/player_dashboard.html', context)


@login_required
def player_metrics_self_ajax(request):
    """
    AJAX: return the logged-in athlete's metrics for a given date.
    """
    try:
        if request.user.profile.role != Profile.Role.ATHLETE:
            return JsonResponse({'success': False, 'message': 'Access denied'})
    except Profile.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Profile not found'})

    date_str = request.GET.get('date')
    try:
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else timezone.now().date()
    except ValueError:
        selected_date = timezone.now().date()

    try:
        report = ReadinessReport.objects.get(athlete=request.user, date_created=selected_date)
        metrics = [
            {'name': 'Sleep', 'score': round(report.sleep_quality), 'key': 'sleep_quality'},
            {'name': 'Energy', 'score': round(report.energy_fatigue), 'key': 'energy_fatigue'},
            {'name': 'Soreness', 'score': round(report.muscle_soreness), 'key': 'muscle_soreness'},
            {'name': 'Mood', 'score': round(report.mood_stress), 'key': 'mood_stress'},
            {'name': 'Motivation', 'score': round(report.motivation), 'key': 'motivation'},
            {'name': 'Nutrition', 'score': round(report.nutrition_quality), 'key': 'nutrition_quality'},
            {'name': 'Hydration', 'score': round(report.hydration), 'key': 'hydration'},
        ]
        return JsonResponse({'success': True, 'metrics': metrics, 'date': selected_date.strftime('%Y-%m-%d')})
    except ReadinessReport.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'No report for this day'})


@login_required
def player_status(request):
    """
    GET: return the player's current status payload. Athlete-only.
    """
    try:
        if request.user.profile.role != Profile.Role.ATHLETE:
            return JsonResponse({'success': False, 'message': 'Access denied'})
    except Profile.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Profile not found'})

    p = request.user.profile
    return JsonResponse({
        'success': True,
        'current_status': p.current_status,
        'status_note': p.status_note or '',
        'status_updated_at': p.status_updated_at.strftime('%Y-%m-%d %H:%M') if p.status_updated_at else None,
    })


@login_required
def player_set_status(request):
    """
    POST: set the player's current status. Payload: {status, note?}
    Athlete-only.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'POST required'}, status=405)

    try:
        if request.user.profile.role != Profile.Role.ATHLETE:
            return JsonResponse({'success': False, 'message': 'Access denied'}, status=403)
    except Profile.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Profile not found'}, status=404)

    try:
        import json as _json
        data = _json.loads(request.body.decode('utf-8')) if request.body else request.POST
    except Exception:
        data = request.POST

    status_value = data.get('status')
    note = data.get('note', '')

    valid = [choice[0] for choice in Profile.PlayerStatus.choices]
    if status_value not in valid:
        return JsonResponse({'success': False, 'message': 'Invalid status'}, status=400)
    if note and len(note) > 140:
        return JsonResponse({'success': False, 'message': 'Note too long (max 140)'}, status=400)

    p = request.user.profile
    p.current_status = status_value
    p.status_note = note
    p.save()

    return JsonResponse({
        'success': True,
        'current_status': p.current_status,
        'status_note': p.status_note or '',
        'status_updated_at': p.status_updated_at.strftime('%Y-%m-%d %H:%M') if p.status_updated_at else None,
    })

@login_required
def player_week_partial(request):
    """
    Return the Weekly Overview HTML fragment for the given week_start.
    """
    try:
        if request.user.profile.role != Profile.Role.ATHLETE:
            return JsonResponse({'success': False, 'message': 'Access denied'})
    except Profile.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Profile not found'})

    today = timezone.now().date()
    week_start_param = request.GET.get('week_start')
    from datetime import timedelta
    if week_start_param:
        try:
            selected_week_start = datetime.strptime(week_start_param, '%Y-%m-%d').date()
        except ValueError:
            selected_week_start = today - timedelta(days=today.weekday())
    else:
        selected_week_start = today - timedelta(days=today.weekday())
    selected_week_end = selected_week_start + timedelta(days=6)
    prev_week_start = selected_week_start - timedelta(days=7)
    next_week_start = selected_week_start + timedelta(days=7)
    week_label = f"{selected_week_start.strftime('%b %d')} – {selected_week_end.strftime('%b %d, %Y')}"

    # Build recent_rows for this week
    team = getattr(getattr(request.user, 'profile', None), 'team', None)
    schedule = None
    if team:
        try:
            schedule = TeamSchedule.objects.get(team=team)
        except TeamSchedule.DoesNotExist:
            schedule = TeamSchedule.objects.create(team=team)

    def target_for_tag(tag_obj) -> int:
        if not tag_obj:
            return 70
        if hasattr(tag_obj, 'target') and tag_obj.target is not None:
            return int(tag_obj.target)
        if hasattr(tag_obj, 'target_min') and hasattr(tag_obj, 'target_max'):
            try:
                return round((int(tag_obj.target_min) + int(tag_obj.target_max)) / 2)
            except Exception:
                return 70
        return 70

    reports = ReadinessReport.objects.filter(
        athlete=request.user,
        date_created__gte=selected_week_start,
        date_created__lte=selected_week_end
    ).values('date_created', 'readiness_score')
    date_to_score = {r['date_created']: r['readiness_score'] for r in reports}

    # Prefetch TeamTags used this week
    tag_map = {}
    if schedule:
        from datetime import timedelta as _td
        ids = set()
        for i in range(7):
            d = selected_week_start + _td(days=i)
            tid = schedule.get_day_tag_id(d)
            if tid:
                ids.add(int(tid))
        if ids:
            tag_map = {t.id: t for t in TeamTag.objects.filter(team=team, id__in=list(ids))}

    recent_rows = []
    for i in range(7):
        d = selected_week_start + timedelta(days=i)
        if schedule:
            tid = schedule.get_day_tag_id(d)
            tag_obj = tag_map.get(int(tid)) if tid else None
        else:
            tag_obj = None
        tag_display = tag_obj.name if tag_obj else '—'
        score = date_to_score.get(d)
        target = target_for_tag(tag_obj)
        recent_rows.append({
            'date': d,
            'day_label': d.strftime('%a %d'),
            'date_str': d.strftime('%Y-%m-%d'),
            'type': tag_display,
            'score': score,
            'target': target,
        })

    html = render_to_string('core/_player_week.html', {
        'week_label': week_label,
        'prev_week_start': prev_week_start,
        'next_week_start': next_week_start,
        'recent_rows': recent_rows,
    }, request=request)

    # Update URL to reflect current week_start
    return JsonResponse({'success': True, 'html': html})


@login_required
def player_month_partial(request):
    """
    Return the Monthly Overview HTML fragment for the given month (YYYY-MM).
    """
    try:
        if request.user.profile.role != Profile.Role.ATHLETE:
            return JsonResponse({'success': False, 'message': 'Access denied'})
    except Profile.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Profile not found'})

    today = timezone.now().date()
    import calendar
    month_param = request.GET.get('month')
    if month_param:
        try:
            current_year, current_month = map(int, month_param.split('-'))
        except (ValueError, TypeError):
            current_year = today.year
            current_month = today.month
    else:
        current_year = today.year
        current_month = today.month

    first_day = datetime(current_year, current_month, 1).date()
    days_in_month = calendar.monthrange(current_year, current_month)[1]

    month_cells = []
    start_weekday = first_day.weekday()
    for _ in range(start_weekday):
        month_cells.append({'date': None})
    for day in range(1, days_in_month + 1):
        d = datetime(current_year, current_month, day).date()
        score = ReadinessReport.objects.filter(athlete=request.user, date_created=d).values_list('readiness_score', flat=True).first()
        month_cells.append({
            'date': d,
            'day': day,
            'date_str': d.strftime('%Y-%m-%d'),
            'score': score,
        })
    while len(month_cells) % 7 != 0:
        month_cells.append({'date': None})

    if current_month == 1:
        prev_month_date = datetime(current_year - 1, 12, 1).date()
    else:
        prev_month_date = datetime(current_year, current_month - 1, 1).date()
    if current_month == 12:
        next_month_date = datetime(current_year + 1, 1, 1).date()
    else:
        next_month_date = datetime(current_year, current_month + 1, 1).date()

    html = render_to_string('core/_player_month.html', {
        'current_month_name': calendar.month_name[current_month],
        'current_year': current_year,
        'prev_month': prev_month_date,
        'next_month': next_month_date,
        'month_cells': month_cells,
    }, request=request)

    return JsonResponse({'success': True, 'html': html})


@login_required
def coach_player_dashboard(request, athlete_id):
    """
    Coach view of a specific athlete's Player Dashboard.
    """
    # Only coaches
    try:
        if request.user.profile.role != Profile.Role.COACH:
            messages.warning(request, "Access denied. Coach access required.")
            return redirect('core:home')
    except Profile.DoesNotExist:
        messages.error(request, "Your profile is not set up. Please contact your administrator.")
        return redirect('logout')

    athlete = get_object_or_404(User, id=athlete_id, profile__role=Profile.Role.ATHLETE)
    # same team check
    if athlete.profile.team != request.user.profile.team:
        messages.warning(request, "Access denied. You can only view athletes from your team.")
        return redirect('core:coach_dashboard')

    today = timezone.now().date()

    # Weekly range handling
    from datetime import timedelta
    week_start_param = request.GET.get('week_start')
    if week_start_param:
        try:
            selected_week_start = datetime.strptime(week_start_param, '%Y-%m-%d').date()
        except ValueError:
            selected_week_start = today - timedelta(days=today.weekday())
    else:
        selected_week_start = today - timedelta(days=today.weekday())
    selected_week_end = selected_week_start + timedelta(days=6)
    prev_week_start = selected_week_start - timedelta(days=7)
    next_week_start = selected_week_start + timedelta(days=7)
    week_label = f"{selected_week_start.strftime('%b %d')} – {selected_week_end.strftime('%b %d, %Y')}"

    # Build series for selected week
    start = selected_week_start
    reports = ReadinessReport.objects.filter(
        athlete=athlete,
        date_created__gte=start,
        date_created__lte=selected_week_end
    ).values('date_created', 'readiness_score')
    date_to_score = {r['date_created']: r['readiness_score'] for r in reports}

    series = []
    for i in range(7):
        d = start + timedelta(days=i)
        series.append({'date': d, 'label': d.strftime('%a'), 'score': date_to_score.get(d)})

    # Today
    today_report = ReadinessReport.objects.filter(athlete=athlete, date_created=today).first()
    today_score = today_report.readiness_score if today_report else None

    # 7-day stats
    valid_scores = [s['score'] for s in series if s['score'] is not None]
    seven_day_avg = round(sum(valid_scores) / len(valid_scores)) if valid_scores else 0
    seven_day_min = min(valid_scores) if valid_scores else None
    seven_day_max = max(valid_scores) if valid_scores else None

    # Recent rows (selected week)
    schedule = None
    team = athlete.profile.team
    if team:
        try:
            schedule = TeamSchedule.objects.get(team=team)
        except TeamSchedule.DoesNotExist:
            schedule = TeamSchedule.objects.create(team=team)

    # Today's tag for actions header
    today_tag_obj = schedule.get_day_tag(today) if schedule else None
    today_tag_name = today_tag_obj.name if today_tag_obj else '—'

    def target_for_tag(tag_obj) -> int:
        if not tag_obj:
            return 70
        if hasattr(tag_obj, 'target') and tag_obj.target is not None:
            return int(tag_obj.target)
        if hasattr(tag_obj, 'target_min') and hasattr(tag_obj, 'target_max'):
            try:
                return round((int(tag_obj.target_min) + int(tag_obj.target_max)) / 2)
            except Exception:
                return 70
        return 70

    recent_rows = []
    for i in range(7):
        d = start + timedelta(days=i)
        tag_obj = schedule.get_day_tag(d) if schedule else None
        tag_display = tag_obj.name if tag_obj else '—'
        score = date_to_score.get(d)
        target = target_for_tag(tag_obj)
        recent_rows.append({
            'date': d,
            'day_label': d.strftime('%a %d'),
            'date_str': d.strftime('%Y-%m-%d'),
            'type': tag_display,
            'score': score,
            'target': target,
        })

    # Monthly overview for selected month
    import calendar
    month_param = request.GET.get('month')
    if month_param:
        try:
            current_year, current_month = map(int, month_param.split('-'))
        except (ValueError, TypeError):
            current_year = today.year
            current_month = today.month
    else:
        current_year = today.year
        current_month = today.month

    first_day = datetime(current_year, current_month, 1).date()
    days_in_month = calendar.monthrange(current_year, current_month)[1]
    month_cells = []
    start_weekday = first_day.weekday()
    for _ in range(start_weekday):
        month_cells.append({'date': None})
    for day in range(1, days_in_month + 1):
        d = datetime(current_year, current_month, day).date()
        score = ReadinessReport.objects.filter(athlete=athlete, date_created=d).values_list('readiness_score', flat=True).first()
        month_cells.append({'date': d, 'day': day, 'date_str': d.strftime('%Y-%m-%d'), 'score': score})
    while len(month_cells) % 7 != 0:
        month_cells.append({'date': None})

    if current_month == 1:
        prev_month_date = datetime(current_year - 1, 12, 1).date()
    else:
        prev_month_date = datetime(current_year, current_month - 1, 1).date()
    if current_month == 12:
        next_month_date = datetime(current_year + 1, 1, 1).date()
    else:
        next_month_date = datetime(current_year, current_month + 1, 1).date()

    context = {
        'today_score': today_score,
        'seven_day_avg': seven_day_avg,
        'seven_day_min': seven_day_min,
        'seven_day_max': seven_day_max,
        'series': series,
        'streak': 0,  # not used in current template
        'has_today': today_report is not None,
        # Actions header
        'today_has_report': today_report is not None,
        'today_date_str': today.strftime('%Y-%m-%d'),
        'today_tag_name': today_tag_name,
        'current_status': getattr(athlete.profile, 'current_status', None),
        'status_note': getattr(athlete.profile, 'status_note', ''),
        'status_updated_at': getattr(athlete.profile, 'status_updated_at', None),
        'recent_rows': recent_rows,
        'month_cells': month_cells,
        'current_month_name': calendar.month_name[current_month],
        'current_year': current_year,
        'week_label': week_label,
        'prev_week_start': prev_week_start,
        'next_week_start': next_week_start,
        'prev_month': prev_month_date,
        'next_month': next_month_date,
        # dynamic endpoints for JS
        'metrics_base_url': reverse('core:player_metrics_ajax', args=[athlete.id]),
        'week_partial_url': reverse('core:coach_player_week_partial', args=[athlete.id]),
        'month_partial_url': reverse('core:coach_player_month_partial', args=[athlete.id]),
        'back_url': reverse('core:coach_dashboard'),
        'athlete_name': athlete.get_full_name() or athlete.username,
    }

    return render(request, 'core/player_dashboard.html', context)


@login_required
def coach_player_week_partial(request, athlete_id):
    # Only coach and same team
    try:
        if request.user.profile.role != Profile.Role.COACH:
            return JsonResponse({'success': False, 'message': 'Access denied'})
    except Profile.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Profile not found'})

    athlete = get_object_or_404(User, id=athlete_id, profile__role=Profile.Role.ATHLETE)
    if athlete.profile.team != request.user.profile.team:
        return JsonResponse({'success': False, 'message': 'Access denied'})

    today = timezone.now().date()
    week_start_param = request.GET.get('week_start')
    from datetime import timedelta
    if week_start_param:
        try:
            selected_week_start = datetime.strptime(week_start_param, '%Y-%m-%d').date()
        except ValueError:
            selected_week_start = today - timedelta(days=today.weekday())
    else:
        selected_week_start = today - timedelta(days=today.weekday())
    selected_week_end = selected_week_start + timedelta(days=6)
    prev_week_start = selected_week_start - timedelta(days=7)
    next_week_start = selected_week_start + timedelta(days=7)
    week_label = f"{selected_week_start.strftime('%b %d')} – {selected_week_end.strftime('%b %d, %Y')}"

    team = athlete.profile.team
    try:
        schedule = TeamSchedule.objects.get(team=team)
    except TeamSchedule.DoesNotExist:
        schedule = TeamSchedule.objects.create(team=team)

    def target_for_tag(tag_obj) -> int:
        if not tag_obj:
            return 70
        # Prefer explicit midpoint of TeamTag range when available
        if hasattr(tag_obj, 'target_min') and hasattr(tag_obj, 'target_max'):
            try:
                return round((int(tag_obj.target_min) + int(tag_obj.target_max)) / 2)
            except Exception:
                return 70
        return 70

    reports = ReadinessReport.objects.filter(
        athlete=athlete,
        date_created__gte=selected_week_start,
        date_created__lte=selected_week_end
    ).values('date_created', 'readiness_score')
    date_to_score = {r['date_created']: r['readiness_score'] for r in reports}

    recent_rows = []
    for i in range(7):
        d = selected_week_start + timedelta(days=i)
        tag_obj = schedule.get_day_tag(d) if schedule else None
        tag_display = tag_obj.name if tag_obj else '—'
        score = date_to_score.get(d)
        target = target_for_tag(tag_obj)
        recent_rows.append({
            'date': d,
            'day_label': d.strftime('%a %d'),
            'date_str': d.strftime('%Y-%m-%d'),
            'type': tag_display,
            'score': score,
            'target': target,
        })

    html = render_to_string('core/_player_week.html', {
        'week_label': week_label,
        'prev_week_start': prev_week_start,
        'next_week_start': next_week_start,
        'recent_rows': recent_rows,
    }, request=request)
    return JsonResponse({'success': True, 'html': html})


@login_required
def coach_player_month_partial(request, athlete_id):
    try:
        if request.user.profile.role != Profile.Role.COACH:
            return JsonResponse({'success': False, 'message': 'Access denied'})
    except Profile.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Profile not found'})

    athlete = get_object_or_404(User, id=athlete_id, profile__role=Profile.Role.ATHLETE)
    if athlete.profile.team != request.user.profile.team:
        return JsonResponse({'success': False, 'message': 'Access denied'})

    today = timezone.now().date()
    import calendar
    month_param = request.GET.get('month')
    if month_param:
        try:
            current_year, current_month = map(int, month_param.split('-'))
        except (ValueError, TypeError):
            current_year = today.year
            current_month = today.month
    else:
        current_year = today.year
        current_month = today.month

    first_day = datetime(current_year, current_month, 1).date()
    days_in_month = calendar.monthrange(current_year, current_month)[1]
    month_cells = []
    start_weekday = first_day.weekday()
    for _ in range(start_weekday):
        month_cells.append({'date': None})
    for day in range(1, days_in_month + 1):
        d = datetime(current_year, current_month, day).date()
        score = ReadinessReport.objects.filter(athlete=athlete, date_created=d).values_list('readiness_score', flat=True).first()
        month_cells.append({'date': d, 'day': day, 'date_str': d.strftime('%Y-%m-%d'), 'score': score})
    while len(month_cells) % 7 != 0:
        month_cells.append({'date': None})

    if current_month == 1:
        prev_month_date = datetime(current_year - 1, 12, 1).date()
    else:
        prev_month_date = datetime(current_year, current_month - 1, 1).date()
    if current_month == 12:
        next_month_date = datetime(current_year + 1, 1, 1).date()
    else:
        next_month_date = datetime(current_year, current_month + 1, 1).date()

    html = render_to_string('core/_player_month.html', {
        'current_month_name': calendar.month_name[current_month],
        'current_year': current_year,
        'prev_month': prev_month_date,
        'next_month': next_month_date,
        'month_cells': month_cells,
    }, request=request)
    return JsonResponse({'success': True, 'html': html})


@login_required
def team_schedule_month_partial(request):
    """
    Return the Team Schedule month card (header + grid + actions) for smooth month navigation.
    """
    try:
        if request.user.profile.role != Profile.Role.COACH:
            return JsonResponse({'success': False, 'message': 'Access denied'})
    except Profile.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Profile not found'})

    coach_team = getattr(request.user.profile, 'team', None)
    if not coach_team:
        return JsonResponse({'success': False, 'message': 'No team'})

    # Get or create team schedule
    team_schedule, _ = TeamSchedule.objects.get_or_create(team=coach_team)

    # Month param
    from datetime import datetime, timedelta
    import calendar
    today = timezone.now().date()
    month_param = request.GET.get('month')
    if month_param:
        try:
            current_year, current_month = map(int, month_param.split('-'))
        except (ValueError, TypeError):
            current_year = today.year
            current_month = today.month
    else:
        current_year = today.year
        current_month = today.month

    first_day = datetime(current_year, current_month, 1).date()
    last_day = datetime(current_year, current_month, calendar.monthrange(current_year, current_month)[1]).date()

    # Pre-compute team daily average readiness for the month
    team_athletes = User.objects.filter(profile__team=coach_team, profile__role=Profile.Role.ATHLETE)
    daily_avgs_qs = ReadinessReport.objects.filter(
        athlete__in=team_athletes,
        date_created__gte=first_day,
        date_created__lte=last_day
    ).values('date_created').annotate(avg_score=Avg('readiness_score'))
    date_to_avg = {entry['date_created']: round(entry['avg_score']) for entry in daily_avgs_qs}

    calendar_data = []
    start_weekday = first_day.weekday()
    for _ in range(start_weekday):
        calendar_data.append({'date': None, 'day': None, 'tag_id': None, 'is_current_month': False})
    current_date = first_day
    while current_date <= last_day:
        weekday = current_date.strftime('%a')
        tag = team_schedule.get_day_tag(current_date)
        avg_score = date_to_avg.get(current_date)
        calendar_data.append({
            'date': current_date,
            'day': current_date.day,
            'weekday': weekday,
            'tag_id': tag.id if tag else None,
            'tag_name': tag.name if tag else None,
            'tag_color': tag.color if tag else '#6c757d',
            'range_min': int(tag.target_min) if getattr(tag, 'target_min', None) is not None else None,
            'range_max': int(tag.target_max) if getattr(tag, 'target_max', None) is not None else None,
            'is_current_month': True,
            'is_today': current_date == today,
            'date_str': current_date.strftime('%Y-%m-%d'),
            'avg_score': avg_score
        })
        current_date += timedelta(days=1)
    while len(calendar_data) % 7 != 0:
        calendar_data.append({'date': None, 'day': None, 'tag_id': None, 'is_current_month': False})

    # Prev/next
    if current_month == 1:
        prev_month_date = datetime(current_year - 1, 12, 1).date()
    else:
        prev_month_date = datetime(current_year, current_month - 1, 1).date()
    if current_month == 12:
        next_month_date = datetime(current_year + 1, 1, 1).date()
    else:
        next_month_date = datetime(current_year, current_month + 1, 1).date()

    html = render_to_string('core/_team_schedule_month.html', {
        'team': coach_team,
        'calendar_data': calendar_data,
        'current_year': current_year,
        'month_name': calendar.month_name[current_month],
        'prev_month': prev_month_date,
        'next_month': next_month_date,
    }, request=request)
    return JsonResponse({'success': True, 'html': html})


@login_required
def team_tag_management(request):
    """
    View for coaches to manage their team's tags (list, add, edit, delete).
    """
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'COACH':
        messages.error(request, 'Access denied. Only coaches can manage team tags.')
        return redirect('core:player_dashboard')
    
    coach_team = request.user.profile.team
    team_tags = TeamTag.objects.filter(team=coach_team).order_by('name')
    
    context = {
        'team_tags': team_tags,
        'coach_team': coach_team,
    }
    
    return render(request, 'core/team_tag_management.html', context)


@login_required
def team_tag_create(request):
    """
    View for coaches to create new team tags.
    """
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'COACH':
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': 'Access denied'}, status=403)
        messages.error(request, 'Access denied. Only coaches can create team tags.')
        return redirect('core:player_dashboard')
    
    coach_team = request.user.profile.team
    
    if request.method == 'POST':
        form = TeamTagForm(request.POST, team=coach_team)
        if form.is_valid():
            form.save()
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'message': f'Tag "{form.instance.name}" created successfully!'})
            messages.success(request, f'Tag "{form.instance.name}" created successfully!')
            return redirect('core:team_tag_management')
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'errors': form.errors})
    else:
        form = TeamTagForm(team=coach_team)
    
    context = {
        'form': form,
        'coach_team': coach_team,
        'action': 'Create',
    }
    
    return render(request, 'core/team_tag_form.html', context)


@login_required
def team_tag_edit(request, tag_id):
    """
    View for coaches to edit existing team tags.
    """
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'COACH':
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': 'Access denied'}, status=403)
        messages.error(request, 'Access denied. Only coaches can edit team tags.')
        return redirect('core:player_dashboard')
    
    coach_team = request.user.profile.team
    
    try:
        tag = TeamTag.objects.get(id=tag_id, team=coach_team)
    except TeamTag.DoesNotExist:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': 'Tag not found'}, status=404)
        messages.error(request, 'Tag not found or you do not have permission to edit it.')
        return redirect('core:team_tag_management')
    
    if request.method == 'POST':
        form = TeamTagForm(request.POST, instance=tag, team=coach_team)
        if form.is_valid():
            form.save()
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'message': f'Tag "{form.instance.name}" updated successfully!'})
            messages.success(request, f'Tag "{form.instance.name}" updated successfully!')
            return redirect('core:team_tag_management')
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'errors': form.errors})
    else:
        form = TeamTagForm(instance=tag, team=coach_team)
    
    context = {
        'form': form,
        'coach_team': coach_team,
        'action': 'Edit',
        'tag': tag,
    }
    
    return render(request, 'core/team_tag_form.html', context)


@login_required
def team_tag_delete(request, tag_id):
    """
    View for coaches to delete team tags.
    """
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'COACH':
        messages.error(request, 'Access denied. Only coaches can delete team tags.')
        return redirect('core:player_dashboard')
    
    coach_team = request.user.profile.team
    
    try:
        tag = TeamTag.objects.get(id=tag_id, team=coach_team)
    except TeamTag.DoesNotExist:
        messages.error(request, 'Tag not found or you do not have permission to delete it.')
        return redirect('core:team_tag_management')
    
    if request.method == 'POST':
        tag.delete()
        # If AJAX, return JSON success, otherwise redirect back to Team Schedule
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True})
        return redirect('core:team_schedule_settings')
    
    # For non-POST (e.g., GET), avoid separate confirm page and stay within Team Schedule
    return redirect('core:team_schedule_settings')


def role_selection(request):
    """First step: user selects whether they are an Athlete or Coach."""
    # If already authenticated, redirect to appropriate dashboard
    if request.user.is_authenticated:
        return redirect('core:home')
    
    if request.method == 'POST':
        role = request.POST.get('role')
        if role in [Profile.Role.ATHLETE, Profile.Role.COACH]:
            request.session['selected_role'] = role
            # Check if join_code is in session (from join link)
            join_code = request.session.get('join_code')
            return redirect('core:signup')
        else:
            messages.error(request, 'Please select a valid role.')
    
    return render(request, 'core/role_selection.html')


def signup(request):
    """User registration form with role-based redirect."""
    # If already authenticated, redirect to appropriate dashboard
    if request.user.is_authenticated:
        return redirect('core:home')
    
    # Get role from session (must come from role_selection)
    selected_role = request.session.get('selected_role')
    if not selected_role or selected_role not in [Profile.Role.ATHLETE, Profile.Role.COACH]:
        messages.warning(request, 'Please select your role first.')
        return redirect('core:role_selection')
    
    # Get join_code from session (from join link) or URL parameter
    join_code = request.session.get('join_code') or request.GET.get('code', '')
    if join_code:
        request.session['join_code'] = join_code.upper().strip()
    
    form = UserSignupForm()
    
    if request.method == 'POST':
        form = UserSignupForm(request.POST)
        if form.is_valid():
            # Create user and profile
            user = form.save(role=selected_role)
            
            # Auto-login the user
            login(request, user)
            
            # Clear role from session
            request.session.pop('selected_role', None)
            
            # Redirect based on role
            if selected_role == Profile.Role.COACH:
                return redirect('core:team_setup_coach')
            else:  # ATHLETE
                return redirect('core:athlete_setup')
    
    context = {
        'form': form,
        'role': selected_role,
        'join_code': request.session.get('join_code', ''),
    }
    return render(request, 'core/signup.html', context)


@login_required
def team_setup_coach(request):
    """Coach team setup: create new team or join existing team."""
    # Must be a coach
    if request.user.profile.role != Profile.Role.COACH:
        messages.error(request, 'Access denied. Coach access required.')
        return redirect('core:home')
    
    # If already on a team, redirect to dashboard
    if request.user.profile.team:
        messages.info(request, 'You are already on a team.')
        return redirect('core:coach_dashboard')
    
    create_form = TeamCreationForm()
    join_form = JoinTeamForm()
    
    # Check if join_code is in session (from signup or join link)
    join_code = request.session.get('join_code', '')
    if join_code:
        join_form.fields['join_code'].initial = join_code
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'create':
            create_form = TeamCreationForm(request.POST)
            if create_form.is_valid():
                team = create_form.save()
                # Assign coach to team
                profile = request.user.profile
                profile.team = team
                profile.save()
                # Clear join_code from session
                request.session.pop('join_code', None)
                # Redirect to get started tutorial
                request.session['tutorial_step'] = 1
                return redirect('core:get_started')
        
        elif action == 'join':
            join_form = JoinTeamForm(request.POST)
            if join_form.is_valid():
                team = join_form.cleaned_data['team']
                # Check if user already has a team (soft-lock)
                if request.user.profile.team:
                    messages.error(request, 'You are already on a team. Leave your current team first.')
                    return redirect('core:team_setup_coach')
                # Assign coach to team
                profile = request.user.profile
                profile.team = team
                profile.save()
                # Clear join_code from session
                request.session.pop('join_code', None)
                # If joining existing team, go straight to dashboard (no tutorial)
                return redirect('core:coach_dashboard')
    
    context = {
        'create_form': create_form,
        'join_form': join_form,
        'has_join_code': bool(join_code),
    }
    return render(request, 'core/team_setup_coach.html', context)


@login_required
def athlete_setup(request):
    """Athlete setup: join team or individual mode (coming soon)."""
    # Must be an athlete
    if request.user.profile.role != Profile.Role.ATHLETE:
        messages.error(request, 'Access denied. Athlete access required.')
        return redirect('core:home')
    
    # If already on a team, redirect to dashboard
    if request.user.profile.team:
        messages.info(request, 'You are already on a team.')
        return redirect('core:player_dashboard')
    
    join_form = JoinTeamForm()
    
    # Check if join_code is in session (from signup or join link)
    join_code = request.session.get('join_code', '')
    if join_code:
        join_form.fields['join_code'].initial = join_code
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'join':
            join_form = JoinTeamForm(request.POST)
            if join_form.is_valid():
                team = join_form.cleaned_data['team']
                # Check if user already has a team (soft-lock)
                if request.user.profile.team:
                    messages.error(request, 'You are already on a team. Leave your current team first.')
                    return redirect('core:athlete_setup')
                # Assign athlete to team
                profile = request.user.profile
                profile.team = team
                profile.save()
                # Clear join_code from session
                request.session.pop('join_code', None)
                messages.success(request, f'Joined team "{team.name}"!')
                return redirect('core:player_dashboard')
        
        elif action == 'individual':
            messages.info(request, 'Individual mode is coming soon!')
            # For now, redirect to player dashboard even without a team
            return redirect('core:player_dashboard')
    
    context = {
        'join_form': join_form,
        'has_join_code': bool(join_code),
    }
    return render(request, 'core/athlete_setup.html', context)


def join_team_link(request, code):
    """Handle shareable join team links for authenticated and unauthenticated users."""
    # Normalize code to uppercase
    code = code.upper().strip()
    
    try:
        team = Team.objects.get(join_code=code)
    except Team.DoesNotExist:
        messages.error(request, 'Invalid team code. Please check the link and try again.')
        if request.user.is_authenticated:
            return redirect('core:home')
        else:
            return redirect('core:role_selection')
    
    # If not authenticated, store code in session and redirect to role selection
    if not request.user.is_authenticated:
        request.session['join_code'] = code
        messages.info(request, f'You\'ll join "{team.name}" after creating your account.')
        return redirect('core:role_selection')
    
    # User is authenticated - handle joining
    user = request.user
    
    # If user already on this team
    if user.profile.team == team:
        messages.info(request, f'You are already a member of {team.name}.')
        # Redirect to appropriate dashboard
        if user.profile.role == Profile.Role.COACH:
            return redirect('core:coach_dashboard')
        else:
            return redirect('core:player_dashboard')
    
    # If user already on a different team
    if user.profile.team and user.profile.team != team:
        messages.warning(request, f'You are already on team "{user.profile.team.name}". Leave your current team first to join "{team.name}".')
        if user.profile.role == Profile.Role.COACH:
            return redirect('core:coach_dashboard')
        else:
            return redirect('core:player_dashboard')
    
    # Handle POST confirmation
    if request.method == 'POST':
        confirm = request.POST.get('confirm', '').lower()
        if confirm in ['yes', 'join', 'confirm']:
            # Assign user to team
            profile = user.profile
            profile.team = team
            profile.save()
            # Clear join_code from session if present
            request.session.pop('join_code', None)
            messages.success(request, f'Successfully joined "{team.name}"!')
            # Redirect to appropriate dashboard
            if user.profile.role == Profile.Role.COACH:
                return redirect('core:coach_dashboard')
            else:
                return redirect('core:player_dashboard')
        else:
            messages.error(request, 'Join cancelled.')
            return redirect('core:home')
    
    # Show confirmation page (GET request, authenticated, no team or same team check passed)
    context = {
        'team': team,
        'join_code': code,
    }
    return render(request, 'core/join_team_confirm.html', context)


@login_required
def get_started(request, step=None):
    """Multi-step tutorial for coaches after creating a team."""
    # Must be a coach with a team
    if request.user.profile.role != Profile.Role.COACH:
        messages.error(request, 'Access denied. Coach access required.')
        return redirect('core:home')
    
    team = request.user.profile.team
    if not team:
        messages.warning(request, 'You must create or join a team first.')
        return redirect('core:team_setup_coach')
    
    # Get current step from session or URL parameter
    if step is None:
        step = request.session.get('tutorial_step', 1)
    else:
        request.session['tutorial_step'] = step
    
    step = int(step)
    
    # Handle skip tutorial
    if request.GET.get('skip') == 'true':
        request.session.pop('tutorial_step', None)
        return redirect('core:coach_dashboard')
    
    # Handle step navigation
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'next':
            # Validate current step before proceeding
            if step == 3:
                # Check if at least one tag exists
                tag_count = TeamTag.objects.filter(team=team).count()
                if tag_count == 0:
                    messages.error(request, 'Please create at least one team tag before continuing.')
                    return redirect('core:get_started', step=3)
            
            # Move to next step
            if step < 5:
                step += 1
                request.session['tutorial_step'] = step
                return redirect('core:get_started', step=step)
            else:
                # Tutorial complete
                request.session.pop('tutorial_step', None)
                return redirect('core:coach_dashboard')
        
        elif action == 'back':
            if step > 1:
                step -= 1
                request.session['tutorial_step'] = step
                return redirect('core:get_started', step=step)
    
    # Prepare context based on step
    context = {
        'team': team,
        'current_step': step,
        'total_steps': 5,
    }
    
    # Step 2: Introduction to the app
    if step == 2:
        # No special handling needed, just render the intro template
        pass
    
    # Step 3: Tag creation (simplified - just add Training and Matches)
    elif step == 3:
        # Handle simple tag creation via AJAX
        if request.method == 'POST' and request.POST.get('action') == 'create_tag':
            tag_name = request.POST.get('tag_name', '').strip()
            # Only allow predefined tags: Training or Matches
            predefined_tags = {
                'Training': {'target_min': 60, 'target_max': 70, 'color': '#0d6efd'},
                'Matches': {'target_min': 80, 'target_max': 100, 'color': '#198754'},
            }
            
            if tag_name in predefined_tags:
                # Check if tag already exists
                if TeamTag.objects.filter(team=team, name=tag_name).exists():
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({'success': False, 'message': f'"{tag_name}" tag already exists.'})
                
                # Create the tag
                tag_data = predefined_tags[tag_name]
                tag = TeamTag.objects.create(
                    team=team,
                    name=tag_name,
                    target_min=tag_data['target_min'],
                    target_max=tag_data['target_max'],
                    color=tag_data['color']
                )
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': True, 'message': f'"{tag_name}" tag created!'})
                return redirect('core:get_started', step=3)
            else:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'message': 'Invalid tag name.'})
        
        # Get existing tags
        existing_tags = TeamTag.objects.filter(team=team).order_by('name')
        # Check which predefined tags already exist
        has_training = TeamTag.objects.filter(team=team, name='Training').exists()
        has_matches = TeamTag.objects.filter(team=team, name='Matches').exists()
        has_any_tags = existing_tags.exists()
        
        context.update({
            'existing_tags': existing_tags,
            'has_training': has_training,
            'has_matches': has_matches,
            'has_any_tags': has_any_tags,
        })
    
    # Step 4: Schedule setup
    elif step == 4:
        # Get or create team schedule (same instance used in coach dashboard)
        team_schedule, created = TeamSchedule.objects.get_or_create(team=team)
        
        # Fix: Clear auto-populated weekly schedule if it exists
        # Only clear if: all days have same tag AND schedule appears unedited (created within 1 second of updated) AND no date overrides
        # This avoids clearing legitimate schedules where a coach manually set all days to the same tag
        if not created and team_schedule.weekly_schedule:
            weekday_values = [team_schedule.weekly_schedule.get(day) for day in ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'] if team_schedule.weekly_schedule.get(day) is not None]
            time_diff = (team_schedule.updated_at - team_schedule.created_at).total_seconds()
            # Only clear if all 7 days have the same tag, schedule was never manually edited (within 1 second), and no custom date overrides
            if (len(set(weekday_values)) == 1 and len(weekday_values) == 7 and 
                time_diff < 1.0 and 
                not team_schedule.date_overrides):
                # This matches the pattern of auto-population - clear it
                team_schedule.weekly_schedule = {}
                team_schedule.save()
        
        # Use existing calendar view logic
        from datetime import datetime, timedelta
        import calendar
        today = timezone.now().date()
        month_param = request.GET.get('month')
        if month_param:
            try:
                current_year, current_month = map(int, month_param.split('-'))
            except (ValueError, TypeError):
                current_year = today.year
                current_month = today.month
        else:
            current_year = today.year
            current_month = today.month
        
        first_day = datetime(current_year, current_month, 1).date()
        last_day = datetime(current_year, current_month, calendar.monthrange(current_year, current_month)[1]).date()
        
        # Get available tags
        day_tags = TeamTag.objects.filter(team=team)
        
        # Generate calendar data
        calendar_data = []
        current_date = first_day
        
        # Add empty cells for days before the first day of the month
        start_weekday = first_day.weekday()
        for i in range(start_weekday):
            calendar_data.append({'date': None, 'day': None, 'tag_id': None, 'is_current_month': False})
        
        # Add all days of the month
        while current_date <= last_day:
            weekday = current_date.strftime('%a')
            tag = team_schedule.get_day_tag(current_date)
            calendar_data.append({
                'date': current_date,
                'day': current_date.day,
                'weekday': weekday,
                'tag_id': tag.id if tag else None,
                'tag_name': tag.name if tag else None,
                'tag_color': tag.color if tag else '#6c757d',
                'range_min': int(tag.target_min) if getattr(tag, 'target_min', None) is not None else None,
                'range_max': int(tag.target_max) if getattr(tag, 'target_max', None) is not None else None,
                'is_current_month': True,
                'is_today': current_date == today,
                'date_str': current_date.strftime('%Y-%m-%d'),
            })
            current_date += timedelta(days=1)
        
        # Pad the end of the month to complete the last week
        while len(calendar_data) % 7 != 0:
            calendar_data.append({'date': None, 'day': None, 'tag_id': None, 'is_current_month': False})
        
        # Prev/next month for navigation
        if current_month == 1:
            prev_month_date = datetime(current_year - 1, 12, 1).date()
        else:
            prev_month_date = datetime(current_year, current_month - 1, 1).date()
        if current_month == 12:
            next_month_date = datetime(current_year + 1, 1, 1).date()
        else:
            next_month_date = datetime(current_year, current_month + 1, 1).date()
        
        context.update({
            'team_schedule': team_schedule,
            'day_tags': day_tags,
            'calendar_data': calendar_data,
            'current_month': current_month,
            'current_year': current_year,
            'month_name': calendar.month_name[current_month],
            'prev_month': prev_month_date,
            'next_month': next_month_date,
        })
    
    # Step 5: Share team
    elif step == 5:
        share_link = f"{request.scheme}://{request.get_host()}{reverse('core:join_team_link', args=[team.join_code])}"
        context['share_link'] = share_link
    
    # Handle AJAX partial requests for step 4 calendar
    if step == 4 and request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.GET.get('partial') == 'month':
        # Return just the calendar HTML for smooth navigation
        html = render_to_string('core/get_started_step4_calendar.html', context, request=request)
        return JsonResponse({'success': True, 'html': html})
    
    template_name = f'core/get_started_step{step}.html'
    return render(request, template_name, context)


@login_required
def team_admin(request):
    """
    Team Administration for coaches:
    - Rename team
    - Add/remove athletes and coaches
    - Delete team (with confirmation)
    """
    # Permissions
    try:
        if request.user.profile.role != Profile.Role.COACH:
            messages.error(request, 'Access denied. Coach access required.')
            return redirect('core:home')
    except Profile.DoesNotExist:
        messages.error(request, 'Your profile is not set up.')
        return redirect('logout')

    team = getattr(request.user.profile, 'team', None)
    if not team:
        messages.error(request, 'You are not assigned to a team.')
        return redirect('core:coach_dashboard')

    name_form = TeamNameForm(instance=team)

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'rename':
            name_form = TeamNameForm(request.POST, instance=team)
            if name_form.is_valid():
                name_form.save()
                messages.success(request, 'Team name updated.')
                return redirect('core:team_admin')
        elif action == 'remove_member':
            try:
                user_id = int(request.POST.get('user_id'))
            except (TypeError, ValueError):
                user_id = None
            if user_id:
                try:
                    member = User.objects.get(id=user_id)
                    profile = member.profile
                except (User.DoesNotExist, Profile.DoesNotExist):
                    profile = None
                if profile and profile.team_id == team.id:
                    # Prevent removing the last coach
                    if profile.role == Profile.Role.COACH:
                        num_coaches = User.objects.filter(profile__team=team, profile__role=Profile.Role.COACH).count()
                        if num_coaches <= 1:
                            messages.error(request, 'Cannot remove the last coach on the team.')
                        else:
                            profile.team = None
                            profile.save()
                            messages.success(request, f'Removed {member.get_full_name() or member.username} from team.')
                    else:
                        profile.team = None
                        profile.save()
                        messages.success(request, f'Removed {member.get_full_name() or member.username} from team.')
                else:
                    messages.error(request, 'Member not found on this team.')
                return redirect('core:team_admin')
        elif action == 'delete_team':
            confirm = request.POST.get('confirm', '')
            # Simple confirm: must match the exact team name
            if confirm == team.name:
                # Detach all members
                Profile.objects.filter(team=team).update(team=None)
                team.delete()
                messages.success(request, 'Team deleted.')
                return redirect('core:coach_dashboard')
            else:
                messages.error(request, 'Confirmation failed. Enter the exact team name to delete.')
                return redirect('core:team_admin')

    # Members
    coaches = User.objects.filter(profile__team=team, profile__role=Profile.Role.COACH).select_related('profile')
    athletes = User.objects.filter(profile__team=team, profile__role=Profile.Role.ATHLETE).select_related('profile')
    coach_count = coaches.count()

    context = {
        'team': team,
        'name_form': name_form,
        'coaches': coaches,
        'athletes': athletes,
        'coach_count': coach_count,
    }
    return render(request, 'core/team_admin.html', context)
