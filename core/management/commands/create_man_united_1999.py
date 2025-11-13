from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.utils import timezone
from django.conf import settings
from datetime import timedelta, date
import random
from core.models import Team, Profile, ReadinessReport


class Command(BaseCommand):
    help = 'Create Manchester United 1999 team with Sir Alex Ferguson as coach and players from the treble-winning squad, including data until end of December'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force creation even in production (use with extreme caution)',
        )

    def handle(self, *args, **options):
        # Security check: prevent running in production unless forced
        if not settings.DEBUG and not options['force']:
            raise CommandError(
                'This command is disabled in production for security reasons.\n'
                'Test accounts with simple passwords should not be created in production.\n'
                'If you really need to run this in production, use --force flag.\n'
                'WARNING: Using --force will create accounts with weak passwords!'
            )
        
        if options['force']:
            self.stdout.write(
                self.style.WARNING(
                    'WARNING: Running in production mode with --force flag.\n'
                    'This will create accounts with weak passwords (coach123/athlete123).\n'
                    'These should be changed immediately after creation!'
                )
            )
        
        self.stdout.write('Creating Manchester United 1999 team...')

        # Create team
        team, created = Team.objects.get_or_create(name="Manchester United 1999")
        if created:
            self.stdout.write(f'Created team: {team.name}')
        else:
            self.stdout.write(f'Team {team.name} already exists. Skipping team creation.')
            return

        # Create coach - Sir Alex Ferguson
        coach_username = 'sir_alex_ferguson'
        coach_email = 'sir.alex.ferguson@manutd.com'
        
        if User.objects.filter(username=coach_username).exists():
            coach = User.objects.get(username=coach_username)
            self.stdout.write(f'Coach {coach.get_full_name()} already exists.')
        else:
            coach = User.objects.create_user(
                username=coach_username,
                email=coach_email,
                password='coach123',
                first_name='Alex',
                last_name='Ferguson'
            )
            coach.profile.role = Profile.Role.COACH
            coach.profile.team = team
            coach.profile.teams.add(team)
            coach.profile.save()
            self.stdout.write(f'Created coach: {coach.get_full_name()}')

        # Create athletes - Key players from the 1999 treble-winning squad
        # Assumptions: Using realistic names from that era, formatted for usernames
        athletes_data = [
            ('Peter', 'Schmeichel', 'GK'),
            ('Gary', 'Neville', 'RB'),
            ('Denis', 'Irwin', 'LB'),
            ('Jaap', 'Stam', 'CB'),
            ('Ronny', 'Johnsen', 'CB'),
            ('David', 'Beckham', 'RM'),
            ('Paul', 'Scholes', 'CM'),
            ('Roy', 'Keane', 'CM'),
            ('Ryan', 'Giggs', 'LM'),
            ('Andy', 'Cole', 'ST'),
            ('Dwight', 'Yorke', 'ST'),
            ('Teddy', 'Sheringham', 'ST'),
            ('Ole Gunnar', 'Solskjær', 'ST'),
            ('Nicky', 'Butt', 'CM'),
            ('Jesper', 'Blomqvist', 'LM'),
            ('Henning', 'Berg', 'CB'),
            ('Wes', 'Brown', 'CB'),
            ('Phil', 'Neville', 'LB'),
            ('David', 'May', 'CB'),
            ('Jonathan', 'Greening', 'CM'),
        ]

        athlete_users = []
        for first_name, last_name, position in athletes_data:
            # Create username from name (lowercase, replace spaces and special chars)
            username = f"{first_name.lower().replace(' ', '_')}_{last_name.lower().replace('ø', 'o').replace('æ', 'ae')}"
            email = f"{username}@manutd.com"
            
            if User.objects.filter(username=username).exists():
                user = User.objects.get(username=username)
                self.stdout.write(f'Athlete {user.get_full_name()} already exists.')
            else:
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password='athlete123',
                    first_name=first_name,
                    last_name=last_name
                )
                user.profile.role = Profile.Role.ATHLETE
                user.profile.team = team
                user.profile.teams.add(team)
                user.profile.save()
                self.stdout.write(f'Created athlete: {user.get_full_name()} ({position})')
            
            athlete_users.append(user)

        self.stdout.write(f'Created {len(athlete_users)} athletes for {team.name}')

        # Create reports from today until end of December
        today = timezone.now().date()
        # Calculate end date: December 31st of current year
        end_date = date(today.year, 12, 31)
        
        # Calculate number of days from today to end of December
        days_ahead = (end_date - today).days + 1
        
        if days_ahead <= 0:
            self.stdout.write(
                self.style.WARNING(
                    f'End date ({end_date}) is in the past. No future reports will be created.'
                )
            )
        else:
            reports_created = 0
            
            self.stdout.write(f'Generating readiness reports from {today} until {end_date} ({days_ahead} days)...')
            
            for day_offset in range(days_ahead):
                report_date = today + timedelta(days=day_offset)
                
                for athlete in athlete_users:
                    # Check if report already exists for this date
                    if ReadinessReport.objects.filter(athlete=athlete, date_created=report_date).exists():
                        continue
                    
                    # 90% chance of submitting a report on any given day
                    if random.random() < 0.90:
                        # Generate realistic metrics with some variation
                        # Base values that vary slightly per athlete
                        # Assumptions: Elite athletes generally have good metrics, but with realistic variation
                        base_sleep = random.randint(7, 9)  # Elite athletes prioritize sleep
                        base_energy = random.randint(6, 9)
                        base_soreness = random.randint(6, 10)  # Higher is better (less sore)
                        base_mood = random.randint(7, 9)  # High-performing team, good morale
                        base_motivation = random.randint(7, 10)  # Treble-winning season motivation
                        base_nutrition = random.randint(6, 9)  # Professional nutrition support
                        base_hydration = random.randint(7, 9)  # Professional hydration protocols

                        # Add some day-to-day variation
                        sleep_quality = max(1, min(10, base_sleep + random.randint(-2, 1)))
                        energy_fatigue = max(1, min(10, base_energy + random.randint(-2, 2)))
                        muscle_soreness = max(1, min(10, base_soreness + random.randint(-2, 2)))
                        mood_stress = max(1, min(10, base_mood + random.randint(-2, 1)))
                        motivation = max(1, min(10, base_motivation + random.randint(-1, 1)))
                        nutrition_quality = max(1, min(10, base_nutrition + random.randint(-2, 1)))
                        hydration = max(1, min(10, base_hydration + random.randint(-2, 1)))

                        # Create the report
                        report = ReadinessReport.objects.create(
                            athlete=athlete,
                            date_created=report_date,
                            sleep_quality=sleep_quality,
                            energy_fatigue=energy_fatigue,
                            muscle_soreness=muscle_soreness,
                            mood_stress=mood_stress,
                            motivation=motivation,
                            nutrition_quality=nutrition_quality,
                            hydration=hydration,
                            comments=self._generate_random_comment() if random.random() < 0.3 else ''
                        )
                        reports_created += 1

            self.stdout.write(f'Created {reports_created} readiness reports')

        # Summary
        self.stdout.write(
            self.style.SUCCESS(
                f'\nManchester United 1999 team created successfully!\n'
                f'- Team: {team.name}\n'
                f'- Coach: {coach.get_full_name()}\n'
                f'- Athletes: {len(athlete_users)}\n'
                f'- Reports: {ReadinessReport.objects.filter(athlete__in=athlete_users).count()}\n\n'
                f'Login credentials:\n'
                f'- Coach: {coach_username} / coach123\n'
                f'- Athletes: [firstname_lastname] / athlete123\n'
                f'  (e.g., peter_schmeichel, david_beckham, ryan_giggs, etc.)'
            )
        )

    def _generate_random_comment(self):
        comments = [
            "Feeling sharp and ready for training.",
            "Great session yesterday, feeling strong.",
            "Excellent sleep, fully recovered.",
            "Feeling motivated and focused.",
            "Ready to perform at the highest level.",
            "Well rested and energized.",
            "Feeling confident and prepared.",
            "Good recovery day, body feeling fresh.",
            "Training intensity was high, feeling good.",
            "Focused and ready for the challenge ahead.",
            "Feeling strong after yesterday's session.",
            "Well hydrated and fueled for performance.",
            "Mentally and physically prepared.",
            "Feeling sharp and ready to compete.",
            "Good energy levels, ready to go.",
        ]
        return random.choice(comments)

