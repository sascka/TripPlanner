import tempfile
import unittest
from pathlib import Path

from app import create_app
from app.config import Config
from app.extensions import db


class TestConfig(Config):
    TESTING = True
    SECRET_KEY = 'test-secret'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    UPLOAD_FOLDER = Path(tempfile.gettempdir()) / 'tripplanner-tests'
    WEATHER_API_KEY = ''


class TripPlannerSmokeTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.client = self.app.test_client()
        with self.app.app_context():
            db.create_all()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()

    def test_guest_pages_open(self):
        self.assertEqual(self.client.get('/').status_code, 200)
        self.assertEqual(self.client.get('/auth/login').status_code, 200)
        self.assertEqual(self.client.get('/auth/register').status_code, 200)

    def test_user_create_trip(self):
        reg = self.client.post(
            '/auth/register',
            data={
                'name': 'Test User',
                'email': 'test@example.com',
                'password': 'secret123',
                'pwd2': 'secret123',
            },
            follow_redirects=True,
        )
        self.assertIn('Мои поездки'.encode('utf-8'), reg.data)

        res = self.client.post(
            '/trips/new',
            data={
                'title': 'Весенняя Казань',
                'destination': 'Казань',
                'start_date': '2026-05-10',
                'end_date': '2026-05-14',
                'budget': '25000',
                'description': 'Проверить прогулочный маршрут.',
            },
            follow_redirects=True,
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn('Весенняя Казань'.encode('utf-8'), res.data)

        api = self.client.get('/api/trips')
        self.assertEqual(api.status_code, 200)
        self.assertEqual(api.json[0]['destination'], 'Казань')


if __name__ == '__main__':
    unittest.main()
