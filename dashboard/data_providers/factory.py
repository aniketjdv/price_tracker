from django.conf import settings

from .amazon import AmazonProvider
from .flipkart import FlipkartProvider
from .simulator import SimulatorProvider


PROVIDERS = {
    "simulator": SimulatorProvider,
    "amazon": AmazonProvider,
    "flipkart": FlipkartProvider,
}


def get_provider(name=None):
    provider_name = (name or getattr(settings, "ECOMMERCE_PROVIDER", "simulator")).lower()
    try:
        provider_class = PROVIDERS[provider_name]
    except KeyError as exc:
        raise ValueError(f"Unknown e-commerce provider: {provider_name}") from exc

    if provider_name == "simulator":
        return provider_class()

    credentials = {
        "api_key": getattr(settings, "AMAZON_API_KEY", "") if provider_name == "amazon" else getattr(settings, "FLIPKART_API_KEY", ""),
        "api_secret": getattr(settings, "AMAZON_API_SECRET", ""),
        "partner_tag": getattr(settings, "AMAZON_PARTNER_TAG", ""),
        "affiliate_id": getattr(settings, "FLIPKART_AFFILIATE_ID", ""),
    }
    return provider_class(**credentials)
