from datetime import timedelta
from unittest import mock

from django.conf import settings
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from . import otp
from .models import PhoneOTP, User
from .phone import InvalidPhone, normalize_iraqi_phone

PHONE = "+9647701234567"


class RecordingSender:
    """Test sender that keeps the last code sent per channel."""

    sent = []
    failing = set()

    def __init__(self, channel):
        self.channel = channel

    def send(self, phone, code):
        if self.channel in self.failing:
            raise otp.SendError(f"{self.channel} is down")
        self.sent.append((self.channel, phone, code))


class WhatsAppTestSender(RecordingSender):
    def __init__(self):
        super().__init__("whatsapp")


class SmsTestSender(RecordingSender):
    def __init__(self):
        super().__init__("sms")


TEST_OTP = {
    "CODE_TTL_SECONDS": 300,
    "RESEND_SECONDS": 60,
    "MAX_PER_HOUR": 5,
    "MAX_ATTEMPTS": 5,
    "SENDERS": {
        "whatsapp": "accounts.tests.WhatsAppTestSender",
        "sms": "accounts.tests.SmsTestSender",
    },
}


class PhoneNormalizationTests(TestCase):
    def test_accepts_common_iraqi_formats(self):
        for raw in [
            "07701234567",
            "0770 123 4567",
            "7701234567",
            "9647701234567",
            "+964 770 123 4567",
            "00964-770-123-4567",
            "٠٧٧٠١٢٣٤٥٦٧",  # Arabic-Indic digits
        ]:
            with self.subTest(raw=raw):
                self.assertEqual(normalize_iraqi_phone(raw), PHONE)

    def test_rejects_non_mobile_or_wrong_length(self):
        for raw in ["", "0123", "07012345678", "077012345678", "+44 7700 900123", "abc"]:
            with self.subTest(raw=raw), self.assertRaises(InvalidPhone):
                normalize_iraqi_phone(raw)


