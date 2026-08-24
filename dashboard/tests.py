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
		from django.contrib.auth.models import User
		self.user = User.objects.create_user(username="alertuser", password="password123")
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
			user=self.user,
			product=self.product,
			target_price=Decimal("22000.00"),
			current_price=Decimal("25000.00"),
			status=PriceAlert.STATUS_WATCHING,
			email_on=True,
			sms_on=False,
		)

	def test_unauthenticated_cannot_access_price_alerts_page(self):
		response = self.client.get(reverse("dashboard:price_alerts"))
		self.assertEqual(response.status_code, 302)
		self.assertIn(reverse("dashboard:login"), response.url)

	def test_unauthenticated_cannot_create_price_alert(self):
		response = self.client.post(reverse("dashboard:create_price_alert"), {
			"product": self.product.id,
			"target_price": "20000",
		})
		self.assertEqual(response.status_code, 302)
		self.assertIn(reverse("dashboard:login"), response.url)

	def test_price_alerts_page_loads_and_shows_stats(self):
		self.client.login(username="alertuser", password="password123")
		response = self.client.get(reverse("dashboard:price_alerts"))
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Sony WH-1000XM5")
		self.assertContains(response, "₹22,000")
		self.assertEqual(response.context["total_count"], 1)
		self.assertEqual(response.context["watching_count"], 1)
		self.assertEqual(response.context["triggered_count"], 0)

	def test_price_alerts_filter_by_status(self):
		self.client.login(username="alertuser", password="password123")
		# Create a triggered alert for the logged in user
		product2 = Product.objects.create(
			name="Apple iPhone 15",
			category=self.category,
			platform=self.platform,
			current_price=Decimal("75000.00"),
		)
		PriceAlert.objects.create(
			user=self.user,
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
		self.client.login(username="alertuser", password="password123")
		response = self.client.get(reverse("dashboard:price_alerts"), {"q": "Sony"})
		self.assertEqual(len(response.context["alerts"]), 1)

		response_empty = self.client.get(reverse("dashboard:price_alerts"), {"q": "NonExistent"})
		self.assertEqual(len(response_empty.context["alerts"]), 0)

	def test_create_price_alert_watching(self):
		self.client.login(username="alertuser", password="password123")
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
		alert = PriceAlert.objects.get(product=product2, user=self.user)
		self.assertEqual(alert.target_price, Decimal("24000"))
		self.assertEqual(alert.status, PriceAlert.STATUS_WATCHING)
		self.assertTrue(alert.email_on)
		self.assertFalse(alert.sms_on)
		self.assertTrue(product2.tracked_by.filter(id=self.user.id).exists())

	def test_create_price_alert_triggered_immediately(self):
		self.client.login(username="alertuser", password="password123")
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
		alert = PriceAlert.objects.get(product=product2, user=self.user)
		self.assertEqual(alert.status, PriceAlert.STATUS_TRIGGERED)
		self.assertTrue(Notification.objects.filter(user=self.user, type="alert", title="Target Price Reached!").exists())

	def test_edit_price_alert(self):
		self.client.login(username="alertuser", password="password123")
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
		self.client.login(username="alertuser", password="password123")
		response = self.client.post(reverse("dashboard:delete_price_alert", args=[self.alert.id]))
		self.assertRedirects(response, reverse("dashboard:price_alerts"))
		self.assertFalse(PriceAlert.objects.filter(id=self.alert.id).exists())

	def test_toggle_alert_status(self):
		self.client.login(username="alertuser", password="password123")
		self.assertEqual(self.alert.status, PriceAlert.STATUS_WATCHING)
		self.client.post(reverse("dashboard:toggle_alert_status", args=[self.alert.id]))
		self.alert.refresh_from_db()
		self.assertEqual(self.alert.status, PriceAlert.STATUS_TRIGGERED)

		self.client.post(reverse("dashboard:toggle_alert_status", args=[self.alert.id]))
		self.alert.refresh_from_db()
		self.assertEqual(self.alert.status, PriceAlert.STATUS_WATCHING)

	def test_product_detail_page_alert_integration(self):
		self.client.login(username="alertuser", password="password123")
		response = self.client.get(reverse("dashboard:product_detail", args=[self.product.id]))
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.context["user_alert"], self.alert)
		self.assertContains(response, "Active Price Alert")

	def test_product_detail_page_shows_login_prompt_for_unauthenticated_user(self):
		response = self.client.get(reverse("dashboard:product_detail", args=[self.product.id]))
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Sign In to Track Product")

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


