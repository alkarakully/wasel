from django.contrib.gis.geos import Point
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from accounts.models import User
from vendors.models import Vendor

from .models import Order

BAGHDAD = Point(44.4009, 33.3406, srid=4326)


class OrderApiTests(TestCase):
    def setUp(self):
        self.customer = User.objects.create_user(phone="+9647700000010")
        self.other_customer = User.objects.create_user(phone="+9647700000011")
        self.captain = User.objects.create_user(phone="+9647700000012", role=User.Role.CAPTAIN)
        self.owner = User.objects.create_user(phone="+9647700000013", role=User.Role.VENDOR)
        vendor = Vendor.objects.create(status=Vendor.Status.APPROVED, owner=self.owner, name="Kebab", location=BAGHDAD)

        self.order = Order.objects.create(
            customer=self.customer,
            vendor=vendor,
            captain=self.captain,
            delivery_address="Karrada, street 52",
            delivery_location=BAGHDAD,
            subtotal=10000,
            delivery_fee=2000,
            service_fee=500,
            discount=1000,
            tip=1000,
        )
        self.client = APIClient()

    def order_ids(self, user):
        self.client.force_authenticate(user)
        return [order["id"] for order in self.client.get("/api/orders/").json()["results"]]

    def test_requires_login(self):
        self.assertEqual(self.client.get("/api/orders/").status_code, 401)

    def test_customer_captain_and_vendor_owner_see_the_order(self):
        for user in (self.customer, self.captain, self.owner):
            with self.subTest(user=user.role):
                self.assertEqual(self.order_ids(user), [self.order.pk])

    def test_other_customers_do_not(self):
        self.assertEqual(self.order_ids(self.other_customer), [])

    def test_calculate_total(self):
        self.assertEqual(self.order.calculate_total(), 12500)


# --- Pricing and placement --------------------------------------------------

from datetime import timedelta  # noqa: E402
from decimal import Decimal  # noqa: E402

from django.utils import timezone  # noqa: E402

from accounts.models import WalletTransaction  # noqa: E402
from subscriptions.models import WaselPlusSubscription  # noqa: E402
from vendors.models import Offer, Product, ProductModifier  # noqa: E402

from .models import OrderItem, OrderItemModifier  # noqa: E402
from .pricing import delivery_fee_for  # noqa: E402

TAHRIR_LAT, TAHRIR_LNG = 33.3406, 44.4009
NEAR = (TAHRIR_LAT + 0.009, TAHRIR_LNG)  # about 1 km north
FARTHER = (TAHRIR_LAT + 0.04, TAHRIR_LNG)  # about 4.4 km north
OUTSIDE = (TAHRIR_LAT + 0.08, TAHRIR_LNG)  # about 8.9 km, past the 5 km radius


class PricingTestBase(TestCase):
    def setUp(self):
        self.customer = User.objects.create_user(phone="+9647700000020")
        self.owner = User.objects.create_user(phone="+9647700000021", role=User.Role.VENDOR)
        self.vendor = Vendor.objects.create(
            status=Vendor.Status.APPROVED,
            owner=self.owner,
            name="Tahrir Grill",
            location=Point(TAHRIR_LNG, TAHRIR_LAT, srid=4326),
            is_open=True,
            commission_rate=Decimal("15"),
        )
        self.kebab = Product.objects.create(vendor=self.vendor, name_ar="كباب", name_en="Kebab", price=8000)
        self.regular = ProductModifier.objects.create(
            product=self.kebab, group_name="Size", name_ar="عادي", price_delta=0, is_required=True
        )
        self.large = ProductModifier.objects.create(
            product=self.kebab, group_name="Size", name_ar="كبير", price_delta=2000, is_required=True
        )
        self.bread = ProductModifier.objects.create(
            product=self.kebab, group_name="Extras", name_ar="صمون", price_delta=500
        )
        self.tomatoes = Product.objects.create(
            vendor=self.vendor, name_ar="طماطة", name_en="Tomatoes", price=1500, unit_type=Product.UnitType.KG
        )
        self.client = APIClient()
        self.client.force_authenticate(self.customer)

    def cart(self, items=None, at=NEAR, **extra):
        body = {
            "vendor": self.vendor.pk,
            "items": items
            if items is not None
            else [
                {"product": self.kebab.pk, "quantity": 2, "modifiers": [self.large.pk, self.bread.pk]},
                {"product": self.tomatoes.pk, "quantity": "1.5"},
            ],
            "delivery_latitude": at[0],
            "delivery_longitude": at[1],
        }
        body.update(extra)
        return body

    def quote(self, **kwargs):
        return self.client.post("/api/orders/quote/", self.cart(**kwargs), format="json")

    def place(self, **kwargs):
        body = self.cart(**kwargs)
        body.setdefault("delivery_address", "Karrada, street 52, house 9")
        return self.client.post("/api/orders/", body, format="json")

    def assertError(self, response, code):
        self.assertEqual(response.status_code, 400, response.content)
        self.assertEqual(response.json()["error"], code)


