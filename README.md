# Football Tournament Management Website

Web app for managing a single football tournament (16 teams, 4 groups) with friends.  
It covers group draws, schedules, rankings, and knockout phases, plus a small admin area.

## Features
- Group stage rankings with tie-breakers
- Knockout bracket (quarters → semis → finals)
- Top scorers + MVP ranking
- Group draw with animated UI
- Match details (scorers + MVP)

## Tech Stack
- Backend: Python, Django
- Frontend: Django templates, HTML/CSS, vanilla JS
- DB: PostgreSQL (Neon)
- Media: Cloudinary
- Deploy: Render

## Local Setup
1. Create a virtualenv and install deps:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. Configure environment variables (see `.env` example below).
3. Run migrations and start server:
   ```bash
   python football_tournament/manage.py migrate
   python football_tournament/manage.py runserver
   ```

## Environment Variables
```
SECRET_KEY=your_secret
DEBUG=True
DATABASE_URL=postgres://...
```

## Useful Commands
Initialize tournament data:
```bash
python football_tournament/manage.py init_tournament
```

Run simulation:
```bash
python football_tournament/manage.py simulate_tournament
```

Create/check superuser:
```bash
python football_tournament/manage.py createsuperuser
python football_tournament/manage.py checksuperuser
```

## Project Structure
```
football_tournament/
  tournament/
    domain/          # ranking, knockout logic
    services/        # schedule, draw, ranking services
    templates/       # HTML templates
    static/          # CSS, images
```

## Notes
- The app assumes 16 teams split into 4 groups.
- Knockout tie handling is encoded in final scores (DTS/DCR included).