class TrackNewProductTests(TestCase):
	def setUp(self):
		from django.contrib.auth.models import User
		self.user = User.objects.create_user(username="trackeruser", password="password123")
		self.platform = Platform.objects.create(name="Amazon", color="#FF9900", bg_color="#FFF7ED")
		self.category = Category.objects.create(name="Laptops")
		self.product = Product.objects.create(
			name="Apple MacBook Air M2",
			slug="apple-macbook-air-m2",
			category=self.category,
			platform=self.platform,
			current_price=Decimal("92990.00"),
			original_price=Decimal("99990.00"),
			lowest_price=Decimal("89990.00"),
			tracked=False,
		)

	def test_unauthenticated_cannot_access_track_new(self):
		response = self.client.get(reverse("dashboard:track_new"))
		self.assertEqual(response.status_code, 302)
		self.assertIn(reverse("dashboard:login"), response.url)

	def test_track_new_get_with_url_previews_product(self):
		self.client.login(username="trackeruser", password="password123")
		response = self.client.get(reverse("dashboard:track_new"), {
			"url": f"http://127.0.0.1:8000/store/product/{self.product.slug}/"
		})
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.context["store_product"], self.product)
		self.assertContains(response, "Apple MacBook Air M2")
		self.assertContains(response, "Target Price")

	def test_track_new_post_creates_price_alert_and_redirects_to_alerts(self):
		self.client.login(username="trackeruser", password="password123")
		url = f"http://127.0.0.1:8000/store/product/{self.product.slug}/"
		response = self.client.post(reverse("dashboard:track_new"), {
			"url": url,
			"target_price": "85000",
			"email_on": "on",
		})
		self.assertRedirects(response, reverse("dashboard:price_alerts"))

		self.product.refresh_from_db()
		self.assertTrue(self.product.tracked)
		self.assertTrue(self.product.tracked_by.filter(id=self.user.id).exists())
		self.assertEqual(self.product.url, url)

		alert = PriceAlert.objects.filter(product=self.product, user=self.user).first()
		self.assertIsNotNone(alert)
		self.assertEqual(alert.target_price, Decimal("85000"))
		self.assertEqual(alert.status, PriceAlert.STATUS_WATCHING)
		self.assertTrue(alert.email_on)

	def test_track_new_post_unrecognized_url_shows_error(self):
		self.client.login(username="trackeruser", password="password123")
		response = self.client.post(reverse("dashboard:track_new"), {
			"url": "https://example.com/invalid-non-existent-product"
		})
		self.assertEqual(response.status_code, 200)
		self.assertTrue(response.context["url_error"])


class UserIsolationTests(TestCase):
	def setUp(self):
		from django.contrib.auth.models import User
		self.user1 = User.objects.create_user(username="user1", password="password1")
		self.user2 = User.objects.create_user(username="user2", password="password2")

		self.platform = Platform.objects.create(name="Amazon", color="#FF9900", bg_color="#FFF7ED")
		self.category = Category.objects.create(name="Electronics")
		self.product1 = Product.objects.create(
			name="Product One",
			category=self.category,
			platform=self.platform,
			current_price=Decimal("10000.00"),
		)
		self.product2 = Product.objects.create(
			name="Product Two",
			category=self.category,
			platform=self.platform,
			current_price=Decimal("20000.00"),
		)

		# User 1 has alert for Product 1 and tracks Product 1
		self.alert1 = PriceAlert.objects.create(
			user=self.user1,
			product=self.product1,
			target_price=Decimal("9000.00"),
			current_price=Decimal("10000.00"),
			status=PriceAlert.STATUS_WATCHING,
		)
		self.product1.tracked_by.add(self.user1)

		# User 2 has alert for Product 2 and tracks Product 2
		self.alert2 = PriceAlert.objects.create(
			user=self.user2,
			product=self.product2,
			target_price=Decimal("18000.00"),
			current_price=Decimal("20000.00"),
			status=PriceAlert.STATUS_WATCHING,
		)
		self.product2.tracked_by.add(self.user2)

	def test_user_only_sees_their_own_alerts(self):
		self.client.login(username="user1", password="password1")
		response = self.client.get(reverse("dashboard:price_alerts"))
		self.assertEqual(response.status_code, 200)
		self.assertEqual(len(response.context["alerts"]), 1)
		self.assertEqual(response.context["alerts"][0].product.name, "Product One")
		self.assertEqual(response.context["total_count"], 1)

		self.client.login(username="user2", password="password2")
		response = self.client.get(reverse("dashboard:price_alerts"))
		self.assertEqual(response.status_code, 200)
		self.assertEqual(len(response.context["alerts"]), 1)
		self.assertEqual(response.context["alerts"][0].product.name, "Product Two")
		self.assertEqual(response.context["total_count"], 1)

	def test_user_only_sees_their_own_tracked_products(self):
		self.client.login(username="user1", password="password1")
		response = self.client.get(reverse("dashboard:products") + "?tracked=1")
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Product One")
		self.assertNotContains(response, "Product Two")

		self.client.login(username="user2", password="password2")
		response = self.client.get(reverse("dashboard:products") + "?tracked=1")
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Product Two")
		self.assertNotContains(response, "Product One")

	def test_delete_alert_permission_isolation(self):
		# User 1 tries to delete User 2's alert
		self.client.login(username="user1", password="password1")
		response = self.client.post(reverse("dashboard:delete_price_alert", args=[self.alert2.id]))
		self.assertTrue(PriceAlert.objects.filter(id=self.alert2.id).exists())

		# User 1 deletes their own alert
		response = self.client.post(reverse("dashboard:delete_price_alert", args=[self.alert1.id]))
		self.assertFalse(PriceAlert.objects.filter(id=self.alert1.id).exists())


