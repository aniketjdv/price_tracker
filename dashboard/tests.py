from decimal import Decimal

from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from .data_providers.simulator import SimulatorProvider
from .models import Category, Notification, Platform, PriceAlert, Product
from .services import detect_price_drop, update_simulated_prices


class ProviderTests(SimpleTestCase):
	def test_simulator_returns_api_shaped_response(self):
		response = SimulatorProvider(seed=7).get_products(count=1)
		product = response["products"][0]
		self.assertEqual(response["source"], "simulator")
		self.assertIn("external_id", product)
		self.assertIn("discount_percentage", product)

	def test_simulator_is_deterministic_for_a_seed(self):
		first = SimulatorProvider(seed=7).get_products(count=2)
		second = SimulatorProvider(seed=7).get_products(count=2)
		self.assertEqual(first, second)

	def test_price_drop_detection(self):
		result = detect_price_drop(Decimal("50000"), Decimal("45000"))
		self.assertTrue(result["dropped"])
		self.assertEqual(result["amount"], Decimal("5000"))
		self.assertEqual(result["percentage"], Decimal("10.00"))


class PriceAlertTests(TestCase):
	def setUp(self):
		self.platform = Platform.objects.create(name="Amazon", color="#FF9900", bg_color="#FFF7ED")
		self.category = Category.objects.create(name="Electronics")
		self.product = Product.objects.create(
			name="Sony WH-1000XM5",
			category=self.category,
			platform=self.platform,
			current_price=Decimal("25000.00"),
			original_price=Decimal("30000.00"),
			lowest_price=Decimal("24000.00"),
		)
		self.alert = PriceAlert.objects.create(
			product=self.product,
			target_price=Decimal("22000.00"),
			current_price=Decimal("25000.00"),
			status=PriceAlert.STATUS_WATCHING,
			email_on=True,
			sms_on=False,
		)

	def test_price_alerts_page_loads_and_shows_stats(self):
		response = self.client.get(reverse("dashboard:price_alerts"))
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Sony WH-1000XM5")
		self.assertContains(response, "₹22,000")
		self.assertEqual(response.context["total_count"], 1)
		self.assertEqual(response.context["watching_count"], 1)
		self.assertEqual(response.context["triggered_count"], 0)

	def test_price_alerts_filter_by_status(self):
		# Create a triggered alert
		product2 = Product.objects.create(
			name="Apple iPhone 15",
			category=self.category,
			platform=self.platform,
			current_price=Decimal("75000.00"),
		)
		PriceAlert.objects.create(
			product=product2,
			target_price=Decimal("76000.00"),
			current_price=Decimal("75000.00"),
			status=PriceAlert.STATUS_TRIGGERED,
		)

		response_watching = self.client.get(reverse("dashboard:price_alerts"), {"status": "watching"})
		self.assertEqual(len(response_watching.context["alerts"]), 1)
		self.assertEqual(response_watching.context["alerts"][0].product.name, "Sony WH-1000XM5")

		response_triggered = self.client.get(reverse("dashboard:price_alerts"), {"status": "triggered"})
		self.assertEqual(len(response_triggered.context["alerts"]), 1)
		self.assertEqual(response_triggered.context["alerts"][0].product.name, "Apple iPhone 15")

	def test_price_alerts_search(self):
		response = self.client.get(reverse("dashboard:price_alerts"), {"q": "Sony"})
		self.assertEqual(len(response.context["alerts"]), 1)

		response_empty = self.client.get(reverse("dashboard:price_alerts"), {"q": "NonExistent"})
		self.assertEqual(len(response_empty.context["alerts"]), 0)

	def test_create_price_alert_watching(self):
		product2 = Product.objects.create(
			name="Bose QuietComfort",
			category=self.category,
			platform=self.platform,
			current_price=Decimal("28000.00"),
		)
		response = self.client.post(reverse("dashboard:create_price_alert"), {
			"product": product2.id,
			"target_price": "24000",
			"email_on": "on",
		})
		self.assertRedirects(response, reverse("dashboard:price_alerts"))
		alert = PriceAlert.objects.get(product=product2)
		self.assertEqual(alert.target_price, Decimal("24000"))
		self.assertEqual(alert.status, PriceAlert.STATUS_WATCHING)
		self.assertTrue(alert.email_on)
		self.assertFalse(alert.sms_on)

	def test_create_price_alert_triggered_immediately(self):
		product2 = Product.objects.create(
			name="Kindle Paperwhite",
			category=self.category,
			platform=self.platform,
			current_price=Decimal("12000.00"),
		)
		# Target price is higher than current price -> triggered immediately
		response = self.client.post(reverse("dashboard:create_price_alert"), {
			"product": product2.id,
			"target_price": "13000",
			"email_on": "on",
		})
		self.assertRedirects(response, reverse("dashboard:price_alerts"))
		alert = PriceAlert.objects.get(product=product2)
		self.assertEqual(alert.status, PriceAlert.STATUS_TRIGGERED)
		self.assertTrue(Notification.objects.filter(type="alert", title="Target Price Reached!").exists())

	def test_edit_price_alert(self):
		response = self.client.post(reverse("dashboard:edit_price_alert", args=[self.alert.id]), {
			"target_price": "21000",
			"email_on": "on",
			"sms_on": "on",
			"status": "watching",
		})
		self.assertRedirects(response, reverse("dashboard:price_alerts"))
		self.alert.refresh_from_db()
		self.assertEqual(self.alert.target_price, Decimal("21000"))
		self.assertTrue(self.alert.sms_on)

	def test_delete_price_alert(self):
		response = self.client.post(reverse("dashboard:delete_price_alert", args=[self.alert.id]))
		self.assertRedirects(response, reverse("dashboard:price_alerts"))
		self.assertFalse(PriceAlert.objects.filter(id=self.alert.id).exists())

	def test_toggle_alert_status(self):
		self.assertEqual(self.alert.status, PriceAlert.STATUS_WATCHING)
		self.client.post(reverse("dashboard:toggle_alert_status", args=[self.alert.id]))
		self.alert.refresh_from_db()
		self.assertEqual(self.alert.status, PriceAlert.STATUS_TRIGGERED)

		self.client.post(reverse("dashboard:toggle_alert_status", args=[self.alert.id]))
		self.alert.refresh_from_db()
		self.assertEqual(self.alert.status, PriceAlert.STATUS_WATCHING)

	def test_product_detail_page_alert_integration(self):
		response = self.client.get(reverse("dashboard:product_detail", args=[self.product.id]))
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.context["user_alert"], self.alert)
		self.assertContains(response, "Active Price Alert")

	def test_update_simulated_prices_triggers_alert(self):
		from dashboard.models import ProductListing
		# Create product listing with external ID recognized by simulator
		listing = ProductListing.objects.create(
			product=self.product,
			platform=self.platform,
			external_product_id="SIM-AMA-001",
			current_price=Decimal("25000.00"),
			mrp=Decimal("30000.00"),
			availability=True,
		)
		# Set target price above the simulator price so it triggers
		self.alert.target_price = Decimal("100000.00")
		self.alert.status = PriceAlert.STATUS_WATCHING
		self.alert.save()

		update_simulated_prices()

		self.alert.refresh_from_db()
		self.assertEqual(self.alert.status, PriceAlert.STATUS_TRIGGERED)
		self.assertTrue(Notification.objects.filter(type="alert").exists())


