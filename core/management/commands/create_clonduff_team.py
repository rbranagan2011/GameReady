from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.utils import timezone
from django.conf import settings
from datetime import timedelta
import random
from core.models import Team, Profile, ReadinessReport


class Command(BaseCommand):
    help = 'Create Clonduff Senior Footballers team with coach and athletes, including 2 months of data'

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
        
        self.stdout.write('Creating Clonduff Senior Footballers team...')

        # Create team
        team, created = Team.objects.get_or_create(name="Clonduff Senior Footballers")
        if created:
            self.stdout.write(f'Created team: {team.name}')
        else:
            self.stdout.write(f'Team {team.name} already exists. Skipping team creation.')
            return

        # Create coach
        coach_username = 'ryan_mcshane'
        coach_email = 'ryan.mcshane@clonduff.com'
        
        if User.objects.filter(username=coach_username).exists():
            coach = User.objects.get(username=coach_username)
            self.stdout.write(f'Coach {coach.get_full_name()} already exists.')
        else:
            coach = User.objects.create_user(
                username=coach_username,
                email=coach_email,
                password='coach123',
                first_name='Ryan',
                last_name='McShane'
            )
            coach.profile.role = Profile.Role.COACH
            coach.profile.team = team
            coach.profile.teams.add(team)
            coach.profile.save()
            self.stdout.write(f'Created coach: {coach.get_full_name()}')

        # Create athletes
        athletes_data = [
            ('Rian', 'Branagan'),
            ('Patrick', 'Branagan'),
            ('Aaron', 'Sherry'),
            ('Mark', 'Devlin'),
            ('Brendy', 'Britton'),
            ('Darren', "O'Hagan"),
            ('Jamie', "O'Hagan"),
            ('Packie', "O'Hagan"),
            ('John', 'Brown'),
            ('Jamie', 'Gribben'),
            ('Conor', 'Murray'),
            ('Eamon', 'Brown'),
            ('Dan', 'Rafferty'),
            ('Shane', 'Close'),
            ('Tom', 'Close'),
            ('Aidan', 'Carr'),
            ('Ross', 'Carr'),
            ('Charlie', 'Carr'),
            ('Steve', 'McConville'),
            ('Arthur', 'McConville'),
            ('Senan', 'Carr'),
        ]

        athlete_users = []
        for first_name, last_name in athletes_data:
            # Create username from name (lowercase, replace spaces and special chars)
            username = f"{first_name.lower()}_{last_name.lower().replace("'", '').replace('-', '_')}"
            email = f"{username}@clonduff.com"
            
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
                self.stdout.write(f'Created athlete: {user.get_full_name()}')
            
            athlete_users.append(user)

        self.stdout.write(f'Created {len(athlete_users)} athletes for {team.name}')

        # Create reports for the last 2 months (60 days)
        today = timezone.now().date()
        reports_created = 0
        
        self.stdout.write('Generating readiness reports for the last 2 months...')
        
        for days_ago in range(60):
            date = today - timedelta(days=days_ago)
            
            for athlete in athlete_users:
                # Check if report already exists for this date
                if ReadinessReport.objects.filter(athlete=athlete, date_created=date).exists():
                    continue
                
                # 85% chance of submitting a report on any given day
                if random.random() < 0.85:
                    # Generate realistic metrics with some variation
                    # Base values that vary slightly per athlete
                    base_sleep = random.randint(6, 9)
                    base_energy = random.randint(5, 9)
                    base_soreness = random.randint(6, 10)  # Higher is better (less sore)
                    base_mood = random.randint(6, 9)
                    base_motivation = random.randint(5, 9)
                    base_nutrition = random.randint(5, 8)
                    base_hydration = random.randint(6, 9)

                    # Add some day-to-day variation
                    sleep_quality = max(1, min(10, base_sleep + random.randint(-2, 2)))
                    energy_fatigue = max(1, min(10, base_energy + random.randint(-2, 2)))
                    muscle_soreness = max(1, min(10, base_soreness + random.randint(-2, 2)))
                    mood_stress = max(1, min(10, base_mood + random.randint(-2, 2)))
                    motivation = max(1, min(10, base_motivation + random.randint(-2, 2)))
                    nutrition_quality = max(1, min(10, base_nutrition + random.randint(-2, 2)))
                    hydration = max(1, min(10, base_hydration + random.randint(-2, 2)))

                    # Create the report
                    report = ReadinessReport.objects.create(
                        athlete=athlete,
                        date_created=date,
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
                f'\nClonduff Senior Footballers team created successfully!\n'
                f'- Team: {team.name}\n'
                f'- Coach: {coach.get_full_name()}\n'
                f'- Athletes: {len(athlete_users)}\n'
                f'- Reports: {reports_created}\n\n'
                f'Login credentials:\n'
                f'- Coach: {coach_username} / coach123\n'
                f'- Athletes: [firstname_lastname] / athlete123\n'
                f'  (e.g., rian_branagan, patrick_branagan, etc.)'
            )
        )

    def _generate_random_comment(self):
        comments = [
            "Feeling good today!",
            "Had a tough training session yesterday.",
            "Great sleep last night.",
            "Feeling a bit tired.",
            "Ready for training!",
            "Need to focus on hydration.",
            "Feeling strong and motivated.",
            "Had some stress at work.",
            "Recovery day was helpful.",
            "Looking forward to practice.",
            "Feeling sharp after the weekend.",
            "Slight muscle tightness from yesterday's game.",
            "Well rested and ready to go.",
            "Good energy levels today.",
            "Focused and prepared.",
        ]
        return random.choice(comments)