@override_settings(OTP=TEST_OTP)
class OtpFlowTests(TestCase):
    def setUp(self):
        cache.clear()
        RecordingSender.sent = []
        RecordingSender.failing = set()
        self.client = APIClient()

    def request_code(self, phone="07701234567", **extra):
        return self.client.post("/api/auth/otp/request/", {"phone": phone, **extra}, format="json")

    def verify(self, code, phone="07701234567"):
        return self.client.post("/api/auth/otp/verify/", {"phone": phone, "code": code}, format="json")

    def last_code(self):
        return RecordingSender.sent[-1][2]

    def test_request_sends_by_whatsapp_and_stores_only_a_hash(self):
        response = self.request_code()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["channel"], "whatsapp")
        self.assertEqual(response.json()["phone"], PHONE)
        self.assertNotIn("code", response.json())

        otp_row = PhoneOTP.objects.get()
        self.assertNotEqual(otp_row.code_hash, self.last_code())
        self.assertNotIn(self.last_code(), otp_row.code_hash)

    def test_falls_back_to_sms_when_whatsapp_fails(self):
        RecordingSender.failing = {"whatsapp"}
        response = self.request_code()
        self.assertEqual(response.json()["channel"], "sms")
        self.assertEqual(RecordingSender.sent[-1][0], "sms")

    def test_both_channels_failing_returns_503_and_stores_nothing(self):
        RecordingSender.failing = {"whatsapp", "sms"}
        response = self.request_code()
        self.assertEqual(response.status_code, 503)
        self.assertFalse(PhoneOTP.objects.exists())

    def test_invalid_phone_is_400(self):
        response = self.request_code(phone="12345")
        self.assertEqual(response.status_code, 400)
        self.assertIn("phone", response.json())

    def test_resend_too_soon_is_429_with_retry_after(self):
        self.request_code()
        response = self.request_code()
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.json()["error"], "too_soon")
        self.assertTrue(0 < response.json()["retry_after"] <= 60)

    def test_hourly_limit_per_phone(self):
        for _ in range(5):
            PhoneOTP.objects.create(
                phone=PHONE, code_hash="x", channel="sms", expires_at=timezone.now()
            )
        PhoneOTP.objects.update(created_at=timezone.now() - timedelta(minutes=5))
        response = self.request_code()
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.json()["error"], "too_many_requests")

    def test_first_login_creates_customer_and_returns_token(self):
        self.request_code()
        response = self.verify(self.last_code())
        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertTrue(body["is_new_user"])
        self.assertEqual(body["user"]["phone"], PHONE)
        self.assertEqual(body["user"]["role"], "customer")

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {body['token']}")
        self.assertEqual(self.client.get("/api/auth/me/").json()["phone"], PHONE)

    def test_returning_user_logs_into_same_account(self):
        user = User.objects.create_user(phone=PHONE, name="Zahraa", role=User.Role.CAPTAIN)
        self.request_code()
        response = self.verify(self.last_code())
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["is_new_user"])
        self.assertEqual(response.json()["user"]["id"], user.pk)
        self.assertEqual(User.objects.count(), 1)

    def test_code_works_only_once(self):
        self.request_code()
        code = self.last_code()
        self.assertEqual(self.verify(code).status_code, 201)
        self.assertEqual(self.verify(code).status_code, 400)

    def test_expired_code_is_rejected(self):
        self.request_code()
        PhoneOTP.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
        response = self.verify(self.last_code())
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "invalid_code")

    def test_code_locks_after_five_wrong_guesses(self):
        self.request_code()
        code = self.last_code()
        wrong = "000000" if code != "000000" else "111111"
        for _ in range(5):
            self.assertEqual(self.verify(wrong).status_code, 400)
        self.assertEqual(PhoneOTP.objects.get().attempts, 5)
        # Even the right code is refused now.
        self.assertEqual(self.verify(code).status_code, 400)

    def test_disabled_account_cannot_log_in(self):
        User.objects.create_user(phone=PHONE, is_active=False)
        self.request_code()
        response = self.verify(self.last_code())
        self.assertEqual(response.status_code, 403)

    def test_logout_deletes_token(self):
        self.request_code()
        token = self.verify(self.last_code()).json()["token"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
        self.assertEqual(self.client.post("/api/auth/logout/").status_code, 204)
        self.assertEqual(self.client.get("/api/auth/me/").status_code, 401)

    def test_me_patch_updates_name_and_language_but_not_role(self):
        user = User.objects.create_user(phone=PHONE)
        self.client.force_authenticate(user)
        response = self.client.patch(
            "/api/auth/me/", {"name": "Ali", "language_pref": "ku", "role": "vendor"}, format="json"
        )
        user.refresh_from_db()
        self.assertEqual((user.name, user.language_pref, user.role), ("Ali", "ku", "customer"))
        self.assertEqual(response.json()["name"], "Ali")


class WhatsAppSenderTests(TestCase):
    @override_settings(
        WHATSAPP={
            "TOKEN": "test-token",
            "PHONE_NUMBER_ID": "123",
            "TEMPLATE": "wasel_login_code",
            "TEMPLATE_LANGUAGE": "ar",
            "API_VERSION": "v21.0",
        }
    )
    def test_posts_authentication_template(self):
        response = mock.MagicMock(status=200)
        response.__enter__.return_value = response
        with mock.patch("urllib.request.urlopen", return_value=response) as urlopen:
            otp.WhatsAppCloudSender().send(PHONE, "482913")

        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "https://graph.facebook.com/v21.0/123/messages")
        self.assertEqual(request.get_header("Authorization"), "Bearer test-token")
        self.assertIn(b'"to": "9647701234567"', request.data)
        self.assertIn(b'"482913"', request.data)


