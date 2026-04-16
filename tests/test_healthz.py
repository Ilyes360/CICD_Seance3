from django.test import TestCase


class HealthTests(TestCase):
    def test_health_returns_fields(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("status", payload)
        self.assertIn("database", payload)
        self.assertIn("cache", payload)
