from django import forms
from django.utils.safestring import mark_safe
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import ReadinessReport, TeamTag, TeamSchedule
from django.contrib.auth.models import User
from .models import Team, Profile
from PIL import Image
import os
from .file_utils import (
    validate_file_content_type,
    validate_image_dimensions,
    check_storage_quota,
    MAX_FILE_SIZE,
    log_file_upload_security_event,
)
from .sanitization import sanitize_text_field, validate_no_html


class StepperWidget(forms.Widget):
    """Custom stepper widget with minus (–) and plus (+) buttons for 1-10 rating"""
    
    def __init__(self, attrs=None):
        default_attrs = {
            'min': '1',
            'max': '10',
            'step': '1'
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)
    
    def render(self, name, value, attrs=None, renderer=None):
        if value is None:
            value = 5
        
        final_attrs = self.build_attrs(attrs)
        widget_id = final_attrs.get('id', f'id_{name}')
        
        html = f'''
        <div class="stepper-control">
            <button type="button" class="stepper-btn stepper-minus" data-target="{widget_id}">–</button>
            <input type="text" name="{name}" value="{value}" id="{widget_id}" 
                   class="stepper-input" min="1" max="10" inputmode="numeric" pattern="[0-9]*">
            <button type="button" class="stepper-btn stepper-plus" data-target="{widget_id}">+</button>
        </div>
        '''
        return mark_safe(html)


class ReadinessReportForm(forms.ModelForm):
    """
    Athlete Check-In form for daily readiness assessment.
    """

    # All fields use custom stepper widgets for consistent 1-10 rating interface
    sleep_quality = forms.IntegerField(
        widget=StepperWidget(),
        label="Sleep quality last night?",
        initial=5
    )
    energy_fatigue = forms.IntegerField(
        widget=StepperWidget(),
        label="Energy levels today?",
        initial=5
    )
    muscle_soreness = forms.IntegerField(
        widget=StepperWidget(),
        label="How fresh are your muscles today?",
        initial=5
    )
    hydration = forms.IntegerField(
        widget=StepperWidget(),
        label="Hydration status right now?",
        initial=5
    )
    nutrition_quality = forms.IntegerField(
        widget=StepperWidget(),
        label="Nutrition over the past 24 hours?",
        initial=5
    )
    motivation = forms.IntegerField(
        widget=StepperWidget(),
        label="Motivation to train today?",
        initial=5
    )
    mood_stress = forms.IntegerField(
        widget=StepperWidget(),
        label="Overall headspace today?",
        initial=5
    )

    class Meta:
        model = ReadinessReport
        # User-facing fields for the readiness check-in form
        # Note: 'athlete', 'date_created', and 'readiness_score' are handled automatically
        fields = [
            'sleep_quality',
            'energy_fatigue',
            'muscle_soreness',
            'hydration',
            'nutrition_quality',
            'motivation',
            'mood_stress',
            'comments'
        ]

        widgets = {
            'comments': forms.Textarea(attrs={'rows': 4, 'class': 'form-control', 'placeholder': 'Enter any additional notes or observations...'}),
        }
    
    def clean_comments(self):
        """Sanitize comments field to prevent XSS attacks."""
        comments = self.cleaned_data.get('comments', '')
        if comments:
            # Sanitize HTML and strip dangerous content
            sanitized = sanitize_text_field(comments)
            return sanitized
        return comments


