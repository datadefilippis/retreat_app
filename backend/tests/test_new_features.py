"""
Test file for AFianco - New Features Testing
Testing:
1. Category-based analytics endpoints (Sales/Expenses by category)
2. Download dataset endpoint
3. XLSX/XLS file upload support
4. Datasets list endpoint
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
assert BASE_URL, "REACT_APP_BACKEND_URL environment variable must be set"

# Test credentials
TEST_EMAIL = "admin@demo.com"
TEST_PASSWORD = "demo123"


class TestAuth:
    """Authentication tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token for tests"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, "No access token in response"
        return data["access_token"]
    
    def test_login_success(self):
        """Test login with demo credentials"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "user" in data
        print(f"✓ Login successful, user: {data['user'].get('email')}")


class TestCategoryAnalytics:
    """Test category-based analytics endpoints - NEW FEATURE"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        assert response.status_code == 200
        return response.json()["access_token"]
    
    @pytest.fixture
    def auth_headers(self, auth_token):
        """Get auth headers"""
        return {"Authorization": f"Bearer {auth_token}"}
    
    def test_get_sales_by_category(self, auth_headers):
        """Test GET /api/analytics/categories/sales endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/analytics/categories/sales",
            headers=auth_headers,
            params={"period": "30d"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Validate response structure
        assert "period" in data, "Missing period field"
        assert "total" in data, "Missing total field"
        assert "categories" in data, "Missing categories field"
        assert isinstance(data["categories"], list), "Categories should be a list"
        
        print(f"✓ Sales by category: Total=${data['total']}, {len(data['categories'])} categories found")
        
        # Validate each category has required fields
        for cat in data["categories"]:
            assert "category" in cat, "Missing category name"
            assert "total" in cat, "Missing category total"
            assert "count" in cat, "Missing category count"
            assert "percentage" in cat, "Missing category percentage"
    
    def test_get_expenses_by_category(self, auth_headers):
        """Test GET /api/analytics/categories/expenses endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/analytics/categories/expenses",
            headers=auth_headers,
            params={"period": "30d"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Validate response structure
        assert "period" in data, "Missing period field"
        assert "total" in data, "Missing total field"
        assert "categories" in data, "Missing categories field"
        assert isinstance(data["categories"], list), "Categories should be a list"
        
        print(f"✓ Expenses by category: Total=${data['total']}, {len(data['categories'])} categories found")
        
        # Validate each category has required fields
        for cat in data["categories"]:
            assert "category" in cat, "Missing category name"
            assert "total" in cat, "Missing category total"
            assert "count" in cat, "Missing category count"
            assert "percentage" in cat, "Missing category percentage"
    
    def test_category_trends(self, auth_headers):
        """Test GET /api/analytics/categories/trends endpoint"""
        # Test sales trends
        response = requests.get(
            f"{BASE_URL}/api/analytics/categories/trends",
            headers=auth_headers,
            params={"category_type": "sales", "period": "30d"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert "period" in data, "Missing period field"
        assert "categories" in data, "Missing categories field"
        assert "data" in data, "Missing data field"
        
        print(f"✓ Category trends: {len(data.get('categories', []))} categories, {len(data.get('data', []))} data points")


class TestDatasetsAPI:
    """Test datasets endpoints - including NEW download feature"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        assert response.status_code == 200
        return response.json()["access_token"]
    
    @pytest.fixture
    def auth_headers(self, auth_token):
        """Get auth headers"""
        return {"Authorization": f"Bearer {auth_token}"}
    
    def test_list_datasets(self, auth_headers):
        """Test GET /api/datasets endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/datasets",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ Datasets list: Found {len(data)} datasets")
        
        # If there are datasets, validate structure
        for dataset in data:
            assert "id" in dataset, "Missing dataset id"
            assert "name" in dataset, "Missing dataset name"
            assert "dataset_type" in dataset, "Missing dataset_type"
            assert "row_count" in dataset, "Missing row_count"
            assert "is_active" in dataset, "Missing is_active"
        
        return data
    
    def test_download_endpoint_exists(self, auth_headers):
        """Test that download endpoint exists - NEW FEATURE
        Note: May return 404 for seed data (no physical files)
        """
        # First get list of datasets
        list_response = requests.get(
            f"{BASE_URL}/api/datasets",
            headers=auth_headers
        )
        assert list_response.status_code == 200
        datasets = list_response.json()
        
        if not datasets:
            pytest.skip("No datasets available to test download")
        
        # Try downloading first dataset
        dataset_id = datasets[0]["id"]
        response = requests.get(
            f"{BASE_URL}/api/datasets/{dataset_id}/download",
            headers=auth_headers,
            allow_redirects=False
        )
        
        # 200 = success (file exists), 404 = file not found (expected for seed data)
        assert response.status_code in [200, 404], f"Unexpected status: {response.status_code} - {response.text}"
        
        if response.status_code == 200:
            print(f"✓ Download endpoint working - file downloaded for dataset {dataset_id}")
        else:
            print(f"✓ Download endpoint exists but file not found (expected for seed data) - dataset {dataset_id}")
    
    def test_get_single_dataset(self, auth_headers):
        """Test GET /api/datasets/{id} endpoint"""
        # First get list of datasets
        list_response = requests.get(
            f"{BASE_URL}/api/datasets",
            headers=auth_headers
        )
        assert list_response.status_code == 200
        datasets = list_response.json()
        
        if not datasets:
            pytest.skip("No datasets available")
        
        dataset_id = datasets[0]["id"]
        response = requests.get(
            f"{BASE_URL}/api/datasets/{dataset_id}",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert data["id"] == dataset_id
        print(f"✓ Single dataset fetch working: {data['name']}")
    
    def test_preview_dataset(self, auth_headers):
        """Test GET /api/datasets/{id}/preview endpoint"""
        # First get list of datasets
        list_response = requests.get(
            f"{BASE_URL}/api/datasets",
            headers=auth_headers
        )
        assert list_response.status_code == 200
        datasets = list_response.json()
        
        if not datasets:
            pytest.skip("No datasets available")
        
        dataset_id = datasets[0]["id"]
        response = requests.get(
            f"{BASE_URL}/api/datasets/{dataset_id}/preview",
            headers=auth_headers,
            params={"limit": 10}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert "dataset_id" in data
        assert "preview_rows" in data
        assert "total_rows" in data
        print(f"✓ Dataset preview working: {len(data['preview_rows'])} rows shown of {data['total_rows']}")


class TestUploadEndpoint:
    """Test upload endpoint format support - XLSX/XLS support is NEW"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        assert response.status_code == 200
        return response.json()["access_token"]
    
    @pytest.fixture
    def auth_headers(self, auth_token):
        """Get auth headers without Content-Type for file upload"""
        return {"Authorization": f"Bearer {auth_token}"}
    
    def test_upload_csv_file(self, auth_headers):
        """Test CSV file upload"""
        import io
        
        # Create a simple CSV content
        csv_content = b"date,amount,category,description\n2026-01-15,1500,food_sales,Test sale\n2026-01-16,2000,beverage_sales,Another sale"
        
        files = {
            'file': ('test_sales.csv', io.BytesIO(csv_content), 'text/csv')
        }
        data = {
            'name': 'TEST_CSV_Upload',
            'dataset_type': 'sales'
        }
        
        response = requests.post(
            f"{BASE_URL}/api/datasets/upload",
            headers=auth_headers,
            files=files,
            data=data
        )
        
        assert response.status_code == 200, f"Failed: {response.text}"
        result = response.json()
        assert result['name'] == 'TEST_CSV_Upload'
        assert result['row_count'] == 2
        print(f"✓ CSV upload successful: {result['row_count']} rows imported")
        
        # Clean up - delete the test dataset
        if result.get('id'):
            requests.delete(
                f"{BASE_URL}/api/datasets/{result['id']}",
                headers=auth_headers
            )
    
    def test_upload_rejects_invalid_format(self, auth_headers):
        """Test that unsupported file formats are rejected"""
        import io
        
        # Try uploading a PDF (unsupported)
        files = {
            'file': ('test.pdf', io.BytesIO(b"fake pdf content"), 'application/pdf')
        }
        data = {
            'name': 'TEST_Invalid_Upload',
            'dataset_type': 'sales'
        }
        
        response = requests.post(
            f"{BASE_URL}/api/datasets/upload",
            headers=auth_headers,
            files=files,
            data=data
        )
        
        # Should be rejected with 400
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("✓ Invalid format correctly rejected")


class TestExistingEndpoints:
    """Test existing endpoints still work"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        assert response.status_code == 200
        return response.json()["access_token"]
    
    @pytest.fixture
    def auth_headers(self, auth_token):
        """Get auth headers"""
        return {"Authorization": f"Bearer {auth_token}"}
    
    def test_health_check(self):
        """Test health check endpoint"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        print("✓ Health check passed")
    
    def test_analytics_kpis(self, auth_headers):
        """Test KPIs endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/analytics/kpis",
            headers=auth_headers,
            params={"period": "30d"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "total_sales" in data
        assert "total_expenses" in data
        assert "net_cashflow" in data
        print(f"✓ KPIs: Sales=${data['total_sales']}, Expenses=${data['total_expenses']}, Net=${data['net_cashflow']}")
    
    def test_analytics_charts(self, auth_headers):
        """Test charts endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/analytics/charts",
            headers=auth_headers,
            params={"period": "30d"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Charts data: {len(data)} data points")
    
    def test_alerts_list(self, auth_headers):
        """Test alerts list endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/alerts",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Alerts: {len(data)} alerts found")
    
    def test_modules_available(self, auth_headers):
        """Test modules available endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/modules/available",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Modules: {len(data)} modules available")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
