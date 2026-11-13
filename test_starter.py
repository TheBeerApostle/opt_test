import asyncio
import unittest
from decimal import Decimal

from starter import recommend_price, sample_fetch_offers


def offers(*items, status="success"):
    async def fetch():
        return {
            "status": status,
            "offers": [
                {"seller": s, "price": Decimal(p), "delivery_days": d} for s, p, d in items
            ],
        }
    return fetch


class RecommendPriceTests(unittest.IsolatedAsyncioTestCase):
    async def test_basic_example(self):
        res = await recommend_price(sample_fetch_offers, Decimal("4900.00"), Decimal("4500.00"))
        self.assertEqual(res["price"], Decimal("4728.00"))
        self.assertEqual(res["decision"], "APPLY")
        self.assertIsInstance(res["price"], Decimal)

    async def test_rounds_down_to_kopeck(self):
        f = offers(("A", "4700.01", 1))  # 4629.50985 -> 4629.50
        res = await recommend_price(f, Decimal("4700.00"), Decimal("4000.00"))
        self.assertEqual(res["price"], Decimal("4629.50"))

    async def test_min_price_floor(self):
        f = offers(("A", "1000.00", 1))
        res = await recommend_price(f, Decimal("4600.00"), Decimal("4500.00"))
        self.assertEqual(res["price"], Decimal("4500.00"))
        self.assertEqual(res["decision"], "APPLY")

    async def test_exactly_30_percent_is_apply(self):
        f = offers(("A", "50.00", 1))
        down = await recommend_price(f, Decimal("100.00"), Decimal("70.00"))
        up = await recommend_price(offers(("A", "100.00", 1)), Decimal("100.00"), Decimal("130.00"))
        self.assertEqual((down["price"], down["decision"]), (Decimal("70.00"), "APPLY"))
        self.assertEqual((up["price"], up["decision"]), (Decimal("130.00"), "APPLY"))

    async def test_over_30_percent_is_review(self):
        f = offers(("A", "50.00", 1))
        res = await recommend_price(f, Decimal("100.00"), Decimal("69.99"))
        self.assertEqual(res["price"], Decimal("69.99"))
        self.assertEqual(res["decision"], "REVIEW")

    async def test_timeout_returns_hold(self):
        async def slow():
            await asyncio.sleep(1)
            return {"status": "success", "offers": []}
        res = await recommend_price(slow, Decimal("100.00"), Decimal("50.00"), timeout_s=0.05)
        self.assertEqual((res["price"], res["decision"]), (Decimal("100.00"), "HOLD"))

    async def test_source_exception_returns_hold(self):
        async def broken():
            raise RuntimeError("boom")
        res = await recommend_price(broken, Decimal("100.00"), Decimal("50.00"))
        self.assertEqual((res["price"], res["decision"]), (Decimal("100.00"), "HOLD"))

    async def test_partial_and_error_status_return_hold(self):
        for status in ("partial", "error"):
            f = offers(("A", "10.00", 1), status=status)
            res = await recommend_price(f, Decimal("100.00"), Decimal("50.00"))
            self.assertEqual(res["decision"], "HOLD")
            self.assertEqual(res["price"], Decimal("100.00"))

    async def test_no_suitable_offers_hold_even_below_min(self):
        f = offers(("MyShop", "10.00", 1), ("SLOW", "10.00", 7), ("NODATA", "10.00", None))
        res = await recommend_price(f, Decimal("40.00"), Decimal("50.00"))  # текущая ниже min_price
        self.assertEqual((res["price"], res["decision"]), (Decimal("40.00"), "HOLD"))

    async def test_own_shop_excluded_case_insensitive_and_6_days_ok(self):
        f = offers(("mYsHoP", "10.00", 1), ("A", "100.00", 6), ("B", "90.00", None))
        res = await recommend_price(f, Decimal("100.00"), Decimal("50.00"))
        self.assertEqual(res["price"], Decimal("98.50"))


if __name__ == "__main__":
    unittest.main()