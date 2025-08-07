def test_reset_password_page(client):
    response = client.get('/reset-password')
    assert response.status_code == 200
    assert 'Reset Password' in response.text
