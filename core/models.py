from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from datetime import timedelta
import json
import string
import secrets


# Create a Team model to group users
class Team(models.Model):
    """Represents a single sports team."""
    name = models.CharField(max_length=100, unique=True)
    target_readiness = models.PositiveIntegerField(
        default=100,
        help_text="Target team readiness percentage (0-100)"
    )
    join_code = models.CharField(
        max_length=8,
        unique=True,
        editable=False,
        blank=True,
        null=True,
        help_text="Unique code for joining this team"
    )
    
    # Team branding/logo fields
    logo = models.ImageField(
        upload_to='team_logos/',
        blank=True,
        null=True,
        help_text="Team logo for branding"
    )
    
    logo_display_mode = models.CharField(
        max_length=20,
        choices=[
            ('NONE', 'No Logo'),
            ('HEADER', 'Header Logo Only'),
            ('BACKGROUND', 'Background Only'),
            ('BOTH', 'Header + Background'),
        ],
        default='NONE',
        help_text="How to display the team logo"
    )
    
    background_opacity = models.FloatField(
        default=0.05,
        validators=[MinValueValidator(0.01), MaxValueValidator(0.5)],
        help_text="Background logo opacity (0.01-0.5)"
    )
    
    background_position = models.CharField(
        max_length=20,
        choices=[
            ('CENTER', 'Center'),
            ('TOP_LEFT', 'Top Left'),
            ('TOP_RIGHT', 'Top Right'),
            ('BOTTOM_LEFT', 'Bottom Left'),
            ('BOTTOM_RIGHT', 'Bottom Right'),
        ],
        default='CENTER',
        help_text="Background logo position"
    )

    @staticmethod
    def generate_join_code():
        """Generate a unique 6-character alphanumeric code."""
        alphabet = string.ascii_uppercase + string.digits
        while True:
            code = ''.join(secrets.choice(alphabet) for _ in range(6))
            if not Team.objects.filter(join_code=code).exists():
                return code

    def save(self, *args, **kwargs):
        """Auto-generate join_code if not set."""
        if not self.join_code:
            self.join_code = self.generate_join_code()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class TeamTag(models.Model):
    """
    Coach/team-owned tag that defines a day type with a target range and color.
    - Visible only to the owning team
    - "target_min" and "target_max" define the acceptable readiness range (0-100)
    - "color" is a HEX value used in UI badges
    """
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='tags')
    name = models.CharField(max_length=40)
    target_min = models.PositiveIntegerField(
        default=60, 
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Minimum acceptable readiness percentage (0-100)"
    )
    target_max = models.PositiveIntegerField(
        default=80, 
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Maximum acceptable readiness percentage (0-100)"
    )
    color = models.CharField(max_length=7, default="#0d6efd", help_text="HEX color like #0d6efd")
    
    def clean(self):
        from django.core.exceptions import ValidationError
        if self.target_min > self.target_max:
            raise ValidationError("Minimum target cannot be greater than maximum target")
    
    @property
    def target_midpoint(self):
        """Calculate the midpoint of the target range for display purposes"""
        return (self.target_min + self.target_max) // 2

    class Meta:
        unique_together = ("team", "name")
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.team.name})"