class AdminAccountTests(TestCase):
    """Staff add captains and store owners in the admin; they then sign in by code."""

    def setUp(self):
        self.staff = User.objects.create_superuser("+9647700000999", "a-strong-admin-pass", name="Admin")
        self.client.force_login(self.staff)

    def add_user(self, **fields):
        data = {"phone": "", "name": "", "role": "customer", "password1": "", "password2": ""}
        data.update(fields)
        return self.client.post(f"/{settings.DJANGO_ADMIN_PATH}accounts/user/add/", data)

    def test_any_phone_format_is_stored_the_way_login_finds_it(self):
        response = self.add_user(phone="0750 123 4567", name="Ali", role="captain")
        self.assertEqual(response.status_code, 302)
        captain = User.objects.get(name="Ali")
        self.assertEqual(captain.phone, "+9647501234567")
        self.assertEqual(captain.role, "captain")

    def test_app_accounts_need_no_password(self):
        self.add_user(phone="٠٧٨٠١٢٣٤٥٦٧", name="Store owner", role="vendor")
        owner = User.objects.get(phone="+9647801234567")
        self.assertFalse(owner.has_usable_password())

    def test_staff_can_still_get_a_password(self):
        self.add_user(phone="07709998877", name="Support", password1="a-strong-admin-pass", password2="a-strong-admin-pass")
        self.assertTrue(User.objects.get(phone="+9647709998877").check_password("a-strong-admin-pass"))

    def test_mismatched_passwords_and_bad_numbers_are_refused(self):
        response = self.add_user(phone="07709998877", password1="a-strong-admin-pass", password2="different-pass-1")
        self.assertContains(response, "The two passwords don&#x27;t match.")
        response = self.add_user(phone="12345")
        self.assertContains(response, "Enter an Iraqi mobile number starting with 07.")
        self.assertFalse(User.objects.filter(name="").exclude(pk=self.staff.pk).exists())

    def test_a_number_already_in_use_is_caught_after_normalizing(self):
        User.objects.create_user("+9647501234567", role="captain")
        response = self.add_user(phone="0750 123 4567")
        self.assertContains(response, "already exists")

    def test_editing_normalizes_the_number_too(self):
        user = User.objects.create_user("+9647501234567", name="Old")
        response = self.client.post(
            f"/{settings.DJANGO_ADMIN_PATH}accounts/user/{user.pk}/change/",
            {
                "phone": "0750 765 4321",
                "name": "Old",
                "role": "captain",
                "language_pref": "ar",
                "wallet_balance": "0",
                "is_active": "on",
                "date_joined_0": "2026-01-01",
                "date_joined_1": "10:00:00",
            },
        )
        self.assertEqual(response.status_code, 302, response.content[:2000])
        user.refresh_from_db()
        self.assertEqual(user.phone, "+9647507654321")

    def test_manager_normalizes_too(self):
        user = User.objects.create_user("0770 111 2233")
        self.assertEqual(user.phone, "+9647701112233")
        self.assertFalse(user.has_usable_password())

    def test_staff_may_use_a_non_iraqi_number(self):
        response = self.add_user(
            phone="501 218 3813", name="Owner", password1="a-strong-admin-pass", password2="a-strong-admin-pass"
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(phone="5012183813").exists())
        # createsuperuser goes through the manager.
        admin = User.objects.create_superuser("+1 501 555 0100", "a-strong-admin-pass", name="Admin 2")
        self.assertEqual(admin.phone, "+15015550100")

    def test_app_accounts_still_need_an_iraqi_number(self):
        response = self.add_user(phone="501 218 3813", role="captain")
        self.assertContains(response, "Enter an Iraqi mobile number starting with 07.")
        with self.assertRaises(InvalidPhone):
            User.objects.create_user("5012183813", role="captain")

    def test_editing_a_staff_account_keeps_its_number(self):
        staff = User.objects.create_superuser("5012183813", "a-strong-admin-pass", name="Owner")
        response = self.client.post(
            f"/{settings.DJANGO_ADMIN_PATH}accounts/user/{staff.pk}/change/",
            {
                "phone": "5012183813",
                "name": "Owner",
                "role": "customer",
                "language_pref": "en",
                "wallet_balance": "0",
                "is_active": "on",
                "is_staff": "on",
                "is_superuser": "on",
                "date_joined_0": "2026-01-01",
                "date_joined_1": "10:00:00",
            },
        )
        self.assertEqual(response.status_code, 302, response.content[:1500])