class QuoteTests(PricingTestBase):
    def test_full_breakdown(self):
        body = self.quote().json()
        # Kebab: (8000 + 2000 large + 500 bread) x 2 = 21000; tomatoes 1500 x 1.5 kg = 2250.
        self.assertEqual([item["line_total"] for item in body["items"]], ["21000", "2250"])
        self.assertEqual(body["subtotal"], "23250")
        self.assertEqual(body["delivery_fee"], "1500")
        self.assertEqual(body["service_fee"], "500")
        self.assertEqual(body["discount"], "0")
        self.assertEqual(body["total_amount"], "25250")
        self.assertFalse(body["wasel_plus"])
        self.assertNotIn("commission_amount", body)

    def test_delivery_fee_grows_per_started_km(self):
        self.assertEqual(delivery_fee_for(900), 1500)
        self.assertEqual(delivery_fee_for(2000), 1500)
        self.assertEqual(delivery_fee_for(2001), 1750)
        self.assertEqual(self.quote(at=FARTHER).json()["delivery_fee"], "2250")

    def test_tip_is_added_to_total(self):
        self.assertEqual(self.quote(tip=1000).json()["total_amount"], "26250")

    def test_closed_vendor(self):
        Vendor.objects.update(is_open=False)
        self.assertError(self.quote(), "vendor_closed")

    def test_outside_delivery_radius(self):
        self.assertError(self.quote(at=OUTSIDE), "out_of_delivery_area")

    def test_out_of_stock_product(self):
        Product.objects.filter(pk=self.tomatoes.pk).update(is_available=False)
        self.assertError(self.quote(), "product_unavailable")

    def test_product_from_another_vendor(self):
        other = Vendor.objects.create(status=Vendor.Status.APPROVED, owner=self.owner, name="Other", location=Point(TAHRIR_LNG, TAHRIR_LAT))
        foreign = Product.objects.create(vendor=other, name_ar="شاي", price=500)
        self.assertError(self.quote(items=[{"product": foreign.pk}]), "product_not_found")

    def test_required_option_missing(self):
        self.assertError(self.quote(items=[{"product": self.kebab.pk, "modifiers": [self.bread.pk]}]), "missing_required_option")

    def test_option_from_another_product(self):
        other = Product.objects.create(vendor=self.vendor, name_ar="شاي", price=500)
        other_mod = ProductModifier.objects.create(product=other, group_name="Sugar", name_ar="سكر", price_delta=0)
        items = [{"product": self.kebab.pk, "modifiers": [self.regular.pk, other_mod.pk]}]
        self.assertError(self.quote(items=items), "invalid_modifier")

    def test_fractional_quantity_only_for_kg_items(self):
        items = [{"product": self.kebab.pk, "quantity": "1.5", "modifiers": [self.regular.pk]}]
        self.assertError(self.quote(items=items), "invalid_quantity")

    def test_empty_cart_is_rejected(self):
        self.assertEqual(self.quote(items=[]).status_code, 400)