class EmailVerification(models.Model):
    """
    Email verification tokens for new user accounts.
    Tokens expire after 24 hours.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='email_verification')
    token = models.CharField(max_length=64, unique=True, db_index=True)
    verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    @staticmethod
    def generate_token():
        """Generate a unique verification token."""
        return secrets.token_urlsafe(48)

    def save(self, *args, **kwargs):
        """Auto-generate token and set expiration if not set."""
        if not self.token:
            # Ensure uniqueness
            while True:
                token = self.generate_token()
                if not EmailVerification.objects.filter(token=token).exists():
                    self.token = token
                    break
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=24)
        super().save(*args, **kwargs)

    @property
    def is_expired(self):
        """Check if the verification token has expired."""
        return timezone.now() > self.expires_at

    @property
    def is_valid(self):
        """Check if the token is valid (not expired and not already verified)."""
        return not self.verified and not self.is_expired

    def __str__(self):
        return f"Email verification for {self.user.email} ({'verified' if self.verified else 'pending'})"

    class Meta:
        ordering = ['-created_at']


class Profile(models.Model):
    """
    Extends the built-in Django User model.
    This holds extra information about a user, like their role and team.
    """

    class Role(models.TextChoices):
        ATHLETE = 'ATHLETE', 'Athlete'
        COACH = 'COACH', 'Coach'

    # This links the Profile to a User. One-to-one means each User has one Profile.
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    # The user's role
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.ATHLETE)

    # The team the user belongs to. Coaches can also belong to a team.
    # 'null=True' and 'blank=True' allow for users (like a super-admin)
    # who might not be on a team.
    # NOTE: Keeping team as ForeignKey for backward compatibility and coach's primary team
    # For athletes, use teams (ManyToMany) to support multiple teams
    team = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True, related_name='primary_members')
    
    # Multiple teams support (primarily for athletes)
    # Athletes can belong to multiple teams; coaches typically have one team
    teams = models.ManyToManyField(Team, related_name='members', blank=True)

    # Player current status (MVP). Stored on Profile for simplicity.
    class PlayerStatus(models.TextChoices):
        AVAILABLE = 'AVAILABLE', 'Available'
        INJURED = 'INJURED', 'Injured'
        SICK = 'SICK', 'Sick'
        EXCUSED = 'EXCUSED', 'Excused'

    current_status = models.CharField(
        max_length=16,
        choices=PlayerStatus.choices,
        default=PlayerStatus.AVAILABLE
    )
    status_note = models.CharField(max_length=140, blank=True)
    status_updated_at = models.DateTimeField(auto_now=True)
    
    # Timezone for daily reminder scheduling
    timezone = models.CharField(
        max_length=50,
        default='UTC',
        help_text="User's timezone for daily reminders (e.g., 'America/New_York', 'Europe/London', 'UTC')"
    )
    
    # Daily reminder preference
    daily_reminder_enabled = models.BooleanField(
        default=True,
        help_text="Enable daily reminder emails at 12pm local time"
    )

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"
    
    def get_teams(self):
        """Get all teams for this user. For backward compatibility, includes primary team."""
        teams_list = list(self.teams.all())
        if self.team and self.team not in teams_list:
            teams_list.append(self.team)
        return teams_list


class ReadinessReport(models.Model):
    """
    The daily subjective report submitted by an athlete.
    """
    # A 1-5 or 1-10 scale is common. Let's use 1-10 for more nuance.
    SCALE_VALIDATORS = [MinValueValidator(1), MaxValueValidator(10)]

    # The athlete who submitted this report.
    # We link to the User model for simplicity in queries.
    athlete = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reports")

    # The date of the report. We use 'default=timezone.now' to set it automatically.
    date_created = models.DateField(default=timezone.now)

    # --- The Subjective Metrics ---

    # 1. Sleep Quality
    sleep_quality = models.PositiveIntegerField(
        validators=SCALE_VALIDATORS,
        help_text="Rate your sleep quality from 1 (Very poor/restless/<5hrs) to 10 (Excellent/deep/uninterrupted)"
    )

    # 2. Energy/Fatigue
    energy_fatigue = models.PositiveIntegerField(
        validators=SCALE_VALIDATORS,
        help_text="Rate your energy from 1 (Exhausted/heavy) to 10 (Fully energised/alert)"
    )

    # 3. Muscle Soreness/Stiffness
    muscle_soreness = models.PositiveIntegerField(
        validators=SCALE_VALIDATORS,
        help_text="Rate your muscle soreness from 1 (Extremely sore/tight) to 10 (No soreness/loose/ready)"
    )

    # 4. Mood/Stress
    mood_stress = models.PositiveIntegerField(
        validators=SCALE_VALIDATORS,
        help_text="Rate your mood from 1 (Very stressed/low mood) to 10 (Calm/positive/clear-headed)"
    )

    # 5. Motivation to Train
    motivation = models.PositiveIntegerField(
        validators=SCALE_VALIDATORS,
        help_text="Rate your motivation from 1 (Not motivated) to 10 (Extremely motivated/excited)"
    )

    # 6. Nutrition Quality
    nutrition_quality = models.PositiveIntegerField(
        validators=SCALE_VALIDATORS,
        help_text="Rate your nutrition from 1 (Poor/skipped meals) to 10 (Excellent/balanced meals)"
    )

    # 7. Hydration
    hydration = models.PositiveIntegerField(
        validators=SCALE_VALIDATORS,
        help_text="Rate your hydration from 1 (Dehydrated/dry mouth) to 10 (Well-hydrated/clear urine/alert)"
    )

    # --- The Calculated Score ---

    # This is the final "Readiness Score" for the day.
    # We'll make it a percentage (0-100).
    readiness_score = models.PositiveIntegerField(
        editable=False,  # This ensures it can't be edited in a form
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )

    # Optional field for athletes to add extra context
    comments = models.TextField(blank=True, null=True)

    class Meta:
        # This ensures an athlete can only submit one report per day.
        unique_together = ('athlete', 'date_created')
        ordering = ['-date_created']  # Show newest reports first

    def calculate_readiness_score(self):
        """
        Calculates the readiness score using a weighted average.
        All 7 metrics are on a 1-10 scale where higher is better.
        We compute a weighted average (weights sum to 1.0) and convert to percentage.

        Assumptions:
        - Weights reflect MVP evidence-based priorities provided by coaching staff.
        - No per-athlete personalization yet; global weights apply to all users.
        """
        # MVP weights (sum = 1.00)
        weights = {
            'sleep_quality': 0.22,
            'energy_fatigue': 0.20,
            'muscle_soreness': 0.15,
            'mood_stress': 0.15,
            'motivation': 0.10,
            'nutrition_quality': 0.10,
            'hydration': 0.08,
        }

        # Weighted sum on 1–10 scale
        weighted_avg = (
            self.sleep_quality * weights['sleep_quality'] +
            self.energy_fatigue * weights['energy_fatigue'] +
            self.muscle_soreness * weights['muscle_soreness'] +
            self.mood_stress * weights['mood_stress'] +
            self.motivation * weights['motivation'] +
            self.nutrition_quality * weights['nutrition_quality'] +
            self.hydration * weights['hydration']
        )

        # Convert 1–10 weighted average to 0–100 percentage
        percentage_score = (weighted_avg / 10) * 100
        return round(percentage_score)

    def save(self, *args, **kwargs):
        """
        Override the default save method to automatically calculate
        the readiness_score before saving to the database.
        """
        self.readiness_score = self.calculate_readiness_score()
        super().save(*args, **kwargs)  # Call the "real" save method

    def get_personalized_feedback(self):
        """
        Generates personalized feedback based on the athlete's metrics.
        Analyzes patterns and provides actionable recovery insights.
        """
        # Define metric names and their scores
        metrics = {
            'sleep': self.sleep_quality,
            'energy': self.energy_fatigue,
            'soreness': self.muscle_soreness,
            'mood': self.mood_stress,
            'motivation': self.motivation,
            'nutrition': self.nutrition_quality,
            'hydration': self.hydration
        }
        
        # Classify scores
        def classify_score(score):
            if score >= 8:
                return 'high'
            elif score >= 5:
                return 'moderate'
            else:
                return 'low'
        
        # Find the lowest scoring metric (primary limiter)
        lowest_metric = min(metrics.items(), key=lambda x: x[1])
        lowest_name, lowest_score = lowest_metric
        lowest_classification = classify_score(lowest_score)
        
        # Get all low scores for context
        low_scores = {name: score for name, score in metrics.items() if classify_score(score) == 'low'}
        
        # Rule-based feedback system (ordered by priority - most specific first)
        feedback_rules = [
            # Multiple low scores (highest priority - check first)
            {
                'condition': lambda: len(low_scores) >= 4,
                'message': "Your system needs recovery. Focus on rest, hydration, and nutrition today."
            },
            {
                'condition': lambda: len(low_scores) >= 3,
                'message': "Multiple areas need attention. Prioritise recovery and lighter training today."
            },
            
            # Sleep-related combinations
            {
                'condition': lambda: lowest_name == 'soreness' and 'sleep' in low_scores,
                'message': "Muscle fatigue may be linked to poor sleep. Prioritise rest and stretching."
            },
            {
                'condition': lambda: lowest_name == 'energy' and 'sleep' in low_scores,
                'message': "Low energy likely from poor sleep. Focus on sleep hygiene and recovery."
            },
            {
                'condition': lambda: lowest_name == 'sleep' and 'mood' in low_scores,
                'message': "Poor sleep affecting mood. Create a calming bedtime routine."
            },
            
            # Hydration-related combinations
            {
                'condition': lambda: lowest_name == 'soreness' and 'hydration' in low_scores,
                'message': "Soreness may be tied to dehydration. Drink more water and move lightly today."
            },
            {
                'condition': lambda: lowest_name == 'energy' and 'hydration' in low_scores,
                'message': "Dehydration affecting energy. Increase fluid intake throughout the day."
            },
            {
                'condition': lambda: lowest_name == 'hydration' and 'nutrition' in low_scores,
                'message': "Poor hydration and nutrition. Focus on balanced meals and regular water intake."
            },
            
            # Nutrition-related combinations
            {
                'condition': lambda: lowest_name == 'soreness' and 'nutrition' in low_scores,
                'message': "Soreness likely due to poor fuelling. Eat balanced meals and prioritise recovery."
            },
            {
                'condition': lambda: lowest_name == 'energy' and 'nutrition' in low_scores,
                'message': "Low energy from poor nutrition. Eat regular, balanced meals today."
            },
            {
                'condition': lambda: lowest_name == 'motivation' and 'nutrition' in low_scores,
                'message': "Low motivation may be linked to poor nutrition. Fuel your body properly."
            },
            
            # Mood and motivation combinations
            {
                'condition': lambda: lowest_name == 'motivation' and 'soreness' in low_scores,
                'message': "Reduced motivation may come from soreness — take a low-impact day."
            },
            {
                'condition': lambda: lowest_name == 'mood' and 'sleep' in low_scores,
                'message': "Poor mood linked to sleep issues. Prioritise rest and stress management."
            },
            {
                'condition': lambda: lowest_name == 'motivation' and 'mood' in low_scores,
                'message': "Low motivation and mood. Consider light activity or mental recovery time."
            },
            
            # Energy-specific patterns
            {
                'condition': lambda: lowest_name == 'energy' and 'sleep' not in low_scores and metrics['sleep'] >= 8 and metrics['energy'] < 8,
                'message': "You slept well but energy is low — try light activity or extra recovery time."
            },
            
            # Single low score patterns (when only one metric is low)
            {
                'condition': lambda: len(low_scores) == 1 and lowest_name == 'soreness',
                'message': "Muscle soreness is your main concern today. Focus on gentle movement and recovery work."
            },
            {
                'condition': lambda: len(low_scores) == 1 and lowest_name == 'sleep',
                'message': "Poor sleep is affecting your readiness. Prioritise sleep hygiene and recovery today."
            },
            {
                'condition': lambda: len(low_scores) == 1 and lowest_name == 'energy',
                'message': "Low energy levels detected. Consider lighter training or additional recovery time."
            },
            {
                'condition': lambda: len(low_scores) == 1 and lowest_name == 'hydration',
                'message': "Hydration needs attention. Increase fluid intake throughout the day."
            },
            {
                'condition': lambda: len(low_scores) == 1 and lowest_name == 'nutrition',
                'message': "Nutrition quality is low. Focus on balanced meals and proper fuelling."
            },
            {
                'condition': lambda: len(low_scores) == 1 and lowest_name == 'mood',
                'message': "Mood and stress levels are elevated. Consider stress management and mental recovery."
            },
            {
                'condition': lambda: len(low_scores) == 1 and lowest_name == 'motivation',
                'message': "Motivation is low today. Consider lighter activities or mental recovery time."
            },
        ]
        
        # Check each rule and return the first match
        for rule in feedback_rules:
            if rule['condition']():
                return rule['message']
        
        # Fallback to general feedback based on overall readiness score
        score = self.readiness_score if self.readiness_score is not None else self.calculate_readiness_score()
        if score >= 80:
            return "You're fully recovered and ready to perform."
        elif score >= 60:
            return "Train smart today and monitor recovery."
        elif score >= 40:
            return "Body needs lighter load or active recovery."
        else:
            return "Full rest recommended."

    def __str__(self):
        return f"Report for {self.athlete.username} on {self.date_created} ({self.readiness_score}%)"


class TeamSchedule(models.Model):
    """
    Stores the schedule for each team, supporting both weekly patterns and specific date overrides.
    """
    team = models.OneToOneField(Team, on_delete=models.CASCADE, related_name='schedule')

    # Store the weekly schedule as JSON (default pattern)
    # Format: {"Mon": 3, "Tue": 7, ...} where values are TeamTag IDs
    weekly_schedule = models.JSONField(
        default=dict,
        help_text="Weekly schedule mapping weekdays to day tags"
    )

    # Store specific date overrides as JSON
    # Format: {"2025-10-26": 5, "2025-12-25": 9} where values are TeamTag IDs
    date_overrides = models.JSONField(
        default=dict,
        help_text="Specific date overrides for the weekly schedule"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Schedule for {self.team.name}"

    def get_day_tag_id(self, date_or_weekday):
        """
        Return the TeamTag ID for a specific date or weekday.
        """
        from datetime import date

        if isinstance(date_or_weekday, date):
            date_str = date_or_weekday.strftime('%Y-%m-%d')
            if date_str in self.date_overrides:
                value = self.date_overrides[date_str]
                # Explicit None means cleared tag for this date
                if value is None:
                    return None
                return value
            weekday = date_or_weekday.strftime('%a')
            return self.weekly_schedule.get(weekday)
        return self.weekly_schedule.get(date_or_weekday)

    def get_day_tag(self, date_or_weekday):
        """Return the TeamTag instance for the given date/weekday, or None."""
        tag_id = self.get_day_tag_id(date_or_weekday)
        if tag_id:
            try:
                return TeamTag.objects.get(id=tag_id, team=self.team)
            except TeamTag.DoesNotExist:
                return None
        return None

    def set_day_tag(self, date_or_weekday, tag_id: int | None):
        """
        Set the TeamTag for a specific date or weekday using a TeamTag ID.
        """
        from datetime import date

        if isinstance(date_or_weekday, date):
            date_str = date_or_weekday.strftime('%Y-%m-%d')
            if not self.date_overrides:
                self.date_overrides = {}
            # Allow clearing by setting explicit None
            self.date_overrides[date_str] = int(tag_id) if tag_id is not None else None
        else:
            if not self.weekly_schedule:
                self.weekly_schedule = {}
            # For weekly schedule, None removes the key to indicate no default
            if tag_id is None:
                self.weekly_schedule.pop(date_or_weekday, None)
            else:
                self.weekly_schedule[date_or_weekday] = int(tag_id)

        self.save()
    
    def save(self, *args, **kwargs):
        """Set default empty schedule if none exists."""
        if not self.weekly_schedule:
            self.weekly_schedule = {}
        if not self.date_overrides:
            self.date_overrides = {}
        super().save(*args, **kwargs)


class PlayerPersonalLabel(models.Model):
    """
    Personal labels that players can add to their own days.
    These don't affect target ranges - they're just informational.
    Coaches can see these to understand player's full schedule.
    """
    athlete = models.ForeignKey(User, on_delete=models.CASCADE, related_name='personal_labels')
    date = models.DateField()
    label = models.CharField(max_length=100, help_text="Player's personal label for this day (e.g., 'Gym session', 'Personal training')")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('athlete', 'date')
        ordering = ['date']

    def __str__(self):
        return f"{self.athlete.username} - {self.date}: {self.label}"

# Utility methods retained for potential analytics, independent of tags
class FeatureRequest(models.Model):
    """
    Model for feature requests and bug reports submitted by users.
    Users can upvote and comment on feature requests.
    """
    class RequestType(models.TextChoices):
        FEATURE = 'FEATURE', 'Feature Request'
        BUG = 'BUG', 'Bug Report'
    
    class Status(models.TextChoices):
        OPEN = 'OPEN', 'Open'
        IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
        COMPLETED = 'COMPLETED', 'Completed'
        REJECTED = 'REJECTED', 'Rejected'
        DUPLICATE = 'DUPLICATE', 'Duplicate'
    
    # User who submitted the request
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='feature_requests')
    
    # Request details
    title = models.CharField(max_length=200, help_text="Brief title for the feature request or bug")
    description = models.TextField(max_length=2000, help_text="Detailed description of the feature request or bug")
    request_type = models.CharField(max_length=10, choices=RequestType.choices, default=RequestType.FEATURE)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Upvotes - users who have upvoted this request
    upvoted_by = models.ManyToManyField(User, related_name='upvoted_feature_requests', blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Feature Request'
        verbose_name_plural = 'Feature Requests'
    
    def __str__(self):
        return f"{self.get_request_type_display()}: {self.title}"
    
    def upvote_count(self):
        """Return the number of upvotes."""
        return self.upvoted_by.count()
    
    def has_user_upvoted(self, user):
        """Check if a user has upvoted this request."""
        return self.upvoted_by.filter(id=user.id).exists()


class FeatureRequestComment(models.Model):
    """
    Comments on feature requests.
    """
    # Feature request this comment belongs to
    feature_request = models.ForeignKey(FeatureRequest, on_delete=models.CASCADE, related_name='comments')
    
    # User who made the comment
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='feature_request_comments')
    
    # Comment content
    comment = models.TextField(max_length=1000, help_text="Your comment")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['created_at']
        verbose_name = 'Feature Request Comment'
        verbose_name_plural = 'Feature Request Comments'
    
    def __str__(self):
        return f"Comment by {self.user.username} on {self.feature_request.title}"


class ReadinessStatus:
    @staticmethod
    def get_primary_limiter(report):
        metrics = {
            'sleep_quality': report.sleep_quality,
            'energy_fatigue': report.energy_fatigue,
            'muscle_soreness': report.muscle_soreness,
            'mood_stress': report.mood_stress,
            'motivation': report.motivation,
            'nutrition_quality': report.nutrition_quality,
            'hydration': report.hydration
        }
        return min(metrics.items(), key=lambda x: x[1])

    @staticmethod
    def get_team_primary_limiter(reports):
        if not reports:
            return None, 0, 0
        limiter_counts = {}
        total_reports = len(reports)
        for report in reports:
            limiter, _ = ReadinessStatus.get_primary_limiter(report)
            limiter_counts[limiter] = limiter_counts.get(limiter, 0) + 1
        most_frequent = max(limiter_counts.items(), key=lambda x: x[1])
        metric_name, count = most_frequent
        percentage = round((count / total_reports) * 100, 1)
        return metric_name, count, percentage

    @staticmethod
    def get_athlete_baseline(athlete, days=14):
        from datetime import timedelta
        from django.utils import timezone
        from django.db.models import Avg
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days-1)
        reports = ReadinessReport.objects.filter(
            athlete=athlete,
            date_created__gte=start_date,
            date_created__lte=end_date
        )
        if reports.count() < 3:
            return None
        avg_score = reports.aggregate(avg=Avg('readiness_score'))['avg']
        return round(avg_score, 1) if avg_score else None

    @staticmethod
    def get_consistency_score(athlete, days=14):
        from datetime import timedelta
        from django.utils import timezone
        import statistics
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days-1)
        reports = ReadinessReport.objects.filter(
            athlete=athlete,
            date_created__gte=start_date,
            date_created__lte=end_date
        )
        if reports.count() < 3:
            return None
        scores = [report.readiness_score for report in reports]
        return round(statistics.stdev(scores), 1)
