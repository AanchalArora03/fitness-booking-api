"""Run from the project root: python -m unittest discover -s test -v."""
import os
os.environ.setdefault("JWT_SECRET_KEY", "test-only-signing-key-not-for-production-123456789")

import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Barrier
from unittest.mock import patch

import jwt
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select, func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from api.dependencies import get_db
from core.config import JWT_ALGORITHM, JWT_SECRET_KEY
from core.security import create_access_token, verify_password
from db.base import Base
from main import app
from models.booking import Booking
from models.fitness_class import FitnessClass
from models.user import User
from repositories import booking_repository
from schemas.booking import BookingCreate
from services.booking_service import book_class
from services.class_service import format_ist


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.engine = create_engine(
            f"sqlite:///{Path(self.temp.name) / 'test.db'}",
            connect_args={"check_same_thread": False, "timeout": 30},
        )
        @event.listens_for(self.engine, "connect")
        def foreign_keys(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")
        Base.metadata.create_all(self.engine)
        def override():
            with Session(self.engine) as db:
                yield db
        app.dependency_overrides[get_db] = override
        self.client = TestClient(app)
        self.future = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
        # Fixture users don't log in; login itself is covered by the auth test.
        with Session(self.engine) as db:
            db.add_all([User(name=f"User {i}", email=f"user{i}@example.com", hashed_password="fixture") for i in range(1, 7)])
            db.commit()

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.clear()
        self.engine.dispose()
        self.temp.cleanup()

    def headers(self, user_id=1):
        return {"Authorization": "Bearer " + create_access_token(user_id)}

    def create_class(self, slots=2):
        response = self.client.post('/classes', headers=self.headers(), json={
            'name': ' Yoga ', 'dateTime': self.future,
            'instructor': ' Alice ', 'availableSlots': slots,
        })
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def booking(self, class_id):
        return {'class_id': class_id, 'client_name': 'Guest', 'client_email': 'guest@example.com'}

    def test_signup_login_and_tokens(self):
        data = {'name': ' Alice ', 'email': 'Alice@example.com', 'password': 'example-password'}
        response = self.client.post('/signup', json=data)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(set(response.json()), {'id', 'name', 'email'})
        self.assertEqual(self.client.post('/signup', json=data).status_code, 409)
        with Session(self.engine) as db:
            user = db.get(User, response.json()['id'])
            self.assertNotEqual(user.hashed_password, data['password'])
            self.assertTrue(verify_password(data['password'], user.hashed_password))
        login = self.client.post('/login', json={'email': 'ALICE@example.com', 'password': data['password']})
        self.assertEqual(login.status_code, 200)
        token = login.json()['access_token']
        claims = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        self.assertEqual(claims['exp'] - claims['iat'], login.json()['expires_in'])
        me = self.client.get('/me', headers={'Authorization': 'Bearer ' + token})
        self.assertEqual(me.json(), response.json())
        for email in ['alice@example.com', 'missing@example.com']:
            self.assertEqual(self.client.post('/login', json={'email': email, 'password': 'wrong'}).status_code, 401)
        for payload in [{}, dict(data, email='bad'), dict(data, password='tiny'), dict(data, name=' ')]:
            self.assertEqual(self.client.post('/signup', json=payload).status_code, 422)

    def test_protected_routes_reject_invalid_tokens(self):
        now = datetime.now(timezone.utc)
        claims = {'sub': '1', 'iat': now, 'exp': now + timedelta(minutes=5)}
        tokens = ['bad', create_access_token(999), jwt.encode(claims, 'wrong-key' * 8, algorithm=JWT_ALGORITHM)]
        for changes in [{'exp': now - timedelta(seconds=1)}, {'sub': 'not-an-id'}, {'sub': '9' * 100}]:
            tokens.append(jwt.encode(claims | changes, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM))
        tokens.append(jwt.encode({'sub': '1', 'iat': now}, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM))
        for token in tokens:
            response = self.client.get('/me', headers={'Authorization': 'Bearer ' + token})
            self.assertEqual(response.status_code, 401)
            self.assertEqual(response.headers['www-authenticate'], 'Bearer')
        for method, path in [('get', '/me'), ('get', '/bookings'), ('post', '/classes'), ('post', '/book')]:
            self.assertEqual(getattr(self.client, method)(path).status_code, 401)

    def test_classes_validation_filtering_timezone(self):
        created = self.create_class()
        self.assertEqual(created['name'], 'Yoga')
        self.assertTrue(created['dateTime'].endswith('+05:30'))
        self.assertEqual(datetime.fromisoformat(created['dateTime']), datetime.fromisoformat(self.future))
        with Session(self.engine) as db:
            db.add(FitnessClass(name='Past', instructor='Bob', available_slots=2,
                date_time=format_ist(datetime.now(timezone.utc) - timedelta(days=1))))
            db.commit()
        listing = self.client.get('/classes?timezone=America/New_York')
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(len(listing.json()), 1)
        self.assertEqual(datetime.fromisoformat(listing.json()[0]['dateTime']), datetime.fromisoformat(self.future))
        self.assertEqual(self.client.get('/classes?timezone=Invalid/Zone').status_code, 422)
        base = {'name': 'Yoga', 'instructor': 'Alice', 'dateTime': self.future, 'availableSlots': 2}
        for updates in [{'availableSlots': 0}, {'availableSlots': True}, {'name': ' '}, {'dateTime': '2020-01-01T10:00:00Z'}, {'dateTime': '2030-01-01T10:00:00'}]:
            self.assertEqual(self.client.post('/classes', headers=self.headers(), json=base | updates).status_code, 422)

    def test_booking_ownership_duplicates_and_capacity(self):
        created = self.create_class(2)
        payload = self.booking(created['id'])
        self.assertEqual(self.client.post('/book', headers=self.headers(), json=payload).status_code, 201)
        self.assertEqual(self.client.post('/book', headers=self.headers(), json=payload).status_code, 409)
        self.assertEqual(self.client.get('/classes').json()[0]['availableSlots'], 1)
        self.assertEqual(self.client.get('/bookings', headers=self.headers(2)).json(), [])
        own = self.client.get('/bookings?timezone=UTC', headers=self.headers()).json()
        self.assertEqual(len(own), 1)
        self.assertTrue(own[0]['fitness_class']['dateTime'].endswith('Z'))
        self.assertEqual(self.client.post('/book', headers=self.headers(2), json=payload).status_code, 201)
        self.assertEqual(self.client.post('/book', headers=self.headers(3), json=payload).status_code, 409)
        self.assertEqual(self.client.get('/classes').json()[0]['availableSlots'], 0)
        self.assertEqual(self.client.post('/book', headers=self.headers(), json=self.booking(999)).status_code, 404)
        self.assertEqual(self.client.post('/book', headers=self.headers(), json={}).status_code, 422)

    def test_past_class_cannot_be_booked(self):
        created = self.create_class()
        with Session(self.engine) as db:
            item = db.get(FitnessClass, created['id'])
            item.date_time = format_ist(datetime.now(timezone.utc) - timedelta(days=1))
            db.commit()
        self.assertEqual(self.client.post('/book', headers=self.headers(), json=self.booking(created['id'])).status_code, 409)

    def test_booking_failure_restores_slot(self):
        created = self.create_class(1)
        with Session(self.engine) as db:
            with patch.object(booking_repository, 'create_booking', side_effect=SQLAlchemyError('test failure')):
                with self.assertRaises(SQLAlchemyError):
                    book_class(db, 1, BookingCreate(**self.booking(created['id'])))
            self.assertEqual(db.get(FitnessClass, created['id']).available_slots, 1)
            self.assertEqual(db.scalar(select(func.count()).select_from(Booking)), 0)

    def test_concurrent_requests_cannot_overbook(self):
        created = self.create_class(1)
        barrier = Barrier(6)
        def reserve(user_id):
            with TestClient(app) as client:
                barrier.wait(timeout=10)
                return client.post('/book', headers=self.headers(user_id), json=self.booking(created['id'])).status_code
        with ThreadPoolExecutor(max_workers=6) as pool:
            statuses = list(pool.map(reserve, range(1, 7)))
        self.assertEqual(statuses.count(201), 1, statuses)
        self.assertEqual(statuses.count(409), 5, statuses)
        with Session(self.engine) as db:
            self.assertEqual(db.get(FitnessClass, created['id']).available_slots, 0)
            self.assertEqual(db.scalar(select(func.count()).select_from(Booking)), 1)


if __name__ == '__main__':
    unittest.main()
