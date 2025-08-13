import pytest


@pytest.mark.parametrize(
    "path, text",
    [
        ("/reset-password", "Reset Password"),
        ("/signup/success", "Account Created"),
    ],
)
def test_template_pages(client, path, text):
    response = client.get(path)
    assert response.status_code == 200
    assert text in response.text
