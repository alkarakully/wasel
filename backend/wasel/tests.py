from unittest import mock

from django.test import TestCase


class HealthCheckTests(TestCase):
    def test_ok_when_database_reachable(self):
        response = self.client.get("/healthz/")
        self.assertEqual((response.status_code, response.json()), (200, {"status": "ok"}))

    def test_503_when_database_down(self):
        with mock.patch("wasel.urls.connection.ensure_connection", side_effect=Exception("down")):
            self.assertEqual(self.client.get("/healthz/").status_code, 503)
