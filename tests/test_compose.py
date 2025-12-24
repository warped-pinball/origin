from pathlib import Path

import yaml


def _load_compose():
    compose_path = Path(__file__).resolve().parents[1] / "docker-compose.yml"
    return yaml.safe_load(compose_path.read_text())


def test_app_service_only_exposes_http_port():
    compose = _load_compose()
    app_service = compose["services"]["app"]

    assert app_service["build"]["dockerfile"] == "api_app/Dockerfile"
    assert "8000:8000" in app_service["ports"]
    assert all("udp" not in port.lower() for port in app_service["ports"])


def test_ray_service_handles_udp_ports():
    compose = _load_compose()
    ray_service = compose["services"]["ray"]

    assert ray_service["build"]["dockerfile"] == "ray_app/Dockerfile"
    assert ray_service.get("network_mode") == "host"


def test_ray_uses_api_credentials_not_database_volume():
    compose = _load_compose()
    app_env = compose["services"]["app"].get("environment", [])
    ray_env = compose["services"]["ray"].get("environment", [])

    assert any(env.startswith("RAY_PASSWORD=") for env in app_env)
    assert any(env.startswith("RAY_API_PASSWORD=") for env in ray_env)
    assert any(env.startswith("RAY_API_URL=") for env in ray_env)
    assert not compose["services"]["ray"].get("volumes")


def test_ray_targets_localhost_api_when_host_networked():
    compose = _load_compose()
    ray_env = compose["services"]["ray"].get("environment", [])

    assert "RAY_API_URL=http://127.0.0.1:8000" in ray_env