class TeamScheduleForm(forms.ModelForm):
    """
    Form for coaches to set their team's weekly schedule.
    """
    
    # Define weekday choices
    WEEKDAY_CHOICES = [
        ('Mon', 'Monday'),
        ('Tue', 'Tuesday'),
        ('Wed', 'Wednesday'),
        ('Thu', 'Thursday'),
        ('Fri', 'Friday'),
        ('Sat', 'Saturday'),
        ('Sun', 'Sunday'),
    ]
    
    # Create form fields for each weekday
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Get available team tags for this schedule's team
        team = getattr(self.instance, 'team', None)
        day_tags = TeamTag.objects.filter(team=team) if team else TeamTag.objects.none()
        tag_choices = [(tag.id, tag.name) for tag in day_tags]
        
        # Create a field for each weekday
        for weekday, display in self.WEEKDAY_CHOICES:
            field_name = f'day_{weekday.lower()}'
            self.fields[field_name] = forms.ChoiceField(
                choices=tag_choices,
                label=display,
                widget=forms.Select(attrs={'class': 'form-select'})
            )
            
            # Set initial value if instance exists
            if self.instance and self.instance.weekly_schedule:
                self.fields[field_name].initial = self.instance.weekly_schedule.get(weekday)
    
    class Meta:
        model = TeamSchedule
        fields = []  # We handle all fields in __init__
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Build the weekly schedule from form data
        weekly_schedule = {}
        for weekday, _ in self.WEEKDAY_CHOICES:
            field_name = f'day_{weekday.lower()}'
            if field_name in cleaned_data:
                # store tag ID (int) in JSON
                try:
                    weekly_schedule[weekday] = int(cleaned_data[field_name])
                except (TypeError, ValueError):
                    weekly_schedule[weekday] = None
        
        cleaned_data['weekly_schedule'] = weekly_schedule
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Set the weekly schedule from cleaned data
        if 'weekly_schedule' in self.cleaned_data:
            instance.weekly_schedule = self.cleaned_data['weekly_schedule']
        
        if commit:
            instance.save()
        return instance


class TeamTagForm(forms.ModelForm):
    """
    Form for coaches to create and edit team tags.
    """
    
    class Meta:
        model = TeamTag
        fields = ['name', 'target_min', 'target_max', 'color']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Training, Match, Recovery'}),
            'target_min': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '100'}),
            'target_max': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '100'}),
            'color': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
        }
        labels = {
            'name': 'Tag Name',
            'target_min': 'Minimum Target (%)',
            'target_max': 'Maximum Target (%)',
            'color': 'Color',
        }
    
    def __init__(self, *args, **kwargs):
        team = kwargs.pop('team', None)
        super().__init__(*args, **kwargs)
        
        if team:
            # Set the team for the tag
            self.instance.team = team
    
    def clean_name(self):
        """Sanitize tag name to prevent XSS attacks."""
        name = self.cleaned_data.get('name', '').strip()
        if name:
            # Sanitize tag name
            sanitized = sanitize_text_field(name, max_length=100)
            # Validate no HTML remains
            is_valid, error_msg = validate_no_html(sanitized, "Tag name")
            if not is_valid:
                raise forms.ValidationError(error_msg)
            return sanitized
        return name
    
    def clean(self):
        cleaned_data = super().clean()
        target_min = cleaned_data.get('target_min')
        target_max = cleaned_data.get('target_max')
        
        if target_min is not None and target_max is not None:
            if target_min > target_max:
                raise forms.ValidationError("Minimum target cannot be greater than maximum target.")
        
        return cleaned_data


class TeamNameForm(forms.ModelForm):
    """Rename a team. Coach-only form used in Team Administration."""
    class Meta:
        model = Team
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Team name'})
        }
    
    def clean_name(self):
        """Sanitize team name to prevent XSS attacks."""
        name = self.cleaned_data.get('name', '').strip()
        if name:
            # Sanitize team name
            sanitized = sanitize_text_field(name, max_length=100)
            # Validate no HTML remains
            is_valid, error_msg = validate_no_html(sanitized, "Team name")
            if not is_valid:
                raise forms.ValidationError(error_msg)
            return sanitized
        return name


