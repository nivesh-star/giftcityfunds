import sys
from pathlib import Path

import pytest

# Ensure root workspace is in sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_index_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"GIFT360" in response.data
    assert b"Funds Intelligence Platform" in response.data


def test_api_stats(client):
    response = client.get("/api/stats")
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["summary"]["total_funds"] >= 70
    assert data["summary"]["tier1_verified"] >= 20
    assert data["summary"]["tier2_directory"] >= 40
    assert "amc_distribution" in data["charts"]
    assert "category_distribution" in data["charts"]


def test_api_funds_all(client):
    response = client.get("/api/funds")
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["count"] >= 70
    assert len(data["funds"]) >= 70


def test_api_funds_filtered_search(client):
    response = client.get("/api/funds?q=HDFC")
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["count"] >= 5


def test_api_funds_tier_filter(client):
    response = client.get("/api/funds?tier=tier1_amc")
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["count"] >= 20


def test_api_fund_detail(client):
    # Fetch first fund ID
    funds_res = client.get("/api/funds")
    first_id = funds_res.get_json()["funds"][0]["fund_id"]

    response = client.get(f"/api/fund/{first_id}")
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert "fund_name" in data["fund"]
    assert "related_funds" in data["fund"]


def test_api_compare(client):
    funds_res = client.get("/api/funds")
    ids = [str(f["fund_id"]) for f in funds_res.get_json()["funds"][:3]]
    id_str = ",".join(ids)

    response = client.get(f"/api/compare?ids={id_str}")
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["count"] == 3


def test_api_export_csv(client):
    response = client.get("/api/export/csv")
    assert response.status_code == 200
    assert response.mimetype == "text/csv"
    assert b"fund_name" in response.data


def test_api_export_json(client):
    response = client.get("/api/export/json")
    assert response.status_code == 200
    assert response.mimetype == "application/json"
    data = response.get_json()
    assert len(data) >= 70