class SettingsPageTests(TestCase):
	def setUp(self):
		from django.contrib.auth.models import User
		self.user = User.objects.create_user(
			username="testuser",
			email="test@example.com",
			password="password123",
			first_name="Test",
			last_name="User",
		)

	def test_settings_page_requires_login(self):
		response = self.client.get(reverse("dashboard:settings"))
		self.assertEqual(response.status_code, 302)

	def test_settings_page_authenticated_get(self):
		self.client.login(username="testuser", password="password123")
		response = self.client.get(reverse("dashboard:settings"))
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Account Settings")
		self.assertContains(response, "Personal Information")
		self.assertContains(response, "testuser")

	def test_settings_page_profile_update(self):
		self.client.login(username="testuser", password="password123")
		response = self.client.post(reverse("dashboard:settings"), {
			"first_name": "UpdatedFirst",
			"last_name": "UpdatedLast",
			"email": "updated@example.com",
			"phone": "+91 99999 88888",
		})
		self.assertRedirects(response, reverse("dashboard:settings"))
		self.user.refresh_from_db()
		self.assertEqual(self.user.first_name, "UpdatedFirst")
		self.assertEqual(self.user.last_name, "UpdatedLast")
		self.assertEqual(self.user.email, "updated@example.com")
		self.assertEqual(self.user.profile.phone, "+91 99999 88888")