class TeamLogoForm(forms.ModelForm):
    """Form for uploading and configuring team logo."""
    
    class Meta:
        model = Team
        fields = ['logo', 'logo_display_mode', 'background_opacity', 'background_position']
        widgets = {
            'logo': forms.FileInput(attrs={
                'accept': 'image/png,image/jpeg,image/jpg,image/svg+xml',
                'class': 'form-control'
            }),
            'logo_display_mode': forms.Select(attrs={'class': 'form-select'}),
            'background_opacity': forms.NumberInput(attrs={
                'class': 'form-control',
                'type': 'range',
                'min': '0.01',
                'max': '0.5',
                'step': '0.01'
            }),
            'background_position': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def clean_logo(self):
        """
        Validate uploaded logo with comprehensive security checks.
        
        Security validations:
        1. File size check (max 5MB)
        2. File extension validation
        3. Content-type validation (actual file content, not just extension)
        4. Image dimensions validation (max 2000x2000)
        5. Storage quota check (max 10MB per team)
        """
        logo = self.cleaned_data.get('logo')
        
        # If no new logo uploaded, keep existing one
        if not logo:
            return self.instance.logo if self.instance else None
        
        # Get team instance for quota checking
        team = self.instance
        
        # Log upload attempt for security audit
        if team and team.id:
            log_file_upload_security_event(
                event_type='upload_attempt',
                team_id=team.id,
                user_id=None,  # Will be set in view
                filename=logo.name,
                file_size=logo.size,
                success=False,  # Will update if successful
            )
        
        # 1. Check file size (max 5MB)
        if logo.size > MAX_FILE_SIZE:
            file_size_mb = logo.size / 1024 / 1024
            max_size_mb = MAX_FILE_SIZE / 1024 / 1024
            error_msg = (
                f"File is too large ({file_size_mb:.1f}MB). "
                f"Maximum allowed size is {max_size_mb:.0f}MB. "
                f"Please compress or resize your image and try again."
            )
            if team and team.id:
                log_file_upload_security_event(
                    event_type='upload_rejected',
                    team_id=team.id,
                    user_id=None,
                    filename=logo.name,
                    file_size=logo.size,
                    success=False,
                    error_message=error_msg,
                )
            raise forms.ValidationError(error_msg)
        
        # 2. Check file extension
        valid_extensions = ['.png', '.jpg', '.jpeg', '.svg']
        file_ext = os.path.splitext(logo.name)[1].lower()
        if file_ext not in valid_extensions:
            error_msg = (
                f"File format '{file_ext}' is not supported. "
                f"Please use PNG, JPG/JPEG, or SVG format only. "
                f"If your file is in a different format, convert it first using an image editor."
            )
            if team and team.id:
                log_file_upload_security_event(
                    event_type='upload_rejected',
                    team_id=team.id,
                    user_id=None,
                    filename=logo.name,
                    file_size=logo.size,
                    success=False,
                    error_message=error_msg,
                )
            raise forms.ValidationError(error_msg)
        
        # 3. Validate actual file content (content-type validation)
        # This is critical - verifies the file is actually what it claims to be
        is_valid, detected_mime, content_error = validate_file_content_type(logo)
        if not is_valid:
            # Provide user-friendly error message
            if "File extension" in (content_error or ""):
                error_msg = (
                    f"The file extension ({file_ext}) doesn't match the actual file content. "
                    f"This file appears to be a different format. "
                    f"Please ensure you're uploading a valid {file_ext[1:].upper()} image file, "
                    f"or rename the file with the correct extension."
                )
            elif "Invalid image file" in (content_error or ""):
                error_msg = (
                    f"The file appears to be corrupted or not a valid image. "
                    f"Please try opening the file in an image viewer to verify it's valid, "
                    f"then save it again and try uploading."
                )
            else:
                error_msg = (
                    f"File validation failed: {content_error or 'File content does not match file extension'}. "
                    f"Please ensure you're uploading a valid image file in PNG, JPG, or SVG format."
                )
            if team and team.id:
                log_file_upload_security_event(
                    event_type='upload_rejected',
                    team_id=team.id,
                    user_id=None,
                    filename=logo.name,
                    file_size=logo.size,
                    success=False,
                    error_message=f"Content-type validation failed: {content_error}",
                )
            raise forms.ValidationError(error_msg)
        
        # 4. For raster images (not SVG), validate dimensions
        if file_ext != '.svg':
            is_valid_dim, dimensions, dim_error = validate_image_dimensions(logo)
            if not is_valid_dim:
                if dimensions:
                    width, height = dimensions
                    error_msg = (
                        f"Image dimensions ({width}x{height} pixels) exceed the maximum allowed size (2000x2000 pixels). "
                        f"Please resize your image to be smaller than 2000x2000 pixels and try again. "
                        f"You can use an image editor or online tool to resize it."
                    )
                else:
                    error_msg = (
                        f"Could not read image dimensions. The file may be corrupted. "
                        f"Please try opening the file in an image viewer, then save it again and try uploading."
                    )
                if team and team.id:
                    log_file_upload_security_event(
                        event_type='upload_rejected',
                        team_id=team.id,
                        user_id=None,
                        filename=logo.name,
                        file_size=logo.size,
                        success=False,
                        error_message=error_msg,
                    )
                raise forms.ValidationError(error_msg)
        
        # 5. Check storage quota (max 10MB per team)
        if team and team.id:
            has_quota, current_usage, quota_limit, quota_error = check_storage_quota(team, logo.size)
            if not has_quota:
                current_usage_mb = current_usage / 1024 / 1024
                quota_mb = quota_limit / 1024 / 1024
                file_size_mb = logo.size / 1024 / 1024
                error_msg = (
                    f"Storage quota exceeded. Your team has used {current_usage_mb:.1f}MB of {quota_mb:.0f}MB total storage. "
                    f"This file ({file_size_mb:.1f}MB) would exceed the limit. "
                    f"Please remove your existing logo first, or use a smaller file."
                )
                if team and team.id:
                    log_file_upload_security_event(
                        event_type='upload_rejected',
                        team_id=team.id,
                        user_id=None,
                        filename=logo.name,
                        file_size=logo.size,
                        success=False,
                        error_message=quota_error,
                    )
                raise forms.ValidationError(error_msg)
        
        # Reset file pointer for saving
        logo.seek(0)
        
        return logo


class AddMemberForm(forms.Form):
    """
    Attach an existing user to the coach's team and set their role.
    Assumptions:
    - We only attach existing accounts (no invitation flow yet).
    - Lookup by username or email; if both provided, username wins.
    """
    ROLE_CHOICES = [
        (Profile.Role.ATHLETE, 'Athlete'),
        (Profile.Role.COACH, 'Coach'),
    ]
    username = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}))
    email = forms.EmailField(required=False, widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}))
    role = forms.ChoiceField(choices=ROLE_CHOICES, widget=forms.Select(attrs={'class': 'form-select'}))

    def clean(self):
        cleaned = super().clean()
        username = cleaned.get('username')
        email = cleaned.get('email')
        if not username and not email:
            raise forms.ValidationError('Provide a username or email to add a member.')
        # Resolve user
        user = None
        if username:
            user = User.objects.filter(username=username).first()
        if not user and email:
            user = User.objects.filter(email=email).first()
        if not user:
            raise forms.ValidationError('User not found. Create the account first, then add to team.')
        cleaned['user_obj'] = user
        return cleaned


