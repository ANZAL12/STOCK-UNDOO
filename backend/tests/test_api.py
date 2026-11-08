"""
Unit tests for STOCK UNDO! FastAPI Backend
"""

import sys
import unittest
from pathlib import Path
from fastapi.testclient import TestClient

# Ensure app is in python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.main import app
from app.models.stock import StockStatus


class TestStockUndoAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_health_endpoint(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["app_name"], "STOCK UNDO!")
        self.assertEqual(data["tagline"], "Check stock before you call the godown!")

    def test_tally_status_endpoint(self):
        response = self.client.get("/api/tally/status")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("pc1", data)
        self.assertIn("pc2", data)
        self.assertEqual(data["pc1"]["pc"], "pc1")
        self.assertEqual(data["pc2"]["pc"], "pc2")

    def test_whitelist_endpoint(self):
        response = self.client.get("/api/stock/whitelist")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertGreater(data["total_models"], 0)
        self.assertIsInstance(data["models"], list)

    def test_all_stock_endpoint(self):
        response = self.client.get("/api/stock/all")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("pc1_status", data)
        self.assertIn("pc2_status", data)
        self.assertIn("items", data)
        self.assertGreater(len(data["items"]), 0)

    def test_search_stock_endpoint(self):
        response = self.client.get("/api/stock/search?q=FORMENTY")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        for item in data:
            self.assertIn("FORMENTY", item["model"].upper())


if __name__ == "__main__":
    unittest.main()