class OfferAndCommissionTests(PricingTestBase):
    def make_offer(self, vendor="self", **fields):
        now = timezone.now()
        return Offer.objects.create(
            vendor=self.vendor if vendor == "self" else vendor,
            title=fields.pop("title", "Offer"),
            starts_at=now - timedelta(hours=1),
            ends_at=now + timedelta(hours=1),
            **fields,
        )

    def commission_of_placed_order(self, **kwargs):
        response = self.place(**kwargs)
        self.assertEqual(response.status_code, 201, response.content)
        return Order.objects.get(pk=response.json()["id"]).commission_amount

    def test_best_offer_applies_automatically(self):
        self.make_offer(type=Offer.Type.FIXED, value=1000)
        best = self.make_offer(type=Offer.Type.PERCENT, value=10)  # 2325 off 23250
        body = self.quote().json()
        self.assertEqual(body["offer"], best.pk)
        self.assertEqual(body["discount"], "2325")
        self.assertEqual(body["total_amount"], "22925")

    def test_chosen_offer_below_minimum_is_rejected(self):
        offer = self.make_offer(type=Offer.Type.FIXED, value=3000, min_order=30000)
        self.assertError(self.quote(offer=offer.pk), "offer_not_applicable")

    def test_expired_or_other_vendors_offers_never_apply(self):
        other = Vendor.objects.create(status=Vendor.Status.APPROVED, owner=self.owner, name="Other", location=Point(TAHRIR_LNG, TAHRIR_LAT))
        self.make_offer(vendor=other, type=Offer.Type.PERCENT, value=50)
        expired = self.make_offer(type=Offer.Type.PERCENT, value=50)
        Offer.objects.filter(pk=expired.pk).update(ends_at=timezone.now() - timedelta(minutes=1))
        self.assertEqual(self.quote().json()["discount"], "0")

    def test_free_delivery_offer_discounts_the_delivery_fee(self):
        self.make_offer(vendor=None, type=Offer.Type.FREE_DELIVERY)
        body = self.quote(at=FARTHER).json()
        self.assertEqual(body["delivery_fee"], "2250")
        self.assertEqual(body["discount"], "2250")

    def test_commission_on_full_subtotal_without_offer(self):
        # 15% of 23250 = 3487.5, rounded to 3488.
        self.assertEqual(self.commission_of_placed_order(), Decimal(3488))

    def test_vendor_funded_discount_lowers_commission_base(self):
        self.make_offer(type=Offer.Type.FIXED, value=3250)
        # 15% of (23250 - 3250) = 3000
        self.assertEqual(self.commission_of_placed_order(), Decimal(3000))

    def test_platform_offer_does_not_lower_commission(self):
        self.make_offer(vendor=None, type=Offer.Type.FIXED, value=3250)
        self.assertEqual(self.commission_of_placed_order(), Decimal(3488))

    def test_buy_one_get_one_free_makes_every_second_unit_free(self):
        self.make_offer(type=Offer.Type.BOGO, product=self.kebab)
        # Two large kebabs with bread at 10500 each: one is free.
        self.assertEqual(self.quote().json()["discount"], "10500")
        # With different options, the cheaper units are the free ones: 8000 regular, 2 x 10000 large.
        items = [
            {"product": self.kebab.pk, "quantity": 1, "modifiers": [self.regular.pk]},
            {"product": self.kebab.pk, "quantity": 2, "modifiers": [self.large.pk]},
        ]
        self.assertEqual(self.quote(items=items).json()["discount"], "8000")

    def test_buy_one_get_one_free_needs_two_of_the_item(self):
        self.make_offer(type=Offer.Type.BOGO, product=self.kebab)
        one = [{"product": self.kebab.pk, "quantity": 1, "modifiers": [self.regular.pk]}]
        self.assertEqual(self.quote(items=one).json()["discount"], "0")
        self.make_offer(type=Offer.Type.BOGO, product=self.tomatoes, title="Other item")
        self.assertEqual(self.quote(items=[{"product": self.tomatoes.pk, "quantity": "2"}]).json()["discount"], "0")

    def test_store_funded_buy_one_get_one_lowers_commission_base(self):
        self.make_offer(type=Offer.Type.BOGO, product=self.kebab)
        # 15% of (23250 - 10500) = 1912.5, rounded half up.
        self.assertEqual(self.commission_of_placed_order(), Decimal(1913))

    def assertAddsUp(self, body):
        """total = subtotal + fees + tip - discount, and the line deals sum to items_discount."""
        money = {k: Decimal(body[k]) for k in ("subtotal", "delivery_fee", "service_fee", "tip", "discount", "total_amount")}
        self.assertEqual(
            money["total_amount"],
            money["subtotal"] + money["delivery_fee"] + money["service_fee"] + money["tip"] - money["discount"],
        )
        self.assertEqual(sum(Decimal(line["discount"]) for line in body["items"]), Decimal(body["items_discount"]))

    def test_every_item_with_a_deal_gets_it_in_the_same_order(self):
        burger = Product.objects.create(vendor=self.vendor, name_ar="برغر", price=6000)
        self.make_offer(type=Offer.Type.BOGO, product=self.kebab)
        self.make_offer(type=Offer.Type.BOGO, product=burger, title="Burger 1+1")
        items = [
            {"product": self.kebab.pk, "quantity": 2, "modifiers": [self.regular.pk]},
            {"product": burger.pk, "quantity": 3},
        ]
        body = self.quote(items=items).json()
        # 2 x 8000 kebab: one free; 3 x 6000 burger: one free.
        self.assertEqual([line["discount"] for line in body["items"]], ["8000", "6000"])
        self.assertEqual((body["items_discount"], body["discount"]), ("14000", "14000"))
        self.assertAddsUp(body)

    def test_store_percent_offer_applies_to_the_food_left_after_deals(self):
        self.make_offer(type=Offer.Type.BOGO, product=self.kebab)
        percent = self.make_offer(type=Offer.Type.PERCENT, value=10, title="10%")
        body = self.quote().json()
        # Subtotal 23250, kebab deal 10500, then 10% of the 12750 left = 1275.
        self.assertEqual((body["items_discount"], body["discount"], body["offer"]), ("10500", "11775", percent.pk))
        self.assertAddsUp(body)
        order = Order.objects.get(pk=self.place().json()["id"])
        self.assertEqual((order.discount, order.store_discount), (Decimal(11775), Decimal(11775)))
        # Commission on what the store really sells the food for: 15% of (12750 - 1275) = 1721.25.
        self.assertEqual(order.commission_amount, Decimal(1721))

    def test_wasel_pays_for_its_offer_and_the_store_for_its_deal(self):
        self.make_offer(type=Offer.Type.BOGO, product=self.kebab)
        self.make_offer(vendor=None, type=Offer.Type.FIXED, value=2000, title="Wasel 2000")
        order = Order.objects.get(pk=self.place().json()["id"])
        self.assertEqual((order.discount, order.store_discount), (Decimal(12500), Decimal(10500)))
        # Wasel's 2000 doesn't lower commission: 15% of 12750.
        self.assertEqual(order.commission_amount, Decimal(1913))
        item = order.items.get(product=self.kebab)
        self.assertEqual((item.discount, item.deal.type), (Decimal(10500), Offer.Type.BOGO))
        self.assertEqual(order.total_amount, order.calculate_total())

    def test_store_free_delivery_comes_from_the_store_but_not_off_commission(self):
        self.make_offer(type=Offer.Type.BOGO, product=self.kebab)
        self.make_offer(type=Offer.Type.FREE_DELIVERY, title="Free ride")
        order = Order.objects.get(pk=self.place(at=FARTHER).json()["id"])
        self.assertEqual(order.delivery_fee, Decimal(2250))
        self.assertEqual((order.discount, order.store_discount), (Decimal(12750), Decimal(12750)))
        self.assertEqual(order.commission_amount, Decimal(1913))  # 15% of the 12750 of food left

    def test_store_report_takes_its_deals_off_the_payout(self):
        self.make_offer(type=Offer.Type.BOGO, product=self.kebab)
        self.make_offer(vendor=None, type=Offer.Type.FIXED, value=2000, title="Wasel 2000")
        order = Order.objects.get(pk=self.place().json()["id"])
        from vendors.reports import store_payout

        money = store_payout(Order.objects.filter(pk=order.pk))
        self.assertEqual(money["store_discounts"], Decimal(10500))
        self.assertEqual(money["payout"], Decimal(23250 - 10500 - 1913))

    def test_a_deal_cant_be_picked_as_the_order_offer(self):
        deal = self.make_offer(type=Offer.Type.BOGO, product=self.kebab)
        self.assertError(self.quote(offer=deal.pk), "offer_not_applicable")

    def test_no_commission_during_free_period(self):
        Vendor.objects.update(commission_free_until=timezone.now() + timedelta(days=10))
        self.assertEqual(self.commission_of_placed_order(), Decimal(0))