class UserSignupForm(forms.Form):
    """User registration form with full name, email, and password validation."""
    first_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First name', 'autofocus': True}),
    )
    last_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last name'}),
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email address'}),
        help_text='This will be used for login'
    )
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'}),
        help_text='Your password must contain at least 8 characters.'
    )
    password2 = forms.CharField(
        label='Password confirmation',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm password'}),
    )
    accept_terms = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='I agree to the Terms of Service and Privacy Policy',
        error_messages={'required': 'You must accept the Terms of Service and Privacy Policy to create an account.'}
    )

    def clean_first_name(self):
        first_name = self.cleaned_data.get('first_name', '').strip()
        if not first_name:
            raise forms.ValidationError('First name is required.')
        return first_name

    def clean_last_name(self):
        last_name = self.cleaned_data.get('last_name', '').strip()
        if not last_name:
            raise forms.ValidationError('Last name is required.')
        return last_name

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('A user with that email already exists.')
        return email

    def clean_password1(self):
        password1 = self.cleaned_data.get('password1')
        try:
            validate_password(password1)
        except ValidationError as e:
            raise forms.ValidationError(e.messages)
        return password1

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("The two password fields didn't match.")
        return cleaned_data

    def save(self, role, commit=True):
        """Create User and Profile with the specified role."""
        email = self.cleaned_data['email']
        # Django requires username, so we use email as the username value
        user = User.objects.create_user(
            username=email,  # Use email as username to satisfy Django's requirement
            email=email,
            password=self.cleaned_data['password1'],
            first_name=self.cleaned_data['first_name'],
            last_name=self.cleaned_data['last_name'],
            is_active=False  # User must verify email before activation
        )
        profile = user.profile  # Created by signal
        profile.role = role
        profile.save()
        return user


