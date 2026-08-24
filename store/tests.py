from django.test import TestCase

from dashboard.services import seed_simulator_data
from dashboard.services import update_simulated_prices
from dashboard.models import Notification
from dashboard.models import ProductListing


class StoreSmokeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        seed_simulator_data(count=2, days=3, seed=42)

    def test_store_catalog_and_api_are_available(self):
        response = self.client.get("/store/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ShopSphere")

        listing = ProductListing.objects.first()
        response = self.client.get("/store/api/products/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["products"])

        response = self.client.get(f"/store/api/products/{listing.external_product_id}/price-history/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["history"]), 3)

    def test_store_url_starts_tracking_from_tracker_form(self):
        from django.contrib.auth.models import User
        user = User.objects.create_user(username="storeuser", password="storepassword")
        product = ProductListing.objects.select_related("product").first().product
        product.tracked = False
        product.save(update_fields=["tracked"])
        store_url = f"http://localhost:8000/store/product/{product.slug}/"

        # Unauthenticated request redirects to login
        unauth_response = self.client.post("/track-new/", {"url": store_url})
        self.assertRedirects(unauth_response, "/login/?next=%2Ftrack-new%2F")

        # Authenticated request succeeds
        self.client.login(username="storeuser", password="storepassword")
        response = self.client.post("/track-new/", {"url": store_url})

        product.refresh_from_db()
        self.assertRedirects(response, "/alerts/")
        self.assertTrue(product.tracked)
        self.assertTrue(product.alerts.filter(user=user).exists())

    def test_simulator_notifies_only_tracked_products(self):
        listings = list(ProductListing.objects.select_related("product")[:2])
        listings[0].product.tracked = True
        listings[0].product.save(update_fields=["tracked"])
        listings[1].product.tracked = False
        listings[1].product.save(update_fields=["tracked"])

        update_simulated_prices()

        self.assertFalse(Notification.objects.filter(body__contains=listings[1].product.name).exists())