class DashboardHomeTests(TestCase):
	def test_dashboard_home_loads_with_interactive_elements(self):
		response = self.client.get(reverse("dashboard:dashboard_home"))
		self.assertEqual(response.status_code, 200)
		self.assertIn("chart_products", response.context)
		self.assertIn("donut_gradient", response.context)
		self.assertIn("total_products", response.context)
		self.assertIn("tracked_count", response.context)
		self.assertContains(response, "Price History Trend")
		self.assertContains(response, "Products by Platform")
		self.assertContains(response, "priceHistoryCanvas")


class NotificationPageTests(TestCase):
	def setUp(self):
		from django.contrib.auth.models import User
		self.user = User.objects.create_user(username="testuser", password="password")
		self.notif1 = Notification.objects.create(
			user=self.user,
			type="drop",
			title="Price Drop Alert",
			body="MacBook dropped ₹5,000",
			read=False,
		)
		self.notif_public = Notification.objects.create(
			user=None,
			type="offer",
			title="Weekend Sale",
			body="Big sale is live",
			read=False,
		)

	def test_notifications_page_loads_for_authenticated_user(self):
		self.client.login(username="testuser", password="password")
		response = self.client.get(reverse("dashboard:notifications"))
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Price Drop Alert")
		self.assertContains(response, "Weekend Sale")

	def test_mark_all_notifications_read(self):
		self.client.login(username="testuser", password="password")
		response = self.client.post(reverse("dashboard:notifications"))
		self.assertRedirects(response, reverse("dashboard:notifications"))
		self.notif1.refresh_from_db()
		self.assertTrue(self.notif1.read)


class AdminProductManagementTests(TestCase):
	def setUp(self):
		from django.contrib.auth.models import User
		self.admin_user = User.objects.create_user(username="adminuser", password="adminpassword", is_staff=True)
		self.regular_user = User.objects.create_user(username="regularuser", password="regularpassword", is_staff=False)
		self.platform = Platform.objects.create(name="Amazon", color="#FF9900", bg_color="#FFF7ED")
		self.category = Category.objects.create(name="Smartphones")
		self.product = Product.objects.create(
			name="Samsung Galaxy S24",
			brand="Samsung",
			category=self.category,
			platform=self.platform,
			current_price=Decimal("79999.00"),
			original_price=Decimal("89999.00"),
			lowest_price=Decimal("74999.00"),
			description="Flagship smartphone",
		)

	def test_non_staff_redirected_from_admin_dashboard(self):
		self.client.login(username="regularuser", password="regularpassword")
		response = self.client.get(reverse("dashboard:admin_dashboard"))
		self.assertEqual(response.status_code, 302)

	def test_staff_can_view_admin_dashboard_with_products(self):
		self.client.login(username="adminuser", password="adminpassword")
		response = self.client.get(reverse("dashboard:admin_dashboard"))
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Samsung Galaxy S24")
		self.assertContains(response, "Product Management")

	def test_staff_can_create_product(self):
		self.client.login(username="adminuser", password="adminpassword")
		response = self.client.post(reverse("dashboard:admin_create_product"), {
			"name": "Google Pixel 9",
			"brand": "Google",
			"category": self.category.id,
			"platform": self.platform.id,
			"current_price": "75000",
			"original_price": "82000",
			"lowest_price": "75000",
			"discount": "8",
			"stock": "In Stock",
			"description": "Google AI flagship",
		})
		self.assertRedirects(response, f"{reverse('dashboard:admin_dashboard')}?tab=products")
		self.assertTrue(Product.objects.filter(name="Google Pixel 9").exists())
		created_product = Product.objects.get(name="Google Pixel 9")
		self.assertEqual(created_product.brand, "Google")
		self.assertEqual(created_product.current_price, Decimal("75000"))

	def test_staff_can_edit_product(self):
		self.client.login(username="adminuser", password="adminpassword")
		response = self.client.post(reverse("dashboard:admin_edit_product", args=[self.product.id]), {
			"name": "Samsung Galaxy S24 Ultra",
			"brand": "Samsung",
			"category": self.category.id,
			"platform": self.platform.id,
			"current_price": "69999",
			"original_price": "89999",
			"lowest_price": "69999",
			"discount": "22",
			"stock": "In Stock",
			"description": "Updated flagship with S Pen",
			"prediction": "Lowest price of the season",
		})
		self.assertRedirects(response, f"{reverse('dashboard:admin_dashboard')}?tab=products")
		self.product.refresh_from_db()
		self.assertEqual(self.product.name, "Samsung Galaxy S24 Ultra")
		self.assertEqual(self.product.current_price, Decimal("69999"))
		self.assertEqual(self.product.description, "Updated flagship with S Pen")
		self.assertEqual(self.product.prediction, "Lowest price of the season")

	def test_staff_can_delete_product(self):
		self.client.login(username="adminuser", password="adminpassword")
		response = self.client.post(reverse("dashboard:admin_delete_product", args=[self.product.id]))
		self.assertRedirects(response, f"{reverse('dashboard:admin_dashboard')}?tab=products")
		self.assertFalse(Product.objects.filter(id=self.product.id).exists())