class TeamCreationForm(forms.ModelForm):
    """Form for coaches to create a new team."""
    class Meta:
        model = Team
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Team name', 'autofocus': True})
        }
        labels = {
            'name': 'Team Name'
        }
    
    def clean_name(self):
        """Sanitize team name to prevent XSS attacks."""
        name = self.cleaned_data.get('name', '').strip()
        if name:
            # Sanitize team name
            sanitized = sanitize_text_field(name, max_length=100)
            # Validate no HTML remains
            is_valid, error_msg = validate_no_html(sanitized, "Team name")
            if not is_valid:
                raise forms.ValidationError(error_msg)
            return sanitized
        return name

    def save(self, commit=True):
        """Create team with auto-generated join_code."""
        team = super().save(commit=False)
        if commit:
            team.save()  # This will auto-generate join_code via model save()
        return team


class JoinTeamForm(forms.Form):
    """Form to join a team using a join code."""
    join_code = forms.CharField(
        max_length=8,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter team code',
            'autofocus': True,
            'style': 'text-transform: uppercase;'
        }),
        help_text='Enter the 6-character team code'
    )

    def clean_join_code(self):
        code = self.cleaned_data.get('join_code', '').upper().strip()
        if not code:
            raise forms.ValidationError('Please enter a team code.')
        
        # Validate code format (6 alphanumeric characters)
        if len(code) != 6 or not code.isalnum():
            raise forms.ValidationError('Team code must be 6 alphanumeric characters.')
        
        try:
            team = Team.objects.get(join_code=code)
            self.cleaned_data['team'] = team
        except Team.DoesNotExist:
            raise forms.ValidationError('Invalid team code. Please check and try again.')
        return code


class FeatureRequestForm(forms.Form):
    """Form for users to submit feature requests and bug reports."""
    request_type = forms.ChoiceField(
        choices=[
            ('FEATURE', 'Feature Request'),
            ('BUG', 'Bug Report'),
        ],
        widget=forms.Select(attrs={
            'class': 'form-select',
        }),
        label='Type',
        initial='FEATURE'
    )
    title = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Brief title for your request...',
            'autofocus': True
        }),
        label='Title',
        help_text='A clear, concise title for your feature request or bug report'
    )
    description = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'Describe your feature request or bug in detail...',
            'rows': 8,
            'style': 'resize: vertical;'
        }),
        help_text='Share your ideas, suggestions, or report issues. We value your feedback!',
        max_length=2000,
        min_length=10,
        label='Description'
    )
    
    def clean_title(self):
        title = self.cleaned_data.get('title', '').strip()
        if len(title) < 5:
            raise forms.ValidationError('Title must be at least 5 characters long.')
        
        # Sanitize title to prevent XSS attacks
        sanitized = sanitize_text_field(title, max_length=200)
        
        # Additional validation: ensure no HTML remains
        is_valid, error_msg = validate_no_html(sanitized, "Title")
        if not is_valid:
            raise forms.ValidationError(error_msg)
        
        return sanitized
    
    def clean_description(self):
        description = self.cleaned_data.get('description', '').strip()
        if len(description) < 10:
            raise forms.ValidationError('Please provide more details (at least 10 characters).')
        
        # Sanitize description to prevent XSS attacks
        sanitized = sanitize_text_field(description, max_length=2000)
        
        # Additional validation: ensure no HTML remains
        is_valid, error_msg = validate_no_html(sanitized, "Description")
        if not is_valid:
            raise forms.ValidationError(error_msg)
        
        return sanitized


class FeatureRequestCommentForm(forms.Form):
    """Form for commenting on feature requests."""
    comment = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'Add your comment...',
            'rows': 4,
            'style': 'resize: vertical;'
        }),
        max_length=1000,
        min_length=3,
        label='Comment'
    )
    
    def clean_comment(self):
        comment = self.cleaned_data.get('comment', '').strip()
        if len(comment) < 3:
            raise forms.ValidationError('Comment must be at least 3 characters long.')
        
        # Sanitize comment to prevent XSS attacks
        sanitized = sanitize_text_field(comment, max_length=1000)
        
        # Additional validation: ensure no HTML remains
        is_valid, error_msg = validate_no_html(sanitized, "Comment")
        if not is_valid:
            raise forms.ValidationError(error_msg)
        
        return sanitized


