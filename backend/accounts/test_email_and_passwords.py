from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from .models import AuthToken, PhoneOTP, User
from .tests import TEST_OTP, RecordingSender

PHONE = "+9647701234567"


@override_settings(OTP=TEST_OTP)
class SignInTestBase(TestCase):
    def setUp(self):
        RecordingSender.sent = []
        RecordingSender.failing = set()
        self.client = APIClient()
        self.user = User.objects.create_user(phone=PHONE, name="Ali")

    def last_code(self):
        return RecordingSender.sent[-1][2]

    def as_user(self, token=None):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Token {token or AuthToken.objects.create(user=self.user).key}")
        return client

    def add_email(self, client, email="Ali@Example.com"):
        self.assertEqual(client.post("/api/auth/email/", {"email": email}, format="json").status_code, 200)
        return client.post("/api/auth/email/verify/", {"email": email, "code": self.last_code()}, format="json")

    def password_login(self, login, password, **extra):
        return self.client.post("/api/auth/password/login/", {"login": login, "password": password, **extra}, format="json")


class EmailTests(SignInTestBase):
    def test_adding_an_email_takes_a_code_sent_to_it(self):
        me = self.as_user()
        response = self.add_email(me)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["email"], "ali@example.com")
        self.assertEqual(RecordingSender.sent[-1][:2], ("email", "ali@example.com"))

    def test_a_wrong_code_doesnt_add_the_email(self):
        me = self.as_user()
        me.post("/api/auth/email/", {"email": "ali@example.com"}, format="json")
        response = me.post("/api/auth/email/verify/", {"email": "ali@example.com", "code": "000000"}, format="json")
        self.assertEqual(response.json()["error"], "invalid_code")
        self.user.refresh_from_db()
        self.assertIsNone(self.user.email)

    def test_an_email_belongs_to_one_account(self):
        self.add_email(self.as_user())
        other = User.objects.create_user(phone="+9647701234568")
        client = APIClient()
        client.force_authenticate(other)
        response = client.post("/api/auth/email/", {"email": "ALI@example.com"}, format="json")
        self.assertEqual((response.status_code, response.json()["error"]), (409, "email_taken"))

    def test_sign_in_with_an_email_code(self):
        self.add_email(self.as_user())
        RecordingSender.sent = []
        PhoneOTP.objects.all().delete()  # a minute later: no "too soon"
        self.assertEqual(self.client.post("/api/auth/otp/request/", {"email": "ali@EXAMPLE.com"}, format="json").status_code, 200)
        self.assertEqual(RecordingSender.sent[-1][0], "email")
        response = self.client.post("/api/auth/otp/verify/", {"email": "ali@example.com", "code": self.last_code()}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["user"]["phone"], PHONE)

    def test_an_unknown_email_cant_sign_up(self):
        response = self.client.post("/api/auth/otp/request/", {"email": "new@example.com"}, format="json")
        self.assertEqual((response.status_code, response.json()["error"]), (404, "no_account_for_email"))
        self.assertEqual(RecordingSender.sent, [])

    def test_an_add_email_code_doesnt_sign_anyone_in(self):
        me = self.as_user()
        me.post("/api/auth/email/", {"email": "ali@example.com"}, format="json")
        response = self.client.post("/api/auth/otp/verify/", {"email": "ali@example.com", "code": self.last_code()}, format="json")
        self.assertEqual(response.status_code, 400)


class PasswordTests(SignInTestBase):
    def set_password(self, client, password="kebab-and-tea-42"):
        return client.post("/api/auth/password/", {"password": password}, format="json")

    def test_new_accounts_have_no_password(self):
        self.assertFalse(self.as_user().get("/api/auth/me/").json()["has_password"])
        self.assertEqual(self.password_login("07701234567", "").status_code, 400)

    def test_weak_passwords_are_refused(self):
        response = self.set_password(self.as_user(), "12345678")
        self.assertEqual((response.status_code, response.json()["error"]), (400, "weak_password"))

    def test_sign_in_with_phone_or_email_and_password(self):
        me = self.as_user()
        self.add_email(me)
        self.assertTrue(self.set_password(me).json()["has_password"])
        for login, extra in [("07701234567", {}), (PHONE, {}), ("ALI@example.com", {})]:
            response = self.password_login(login, "kebab-and-tea-42", **extra)
            self.assertEqual(response.status_code, 200, login)
            self.assertEqual(response.json()["user"]["id"], self.user.pk)

    def test_wrong_password_and_unknown_account_look_the_same(self):
        self.set_password(self.as_user())
        wrong = self.password_login("07701234567", "nope-nope-nope")
        unknown = self.password_login("07709999999", "kebab-and-tea-42")
        self.assertEqual(wrong.json(), unknown.json())
        self.assertEqual(wrong.json()["error"], "invalid_login")

    def test_five_wrong_passwords_lock_password_sign_in_but_codes_still_work(self):
        self.set_password(self.as_user())
        for _ in range(5):
            self.password_login("07701234567", "nope-nope-nope")
        locked = self.password_login("07701234567", "kebab-and-tea-42")
        self.assertEqual((locked.status_code, locked.json()["error"]), (429, "locked"))
        self.client.post("/api/auth/otp/request/", {"phone": "07701234567"}, format="json")
        response = self.client.post("/api/auth/otp/verify/", {"phone": "07701234567", "code": self.last_code()}, format="json")
        self.assertEqual(response.status_code, 200)

    def test_setting_a_password_signs_out_other_devices(self):
        other_device = AuthToken.objects.create(user=self.user)
        this_device = AuthToken.objects.create(user=self.user)
        self.assertEqual(self.set_password(self.as_user(this_device.key)).status_code, 200)
        self.assertTrue(AuthToken.objects.filter(pk=this_device.pk).exists())
        self.assertFalse(AuthToken.objects.filter(pk=other_device.pk).exists())


class DeviceTests(SignInTestBase):
    def sign_in_by_code(self):
        self.client.post("/api/auth/otp/request/", {"phone": "07701234567"}, format="json")
        response = self.client.post("/api/auth/otp/verify/", {"phone": "07701234567", "code": self.last_code()}, format="json")
        PhoneOTP.objects.all().delete()  # so the next request isn't "too soon"
        return response.json()["token"]

    def test_each_sign_in_is_its_own_device_and_logout_ends_only_that_one(self):
        phone, tablet = self.sign_in_by_code(), self.sign_in_by_code()
        self.assertNotEqual(phone, tablet)
        self.assertEqual(self.as_user(phone).post("/api/auth/logout/").status_code, 204)
        self.assertEqual(self.as_user(phone).get("/api/auth/me/").status_code, 401)
        self.assertEqual(self.as_user(tablet).get("/api/auth/me/").status_code, 200)
