from datetime import timedelta
from unittest import mock

from django.test import TestCase, override_settings
from django.utils import timezone

from accounts.models import User
from accounts.otp import verify_code
from accounts.tests import TEST_OTP

from .models import NawsilPlusSubscription
from .tasks import expire_nawsil_plus_trials

Status = NawsilPlusSubscription.Status


@override_settings(OTP=TEST_OTP, NAWSIL_PLUS_TRIAL_DAYS=14)
class TrialStartTests(TestCase):
    def login(self, phone):
        from accounts import otp
        from accounts.tests import RecordingSender

        RecordingSender.sent, RecordingSender.failing = [], set()
        otp.request_code(phone)
        return verify_code(phone, RecordingSender.sent[-1][2])

    def test_first_login_starts_a_14_day_trial(self):
        user, created = self.login("+9647701112233")
        self.assertTrue(created)
        trial = NawsilPlusSubscription.objects.get(user=user)
        self.assertEqual(trial.status, Status.TRIAL)
        self.assertAlmostEqual((trial.trial_end_date - trial.trial_start_date).total_seconds(), 14 * 86400, delta=1)

    def test_returning_user_does_not_get_another_trial(self):
        User.objects.create_user(phone="+9647701112233")
        self.login("+9647701112233")
        self.assertFalse(NawsilPlusSubscription.objects.exists())


@mock.patch("subscriptions.tasks.notify_user")
class TrialExpiryTests(TestCase):
    def sub(self, phone, status, ends_in_days):
        user = User.objects.create_user(phone=phone)
        return NawsilPlusSubscription.objects.create(
            user=user, status=status, trial_end_date=timezone.now() + timedelta(days=ends_in_days)
        )

    def test_expires_only_finished_trials_and_tells_the_app(self, notify):
        ended = self.sub("+9647700000070", Status.TRIAL, -1)
        running = self.sub("+9647700000071", Status.TRIAL, 3)
        paid = self.sub("+9647700000072", Status.ACTIVE, -30)

        self.assertEqual(expire_nawsil_plus_trials(), {"expired": 1})

        statuses = dict(NawsilPlusSubscription.objects.values_list("pk", "status"))
        self.assertEqual(statuses, {ended.pk: Status.EXPIRED, running.pk: Status.TRIAL, paid.pk: Status.ACTIVE})
        notify.assert_called_once_with(ended.user_id, {"type": "nawsil_plus.trial_ended"})

    def test_nothing_to_do(self, notify):
        self.assertEqual(expire_nawsil_plus_trials(), {"expired": 0})
        notify.assert_not_called()
