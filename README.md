# Fitness Studio Booking API

A Python and FastAPI backend for registering users, creating fitness classes,
booking available slots, and viewing personal booking history. SQLite stores
the data, SQLAlchemy handles persistence, and Argon2 password hashing plus
expiring JWT bearer tokens provide authentication.

## Requirements

- Python 3.12
- A terminal; no separate database server is needed

## Setup

Run these commands from the repository root (your local `project/backend` folder):

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Paste the generated value after `JWT_SECRET_KEY=` in `.env`. Leave
`ACCESS_TOKEN_EXPIRE_MINUTES=30` unless you want a different token lifetime.
Keep `.env` private. For an existing setup, preserve your existing `.env` rather
than replacing it. Environment variables override the values in this file.

Create the database tables and optional sample classes:

```bash
python -m db.create_tables
python -m scripts.seed
```

The database is `fitness.db`. The seed script creates Yoga, Zumba, and
HIIT classes on upcoming days in IST. It skips a sample class when an upcoming
class with that name already exists. It does not create accounts or passwords.

## Run locally

```bash
python -m uvicorn main:app --reload
```

- Swagger UI: <http://127.0.0.1:8000/docs>
- ReDoc: <http://127.0.0.1:8000/redoc>
- Health check: <http://127.0.0.1:8000/health>

Keep the terminal running. Press Ctrl+C to stop. The root URL `/` has no route.

## Architecture

```text
fitness-booking-api/    # Locally: project/backend
├── api/               # HTTP routes and request dependencies
├── core/              # Configuration, security, application exceptions
├── db/                # Engine, sessions, model base, table creation
├── models/            # SQLAlchemy table definitions
├── repositories/      # Database queries; no independent commits
├── schemas/           # Request validation and response definitions
├── services/          # Business rules and transaction ownership
├── scripts/           # Sample data
├── test/              # Automated tests
├── main.py
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

Requests flow through routes, services, and repositories. Database sessions are
closed after requests. Authenticated identity comes from the verified token,
not an email or user ID supplied in a booking request.

## Endpoints

| Method | Path | Authentication | Purpose |
| --- | --- | --- | --- |
| POST | `/signup` | Public | Register a user (201) |
| POST | `/login` | Public | Return an access token (200) |
| GET | `/me` | Bearer token | Return the authenticated account |
| POST | `/classes` | Bearer token | Create a future class (201) |
| GET | `/classes` | Public | List upcoming classes chronologically |
| POST | `/book` | Bearer token | Book one available slot (201) |
| GET | `/bookings` | Bearer token | List only your bookings |
| GET | `/health` | Public | Check that the application runs |

## API examples

Use these commands in a separate terminal while the server runs.

### Register

```bash
curl -i -X POST http://127.0.0.1:8000/signup \
  -H 'Content-Type: application/json' \
  -d '{"name":"Alice","email":"alice@example.com","password":"MyStrongPassword123"}'
```

### Log in

```bash
curl -s -X POST http://127.0.0.1:8000/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"alice@example.com","password":"MyStrongPassword123"}'
```

Copy the returned `access_token` into this shell variable:

```bash
TOKEN='paste-your-access-token-here'
curl -i http://127.0.0.1:8000/me -H "Authorization: Bearer $TOKEN"
```

Tokens expire after 30 minutes by default. Log in again to get a new token.
Refresh tokens and logout/revocation are not implemented. In Swagger, click
**Authorize** and paste only the token, without the `Bearer` prefix.

### Create a class

Use a future, timezone-aware date. Change the date below if necessary:

```bash
curl -i -X POST http://127.0.0.1:8000/classes \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"name":"Yoga Flow","dateTime":"2030-06-15T10:00:00+05:30","instructor":"John Doe","availableSlots":20}'
```

### List upcoming classes

```bash
curl -s http://127.0.0.1:8000/classes
curl -s 'http://127.0.0.1:8000/classes?timezone=America/New_York'
```

### Book a class

Replace `class_id` with the ID returned by class creation or listing:

```bash
curl -i -X POST http://127.0.0.1:8000/book \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"class_id":1,"client_name":"Alice","client_email":"alice@example.com"}'
```

### View your bookings

```bash
curl -s http://127.0.0.1:8000/bookings -H "Authorization: Bearer $TOKEN"
curl -s 'http://127.0.0.1:8000/bookings?timezone=UTC' -H "Authorization: Bearer $TOKEN"
```

Each booking includes its ID, client details, class ID, and a nested
`fitness_class` object. The nested `availableSlots` is the current remaining
capacity, not a snapshot from when the booking was created.

## Timezones

Input dates must include an offset or `Z`; naive dates are rejected. The service
converts them to `Asia/Kolkata` before storage. SQLite stores canonical ISO 8601
strings with six fractional digits and `+05:30`, so date comparisons and sorting
work consistently. Always use the service to insert class timestamps.

Responses default to IST. `GET /classes` and `GET /bookings` accept a `timezone`
query parameter with an IANA timezone name. Conversion changes the displayed
time, not the stored instant. Invalid zones return 422.

## Booking rules and errors

- Only authenticated users can create classes, book, or view their bookings.
- Class names and instructor names cannot be blank. New classes need a future
  date and a positive integer number of slots.
- One booking per user per class is enforced by a database unique constraint.
- Booking ownership always belongs to the token's user, even if the submitted
  client email differs. Client details are contact information.
- Slot reservation is an atomic conditional update. It checks both future start
  time and remaining capacity. Reservation and booking insertion share one
  transaction, which rolls back on failure. SQLite waits up to 30 seconds for
  a write lock; it is intended here for a small development deployment.
- Passwords are hashed with Argon2. JWTs are verified with a fixed HS256
  algorithm and required identity, issued-at, and expiration claims.
- Request logs include method, path, status, and duration, not passwords or tokens.

| Status | Meaning |
| --- | --- |
| 401 | Missing, invalid, or expired authentication; incorrect login |
| 404 | Class does not exist |
| 409 | Duplicate email/booking, full class, or class already started |
| 422 | Missing or invalid request fields or unsupported timezone |

## Tests

```bash
python -m unittest discover -s test -v
```

Tests use temporary SQLite databases and do not alter your local accounts or
bookings. They cover signup/login, password hashing, token failures, input
validation, timezone conversion, upcoming filtering, booking privacy, duplicate
bookings, rollback, and six concurrent requests competing for one slot.

## Development limitations

`create_all` creates missing tables; it does not migrate existing table schemas.
Use migrations before changing an existing schema. This assignment has no
admin roles, email verification, password reset, cancellation, refresh tokens,
or frontend. Class creation is available to every authenticated user as requested.

## Submission checklist

- Run the tests and try the endpoints in Swagger.
- Preview this README in GitHub and in the [readme.so editor](https://readme.so/editor)
  as required by the assignment. The interactive editor check must be completed
  before submission.
- Create a public GitHub repository and push the source, tests, seed script,
  README, and dependency file. Do not commit `.env`, `.venv`, or `fitness.db`.
- Submit the public repository URL at the
  [assignment submission page](https://www.starlabs.co.in/assignment).
