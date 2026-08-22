from decimal import Decimal

from django.test import SimpleTestCase

from .data_providers.simulator import SimulatorProvider
from .services import detect_price_drop


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
