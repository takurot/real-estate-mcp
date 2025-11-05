#!/usr/bin/env python3
"""
API直接呼び出しテスト
API経由でデータが取得できていることを直接検証する
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_URL = "https://www.reinfolib.mlit.go.jp/ex-api/external/XIT001"


def test_api_direct_call():
    """APIを直接呼び出してデータ取得を検証"""
    print("=" * 60)
    print("API直接呼び出しテスト")
    print("=" * 60)
    print()
    
    api_key = os.getenv("HUDOUSAN_API_KEY")
    if not api_key:
        print("⚠ APIキーが設定されていません。スキップします。")
        return False
    
    # テスト用パラメータ
    params = {
        "year": 2023,
        "area": "13",  # 東京都
        "priceClassification": "01",
    }
    headers = {"Ocp-Apim-Subscription-Key": api_key}
    
    print(f"Test: API呼び出し（東京都、2023年）")
    print(f"URL: {API_URL}")
    print(f"Params: {params}")
    print()
    
    try:
        response = requests.get(API_URL, params=params, headers=headers, timeout=30)
        
        # ステータスコードの確認
        print(f"Status Code: {response.status_code}")
        assert response.status_code == 200, f"API should return 200, got {response.status_code}"
        
        # JSONレスポンスの確認
        data = response.json()
        assert "status" in data, "Response should contain 'status' field"
        assert data["status"] == "OK", f"API status should be 'OK', got '{data.get('status')}'"
        
        # データの存在確認
        assert "data" in data, "Response should contain 'data' field"
        assert isinstance(data["data"], list), "Data should be a list"
        
        data_count = len(data["data"])
        print(f"Data Count: {data_count} items")
        assert data_count > 0, f"API should return data, got {data_count} items"
        
        # データの構造確認（最初のアイテム）
        if data_count > 0:
            first_item = data["data"][0]
            required_fields = ["MunicipalityCode", "Municipality", "TradePrice", "PricePerUnit"]
            for field in required_fields:
                assert field in first_item, f"Data item should contain '{field}' field"
            
            print(f"First Item Sample:")
            print(f"  - MunicipalityCode: {first_item.get('MunicipalityCode')}")
            print(f"  - Municipality: {first_item.get('Municipality')}")
            print(f"  - TradePrice: {first_item.get('TradePrice')}")
            print(f"  - PricePerUnit: {first_item.get('PricePerUnit')}")
        
        print()
        print("✓ API直接呼び出しテスト passed")
        print(f"  - Status: {response.status_code}")
        print(f"  - API Status: {data['status']}")
        print(f"  - Data Items: {data_count}")
        print()
        return True
        
    except requests.exceptions.Timeout:
        print("✗ API call timed out")
        return False
    except requests.exceptions.RequestException as e:
        print(f"✗ API call failed: {e}")
        return False
    except AssertionError as e:
        print(f"✗ Assertion failed: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False


def test_api_without_key():
    """APIキーなしでの呼び出しが401を返すことを確認"""
    print("Test: APIキーなしでの呼び出し")
    
    params = {
        "year": 2023,
        "area": "13",
        "priceClassification": "01",
    }
    headers = {}  # APIキーなし
    
    try:
        response = requests.get(API_URL, params=params, headers=headers, timeout=10)
        assert response.status_code == 401, \
            f"API should return 401 without key, got {response.status_code}"
        
        data = response.json()
        assert "message" in data or "statusCode" in data, \
            "Error response should contain message or statusCode"
        
        print("✓ APIキーなしテスト passed (401 returned as expected)")
        print()
        return True
    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False


if __name__ == "__main__":
    test1 = test_api_direct_call()
    test2 = test_api_without_key()
    
    if test1 and test2:
        print("=" * 60)
        print("All API tests passed!")
        print("=" * 60)
        exit(0)
    else:
        print("=" * 60)
        print("Some API tests failed")
        print("=" * 60)
        exit(1)

