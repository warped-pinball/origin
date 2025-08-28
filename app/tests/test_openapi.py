def test_openapi_schema_available(client):
    response = client.get("/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert "paths" in data and "openapi" in data
