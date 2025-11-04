# GameReady

A Django web application for tracking daily athlete wellness metrics to help coaches optimize training and reduce injury risk.

## Features

### For Athletes
- **Join A Team**: Join your sports team and log your wellness metrics to keep your coach informed on your wellbeing
- **Daily Wellness Reporting**: Submit daily readiness reports with 7 key metrics
- **Historical View**: See your past submissions and readiness scores
- **Automatic Scoring**: System calculates your readiness percentage automatically
- **Trends And Insights**: Receive personalised insights on strengths, weaknesses and areas for improvement

### For Coaches
- **Squad Dashboard**: Overview of all athletes' readiness scores in an easily digestible format
- **Monthly And Weekly Overviews**: Track team condition over time
- **Individual Athlete Details**: Deep dive into specific athlete metrics
- **Schedule Manager**: Create a personalised schedule specific to your team's training and games
- **Compliance Tracking**: Monitor who has/hasn't submitted reports
- **Color-Coded Scores**: Quick visual assessment of team readiness

### Wellness Metrics Tracked
1. **Sleep Quality** (1-10): Sleep duration and quality
2. **Energy/Fatigue** (1-10): Current energy levels
3. **Muscle Soreness/Stiffness** (1-10): Recovery status
4. **Mood/Stress** (1-10): Mental state and stress levels
5. **Motivation to Train** (1-10): Training motivation
6. **Nutrition Quality** (1-10): Fueling and meal quality
7. **Hydration** (1-10): Hydration status

## Installation & Setup

### Prerequisites
- Python 3.8+
- pip (Python package installer)

### Quick Start

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd GameReady
   ```

2. **Create and activate virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Optional: create a .env file**
   The app will generate `.env` with a random `SECRET_KEY` on first run. If you want to set values ahead of time, create it manually:
   ```bash
   cat > .env <<'EOF'
   # Replace the secret below with the output of the command that follows.
   SECRET_KEY=replace-with-random-secret
   DEBUG=True
   ALLOWED_HOSTS=localhost,127.0.0.1
   EOF
   ```

   Generate a random secret to paste into the file:
   ```bash
   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
   ```

5. **Run migrations**
   ```bash
   python manage.py migrate
   ```

6. **Create sample data (optional)**
   ```bash
   python manage.py create_sample_data
   ```

7. **Start the development server**
   ```bash
   python manage.py runserver
   ```

8. **Access the application**
   - Open your browser to `http://127.0.0.1:8000`
   - Login with sample credentials (see below)

## Sample Login Credentials

After running `create_sample_data`, you can use these accounts:

### Coach Account
- **Username**: `coach_smith`
- **Password**: `coach123`
- **Access**: Full coach dashboard with team management

### Athlete Accounts
- **Username**: `alex_johnson`, `maya_patel`, `james_wilson`, `sophia_garcia`, `tyler_brown`
- **Password**: `athlete123`
- **Access**: Daily reporting interface

### Admin Account
- **Username**: `admin`
- **Password**: `admin123`
- **Access**: Django admin interface at `/admin/`

> These passwords are for local demos only—never reuse them for staging or production deployments.

## Usage

### For Athletes
1. **Login** with your athlete credentials
2. **Submit Daily Report**: Rate each wellness metric on a 1-10 scale
3. **View Results**: See your calculated readiness score
4. **Check History**: Review past submissions

### For Coaches
1. **Login** with coach credentials
2. **View Dashboard**: See team overview and today's scores
3. **Analyze Trends**: Review team performance
4. **Drill Down**: Click athlete names for detailed history
5. **Monitor Compliance**: Track who has/hasn't submitted reports

### For Administrators
1. **Access Admin**: Go to `/admin/` and login with admin credentials
2. **Manage Teams**: Create and edit teams
3. **User Management**: Create users and assign roles
4. **Data Export**: View and export all readiness reports

## Technical Details

### Architecture
- **Backend**: Django 5.2.7 with SQLite database
- **Frontend**: Bootstrap 5 with responsive design
- **Authentication**: Django's built-in auth system
- **Database**: Django ORM with automatic migrations

### Key Models
- **Team**: Groups athletes and coaches
- **Profile**: Extends User model with role and team assignment
- **ReadinessReport**: Stores daily wellness metrics and calculated scores

### Readiness Score Calculation
The system calculates a percentage-based readiness score by:
1. Averaging all 7 wellness metrics (each 1-10 scale)
2. Converting to percentage: `(total_score / 70) * 100`
3. Rounding to nearest whole number

### Security Features
- Role-based access control (Athletes vs Coaches)
- Team isolation (coaches only see their team)
- One report per athlete per day constraint
- CSRF protection on all forms

## Development

### Project Structure
```
GameReady/
├── GameReady/     # Django project settings
├── core/                  # Main application
│   ├── models.py         # Database models
│   ├── views.py          # View logic
│   ├── forms.py          # Form definitions
│   ├── admin.py          # Admin interface
│   └── templates/        # HTML templates
├── templates/            # Base templates
├── static/              # Static files (CSS, JS)
└── manage.py            # Django management script
```

### Adding New Features
1. **Models**: Add new fields to existing models or create new ones
2. **Views**: Create new views in `core/views.py`
3. **Templates**: Add HTML templates in `templates/core/`
4. **URLs**: Update `core/urls.py` with new routes
5. **Migrations**: Run `python manage.py makemigrations` and `migrate`

### Customization
- **Metrics**: Modify the 7 wellness metrics in `models.py` and `forms.py`
- **Scoring**: Adjust the readiness calculation in `ReadinessReport.calculate_readiness_score()`
- **Styling**: Update Bootstrap classes in templates or add custom CSS
- **Teams**: Add team-specific features by extending the Team model

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For questions or issues:
1. Check the Django documentation
2. Review the code comments
3. Create an issue in the repository
4. Contact the development team

---

**Built with ❤️ using Django and Bootstrap**
