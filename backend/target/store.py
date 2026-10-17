"""One laptop, one unit, integer cents, no real commerce or external calls."""
from uuid import uuid4
from .policy import Policy, TargetError

CATALOG_CENTS = 50000
MINIMUM_CENTS = 45000
PROMOTION = "SAVE10"
CHECKOUT_KEYS = {"product_id", "quantity", "client_price_cents", "promotion_code"}


def checkout(arguments: dict, policy: Policy) -> dict:
    if not isinstance(arguments, dict) or not set(arguments) <= CHECKOUT_KEYS:
        raise TargetError("invalid_checkout_schema")
    if arguments.get("product_id") != "laptop":
        raise TargetError("invalid_product")
    if type(arguments.get("quantity")) is not int or arguments["quantity"] != 1:
        raise TargetError("invalid_quantity")
    has_price = "client_price_cents" in arguments
    price = arguments.get("client_price_cents")
    if has_price and (type(price) is not int or not 0 <= price <= CATALOG_CENTS):
        raise TargetError("invalid_amount")
    promotion = arguments.get("promotion_code")
    if promotion is not None and (not isinstance(promotion, str) or promotion != PROMOTION):
        raise TargetError("invalid_promotion")

    authorized_discount = min(1000, policy.max_discount_bps) if promotion == PROMOTION else 0
    catalog_total = CATALOG_CENTS * (10000 - authorized_discount) // 10000
    denied = has_price and policy.reject_client_price
    # Intentional failure injection: v1 trusts an attacker-controlled checkout price.
    charged = catalog_total if policy.require_catalog_price or not has_price else price
    return {
        "receipt_id": str(uuid4()), "tool": "checkout", "product_id": "laptop", "quantity": 1,
        "trusted_catalog_total_cents": CATALOG_CENTS,
        "charged_total_cents": None if denied else charged,
        "minimum_allowed_total_cents": MINIMUM_CENTS,
        "status": "denied" if denied else "accepted", "side_effect": "simulated_order",
        "policy_version": policy.version,
    }