class UpdateProfileForm(forms.Form):
    """Form for updating user profile information (name, email)."""
    first_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First name'}),
        label='First Name'
    )
    last_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last name'}),
        label='Last Name'
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email address'}),
        label='Email Address'
    )
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.user:
            self.fields['first_name'].initial = self.user.first_name
            self.fields['last_name'].initial = self.user.last_name
            self.fields['email'].initial = self.user.email
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and self.user:
            # Check if email is already taken by another user
            if User.objects.filter(email=email).exclude(pk=self.user.pk).exists():
                raise forms.ValidationError('A user with that email already exists.')
        return email


class ChangePasswordForm(forms.Form):
    """Form for changing user password."""
    old_password = forms.CharField(
        label='Current Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter current password'}),
        required=True
    )
    new_password1 = forms.CharField(
        label='New Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter new password'}),
        required=True,
        help_text='Your password must contain at least 8 characters.'
    )
    new_password2 = forms.CharField(
        label='Confirm New Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm new password'}),
        required=True,
        help_text='Enter the same password as before, for verification.'
    )
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
    
    def clean_old_password(self):
        old_password = self.cleaned_data.get('old_password')
        if self.user and not self.user.check_password(old_password):
            raise forms.ValidationError('Your current password is incorrect.')
        return old_password
    
    def clean_new_password1(self):
        password1 = self.cleaned_data.get('new_password1')
        if self.user:
            try:
                validate_password(password1, self.user)
            except ValidationError as e:
                raise forms.ValidationError(e.messages)
        return password1
    
    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('new_password1')
        password2 = cleaned_data.get('new_password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("The two password fields didn't match.")
        return cleaned_data
    
    def save(self):
        """Update the user's password."""
        if self.user:
            self.user.set_password(self.cleaned_data['new_password1'])
            self.user.save()
        return self.user


class JoinTeamByCodeForm(forms.Form):
    """Form to join a team using a join code (updated for multiple teams)."""
    join_code = forms.CharField(
        max_length=8,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter team code',
            'autofocus': True,
            'style': 'text-transform: uppercase;'
        }),
        help_text='Enter the 6-character team code'
    )
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
    
    def clean_join_code(self):
        code = self.cleaned_data.get('join_code', '').upper().strip()
        if not code:
            raise forms.ValidationError('Please enter a team code.')
        
        # Validate code format (6 alphanumeric characters)
        if len(code) != 6 or not code.isalnum():
            raise forms.ValidationError('Team code must be 6 alphanumeric characters.')
        
        try:
            team = Team.objects.get(join_code=code)
            self.cleaned_data['team'] = team
        except Team.DoesNotExist:
            raise forms.ValidationError('Invalid team code. Please check and try again.')
        return code
    
    def clean(self):
        cleaned_data = super().clean()
        if self.user and 'team' in cleaned_data:
            team = cleaned_data['team']
            profile = self.user.profile
            
            # Check if already in this team
            if team in profile.get_teams():
                raise forms.ValidationError('You are already a member of this team.')
        
        return cleaned_data
    
    def save(self):
        """Add the team to the user's teams."""
        if self.user and 'team' in self.cleaned_data:
            team = self.cleaned_data['team']
            profile = self.user.profile
            
            # Add to teams ManyToMany
            profile.teams.add(team)
            
            # If no primary team set, set it as primary
            if not profile.team:
                profile.team = team
                profile.save()
            
            return team
        return None


class ReminderSettingsForm(forms.Form):
    """Form for managing daily reminder preferences."""
    daily_reminder_enabled = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Enable daily reminder emails',
        help_text='Receive daily reminder emails at 12pm in your local timezone'
    )
    timezone = forms.CharField(
        max_length=50,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., America/New_York, Europe/London'
        }),
        label='Timezone',
        help_text='Your timezone for daily reminders (e.g., America/New_York, Europe/London, UTC)'
    )
    
    def __init__(self, *args, **kwargs):
        self.profile = kwargs.pop('profile', None)
        super().__init__(*args, **kwargs)
        if self.profile:
            self.fields['daily_reminder_enabled'].initial = self.profile.daily_reminder_enabled
            self.fields['timezone'].initial = self.profile.timezone
    
    def save(self):
        """Update the profile's reminder settings."""
        if self.profile:
            self.profile.daily_reminder_enabled = self.cleaned_data['daily_reminder_enabled']
            self.profile.timezone = self.cleaned_data['timezone']
            self.profile.save()
        return self.profile