class WaselPlusPricingTests(PricingTestBase):
    def test_member_gets_free_delivery_above_minimum_and_lower_service_fee(self):
        WaselPlusSubscription.objects.create(user=self.customer, status=WaselPlusSubscription.Status.ACTIVE)
        body = self.quote().json()  # subtotal 23250 >= 15000
        self.assertTrue(body["wasel_plus"])
        self.assertEqual(body["delivery_fee"], "0")
        self.assertEqual(body["service_fee"], "250")

    def test_member_pays_delivery_below_minimum(self):
        WaselPlusSubscription.objects.create(user=self.customer, status=WaselPlusSubscription.Status.ACTIVE)
        body = self.quote(items=[{"product": self.tomatoes.pk, "quantity": 2}]).json()
        self.assertEqual(body["delivery_fee"], "1500")
        self.assertEqual(body["service_fee"], "250")

    def test_expired_trial_is_not_a_member(self):
        WaselPlusSubscription.objects.create(
            user=self.customer,
            status=WaselPlusSubscription.Status.TRIAL,
            trial_end_date=timezone.now() - timedelta(days=1),
        )
        self.assertFalse(self.quote().json()["wasel_plus"])


class PlaceOrderTests(PricingTestBase):
    def test_requires_login(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.place().status_code, 401)

    def test_order_matches_quote_and_snapshots_prices(self):
        quote = self.quote().json()
        response = self.place()
        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()
        for field in ["subtotal", "delivery_fee", "service_fee", "discount", "total_amount"]:
            self.assertEqual(body[field], quote[field], field)
        self.assertEqual(body["payment_type"], "cod")
        self.assertEqual(body["payment_status"], "pending")
        self.assertRegex(body["delivery_pin"], r"^\d{4}$")

        # Later price changes don't touch the placed order.
        Product.objects.filter(pk=self.kebab.pk).update(price=99000)
        ProductModifier.objects.filter(pk=self.large.pk).update(price_delta=50000)
        item = OrderItem.objects.get(order_id=body["id"], product=self.kebab)
        self.assertEqual((item.unit_price, item.line_total), (Decimal(10500), Decimal(21000)))
        self.assertEqual(
            sorted(OrderItemModifier.objects.filter(order_item=item).values_list("price_delta", flat=True)),
            [Decimal(500), Decimal(2000)],
        )

    def test_delivery_address_is_required(self):
        body = self.cart()
        response = self.client.post("/api/orders/", body, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("delivery_address", response.json())

    def test_customer_contact_for_captain_and_store_only_while_active(self):
        order_id = self.place().json()["id"]
        captain = User.objects.create_user(phone="+9647500000077", role=User.Role.CAPTAIN)
        Order.objects.filter(pk=order_id).update(captain=captain, status=Order.Status.OUT_FOR_DELIVERY)

        for user, expected in [(captain, self.customer.phone), (self.owner, self.customer.phone), (self.customer, None)]:
            self.client.force_authenticate(user)
            contact = self.client.get(f"/api/orders/{order_id}/").json()["customer_contact"]
            self.assertEqual(contact and contact["phone"], expected)

        Order.objects.filter(pk=order_id).update(status=Order.Status.DELIVERED)
        self.client.force_authenticate(captain)
        self.assertIsNone(self.client.get(f"/api/orders/{order_id}/").json()["customer_contact"])

    def test_items_carry_names_and_status_filter_works(self):
        order_id = self.place().json()["id"]
        self.client.force_authenticate(self.owner)
        body = self.client.get("/api/orders/", {"status": "received,preparing"}).json()["results"]
        self.assertEqual([o["id"] for o in body], [order_id])
        kebab = next(item for item in body[0]["items"] if item["product"] == self.kebab.pk)
        self.assertEqual(kebab["name"]["en"], "Kebab")
        self.assertEqual(sorted(m["group_name"] for m in kebab["modifiers"]), ["Extras", "Size"])
        self.assertEqual(self.client.get("/api/orders/", {"status": "delivered"}).json()["results"], [])

    def test_pin_hidden_from_vendor_owner(self):
        order_id = self.place().json()["id"]
        self.client.force_authenticate(self.owner)
        self.assertIsNone(self.client.get(f"/api/orders/{order_id}/").json()["delivery_pin"])

    def test_cash_on_delivery_is_the_only_way_to_pay_for_now(self):
        self.customer.wallet_balance = 100000
        self.customer.save(update_fields=["wallet_balance"])
        for kind in ("wallet", "card"):
            response = self.place(payment_type=kind)
            self.assertError(response, "payment_not_available")
        self.assertFalse(Order.objects.exists())
        self.assertEqual(self.place(payment_type="cod").status_code, 201)

    @override_settings(PAYMENT_METHODS=["cod", "wallet"])  # the wallet is off by default
    def test_wallet_payment_deducts_balance(self):
        User.objects.filter(pk=self.customer.pk).update(wallet_balance=30000)
        response = self.place(payment_type="wallet")
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.json()["payment_status"], "paid")
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.wallet_balance, Decimal(30000 - 25250))
        transaction = WalletTransaction.objects.get(user=self.customer)
        self.assertEqual((transaction.type, transaction.amount), ("payment", Decimal(-25250)))

    @override_settings(PAYMENT_METHODS=["cod", "wallet"])  # the wallet is off by default
    def test_wallet_with_too_little_balance_creates_nothing(self):
        User.objects.filter(pk=self.customer.pk).update(wallet_balance=1000)
        self.assertError(self.place(payment_type="wallet"), "insufficient_wallet_balance")
        self.assertFalse(Order.objects.filter(customer=self.customer).exists())
        self.assertFalse(WalletTransaction.objects.exists())


