from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
import random
from core.models import Team, Profile, ReadinessReport


class Command(BaseCommand):
    help = 'Create sample data for testing the GameReady app'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before creating sample data',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing data...')
            ReadinessReport.objects.all().delete()
            Profile.objects.all().delete()
            User.objects.all().delete()
            Team.objects.all().delete()

        self.stdout.write('Creating sample data...')

        # Create teams
        team1 = Team.objects.create(name="Thunder Basketball")
        team2 = Team.objects.create(name="Lightning Soccer")
        
        self.stdout.write(f'Created teams: {team1.name}, {team2.name}')

        # Create coach
        coach = User.objects.create_user(
            username='coach_smith',
            email='coach@example.com',
            password='coach123',
            first_name='Sarah',
            last_name='Smith'
        )
        coach.profile.role = Profile.Role.COACH
        coach.profile.team = team1
        coach.profile.save()

        self.stdout.write(f'Created coach: {coach.get_full_name()}')

        # Create athletes for team 1
        athletes_team1 = [
            ('alex_johnson', 'Alex', 'Johnson', 'alex@example.com'),
            ('maya_patel', 'Maya', 'Patel', 'maya@example.com'),
            ('james_wilson', 'James', 'Wilson', 'james@example.com'),
            ('sophia_garcia', 'Sophia', 'Garcia', 'sophia@example.com'),
            ('tyler_brown', 'Tyler', 'Brown', 'tyler@example.com'),
        ]

        for username, first_name, last_name, email in athletes_team1:
            user = User.objects.create_user(
                username=username,
                email=email,
                password='athlete123',
                first_name=first_name,
                last_name=last_name
            )
            user.profile.role = Profile.Role.ATHLETE
            user.profile.team = team1
            user.profile.save()

        # Create athletes for team 2
        athletes_team2 = [
            ('emma_davis', 'Emma', 'Davis', 'emma@example.com'),
            ('liam_martinez', 'Liam', 'Martinez', 'liam@example.com'),
            ('olivia_taylor', 'Olivia', 'Taylor', 'olivia@example.com'),
        ]

        for username, first_name, last_name, email in athletes_team2:
            user = User.objects.create_user(
                username=username,
                email=email,
                password='athlete123',
                first_name=first_name,
                last_name=last_name
            )
            user.profile.role = Profile.Role.ATHLETE
            user.profile.team = team2
            user.profile.save()

        self.stdout.write(f'Created {len(athletes_team1)} athletes for {team1.name}')
        self.stdout.write(f'Created {len(athletes_team2)} athletes for {team2.name}')

        # Create historical reports (last 14 days)
        today = timezone.now().date()
        all_athletes = User.objects.filter(profile__role=Profile.Role.ATHLETE)

        for days_ago in range(14):
            date = today - timedelta(days=days_ago)
            
            for athlete in all_athletes:
                # 90% chance of submitting a report on any given day
                if random.random() < 0.9:
                    # Generate realistic metrics with some variation
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

        self.stdout.write('Created historical reports for the last 14 days')

        # Summary
        self.stdout.write(
            self.style.SUCCESS(
                f'\nSample data created successfully!\n'
                f'- Teams: {Team.objects.count()}\n'
                f'- Users: {User.objects.count()}\n'
                f'- Reports: {ReadinessReport.objects.count()}\n\n'
                f'Login credentials:\n'
                f'- Coach: coach_smith / coach123\n'
                f'- Athletes: [username] / athlete123\n'
                f'  (e.g., alex_johnson, maya_patel, etc.)'
            )
        )

    def _generate_random_comment(self):
        comments = [
            "Feeling good today!",
            "Had a tough workout yesterday.",
            "Great sleep last night.",
            "Feeling a bit tired.",
            "Ready for training!",
            "Need to focus on hydration.",
            "Feeling strong and motivated.",
            "Had some stress at work.",
            "Recovery day was helpful.",
            "Looking forward to practice.",
        ]
        return random.choice(comments)
