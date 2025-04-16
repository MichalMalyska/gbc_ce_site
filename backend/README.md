# GBC Course Catalog Backend

Django REST API for serving GBC continuing education course data.

## Features
- Course listing and filtering
- Schedule management
- Pagination support
- Filter options:
  - Course code/name search
  - Department (prefix) filter
  - Day of week filter
  - Time of day filter
  - Delivery type filter

## Getting Started

### Prerequisites
- Python 3.8+
- pip
- virtualenv (recommended)

### Installation
```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate
```

### Development

```bash
python manage.py runserver
```

The API will be available at `http://localhost:8000/api/`

### API Endpoints

#### Courses
- `GET /api/courses/`
  - Query Parameters:
    - `search`: Search in course code and name
    - `day`: Filter by day of week
    - `start_after`: Filter by start time
    - `end_before`: Filter by end time
    - `delivery_type`: Filter by delivery method
    - `has_schedules`: Only show courses with schedules

#### Course Prefixes
- `GET /api/courses/prefixes/`
  - Returns list of unique course prefixes

## Project Structure
```
course_api/
  ├── courses/       # Main app
  │   ├── models.py    # Database models
  │   ├── views.py     # API views
  │   └── serializers.py # Data serializers
  └── course_api/    # Project settings
```

## Data Model
- Course
  - Basic course information
  - Delivery type
  - Fees and hours
- Schedule
  - Day and time information
  - Date ranges
  - Linked to courses

## Environment Setup

1. Create a production environment file:
```bash
cp .env.example .env.production
```

2. Edit the production environment file with your secure credentials:
```bash
nano .env.production
```

3. Store the environment file in a secure location:
```bash
# Example: move to a restricted directory
sudo mkdir -p /etc/gbc-courses
sudo mv .env.production /etc/gbc-courses/
sudo chown root:root /etc/gbc-courses/.env.production
sudo chmod 600 /etc/gbc-courses/.env.production
```

⚠️ Security Notes:
- Never commit environment files to version control
- Restrict access to production environment files
- Regularly rotate database credentials
- Use strong, unique passwords
- Consider using a secrets management service for production