# --- Status flow ----------------------------------------------------------------


class StatusFlowTests(PricingTestBase):
    def setUp(self):
        super().setUp()
        self.captain = User.objects.create_user(phone="+9647700000030", role=User.Role.CAPTAIN)
        self.other_captain = User.objects.create_user(phone="+9647700000031", role=User.Role.CAPTAIN)
        self.order_id = self.place().json()["id"]

    def step(self, user, name, **body):
        self.client.force_authenticate(user)
        return self.client.post(f"/api/orders/{self.order_id}/{name}/", body, format="json")

    def order(self):
        return Order.objects.get(pk=self.order_id)

    def pin(self):
        return self.order().delivery_pin

    def deliver_ready_order(self):
        self.step(self.owner, "accept", prep_minutes=15)
        self.step(self.captain, "claim")
        self.step(self.owner, "ready")
        self.step(self.captain, "pickup")

    def assertStepError(self, response, status_code, code):
        self.assertEqual(response.status_code, status_code, response.content)
        self.assertEqual(response.json()["error"], code)

    def test_full_happy_path(self):
        response = self.step(self.owner, "accept", prep_minutes=20)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["status"], "preparing")
        order = self.order()
        self.assertAlmostEqual((order.estimated_ready_at - order.accepted_at).total_seconds(), 20 * 60, delta=1)

        self.assertEqual(self.step(self.captain, "claim").json()["status"], "preparing")
        self.assertEqual(self.step(self.owner, "ready").json()["status"], "ready")
        self.assertEqual(self.step(self.captain, "pickup").json()["status"], "out_for_delivery")

        response = self.step(self.captain, "deliver", pin=self.pin())
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertEqual(body["status"], "delivered")
        self.assertEqual(body["payment_status"], "paid")  # cash collected at the door
        self.assertIsNone(body["delivery_pin"])  # captain never sees it
        order = self.order()
        self.assertTrue(all([order.accepted_at, order.ready_at, order.picked_up_at, order.delivered_at]))

    def test_steps_cannot_be_skipped(self):
        self.assertStepError(self.step(self.owner, "ready"), 409, "invalid_transition")
        self.step(self.owner, "accept", prep_minutes=10)
        self.step(self.captain, "claim")
        self.assertStepError(self.step(self.captain, "pickup"), 409, "invalid_transition")

    def test_store_steps_need_the_store_owner(self):
        response = self.step(self.customer, "accept", prep_minutes=10)
        self.assertStepError(response, 403, "not_allowed")

    def test_unrelated_users_get_404(self):
        stranger = User.objects.create_user(phone="+9647700000040")
        self.assertEqual(self.step(stranger, "cancel").status_code, 404)

    def test_prep_minutes_is_validated(self):
        self.assertEqual(self.step(self.owner, "accept", prep_minutes=500).status_code, 400)

    def test_customer_can_cancel_before_store_accepts(self):
        response = self.step(self.customer, "cancel", reason="Ordered by mistake")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual((body["status"], body["cancelled_by"]), ("cancelled", "customer"))

    def test_customer_cannot_cancel_after_store_accepts(self):
        self.step(self.owner, "accept", prep_minutes=10)
        self.assertStepError(self.step(self.customer, "cancel"), 409, "invalid_transition")

    def test_store_rejects_with_reason(self):
        self.assertEqual(self.step(self.owner, "reject").status_code, 400)  # reason required
        response = self.step(self.owner, "reject", reason="Out of kebab today")
        body = response.json()
        self.assertEqual((body["status"], body["cancelled_by"], body["cancel_reason"]), ("cancelled", "vendor", "Out of kebab today"))

    @override_settings(PAYMENT_METHODS=["cod", "wallet"])  # the wallet is off by default
    def test_cancelled_wallet_order_is_refunded(self):
        User.objects.filter(pk=self.customer.pk).update(wallet_balance=30000)
        self.client.force_authenticate(self.customer)
        self.order_id = self.place(payment_type="wallet").json()["id"]

        response = self.step(self.owner, "reject", reason="Closing early")
        self.assertEqual(response.json()["payment_status"], "refunded")
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.wallet_balance, Decimal(30000))
        self.assertEqual(
            list(WalletTransaction.objects.filter(user=self.customer).order_by("created_at").values_list("type", "amount")),
            [("payment", Decimal(-25250)), ("refund", Decimal(25250))],
        )

    def test_only_one_captain_can_claim(self):
        self.step(self.owner, "accept", prep_minutes=10)
        self.assertEqual(self.step(self.captain, "claim").status_code, 200)
        self.assertEqual(self.step(self.captain, "claim").status_code, 200)  # repeat is harmless
        self.assertStepError(self.step(self.other_captain, "claim"), 409, "already_claimed")

    def test_customers_cannot_claim(self):
        self.step(self.owner, "accept", prep_minutes=10)
        self.assertStepError(self.step(self.customer, "claim"), 403, "not_allowed")

    def test_claim_needs_store_to_accept_first(self):
        self.assertStepError(self.step(self.captain, "claim"), 409, "invalid_transition")

    def test_other_captain_cannot_pick_up_or_deliver(self):
        self.deliver_ready_order()
        self.assertEqual(self.step(self.other_captain, "deliver", pin=self.pin()).status_code, 404)

    def test_wrong_pin_then_right_pin(self):
        self.deliver_ready_order()
        wrong = "0000" if self.pin() != "0000" else "1111"
        response = self.step(self.captain, "deliver", pin=wrong)
        self.assertStepError(response, 400, "wrong_pin")
        self.assertIn("4 attempts left", response.json()["detail"])
        self.assertEqual(self.order().pin_attempts, 1)
        self.assertEqual(self.step(self.captain, "deliver", pin=self.pin()).json()["status"], "delivered")

    def test_pin_locks_after_five_wrong_tries(self):
        self.deliver_ready_order()
        wrong = "0000" if self.pin() != "0000" else "1111"
        for _ in range(5):
            self.step(self.captain, "deliver", pin=wrong)
        self.assertStepError(self.step(self.captain, "deliver", pin=self.pin()), 423, "pin_locked")
        self.assertEqual(self.order().status, "out_for_delivery")

    def test_available_lists_unclaimed_accepted_orders_for_captains(self):
        self.client.force_authenticate(self.captain)
        self.assertEqual(self.client.get("/api/orders/available/").json()["results"], [])

        self.step(self.owner, "accept", prep_minutes=10)
        self.client.force_authenticate(self.captain)
        ids = [o["id"] for o in self.client.get("/api/orders/available/").json()["results"]]
        self.assertEqual(ids, [self.order_id])

        self.step(self.captain, "claim")
        self.client.force_authenticate(self.other_captain)
        self.assertEqual(self.client.get("/api/orders/available/").json()["results"], [])

    def test_available_is_captains_only(self):
        self.client.force_authenticate(self.customer)
        self.assertEqual(self.client.get("/api/orders/available/").status_code, 403)
