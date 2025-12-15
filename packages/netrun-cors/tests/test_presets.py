"""Tests for CORS preset configurations."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from netrun_cors import CORSPreset


class TestDevelopmentPreset:
    """Test development CORS preset."""

    def test_development_allows_localhost_3000(self, app):
        """Test development preset allows localhost:3000."""
        middleware = CORSPreset.development()
        app.add_middleware(middleware)
        client = TestClient(app)

        @app.get("/test")
        def test_endpoint():
            return {"status": "ok"}

        response = client.get("/test", headers={"Origin": "http://localhost:3000"})
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"

    def test_development_allows_localhost_5173(self, app):
        """Test development preset allows localhost:5173 (Vite)."""
        middleware = CORSPreset.development()
        app.add_middleware(middleware)
        client = TestClient(app)

        @app.get("/test")
        def test_endpoint():
            return {"status": "ok"}

        response = client.get("/test", headers={"Origin": "http://localhost:5173"})
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"

    def test_development_allows_credentials(self, app):
        """Test development preset allows credentials."""
        middleware = CORSPreset.development()
        app.add_middleware(middleware)
        client = TestClient(app)

        @app.get("/test")
        def test_endpoint():
            return {"status": "ok"}

        response = client.get("/test", headers={"Origin": "http://localhost:3000"})
        assert response.headers.get("access-control-allow-credentials") == "true"

    def test_development_exposes_headers(self, app):
        """Test development preset exposes X-Request-ID and X-Process-Time."""
        middleware = CORSPreset.development()
        app.add_middleware(middleware)
        client = TestClient(app)

        @app.get("/test")
        def test_endpoint():
            return {"status": "ok"}

        # Test actual GET request (exposed headers shown in actual responses, not preflight)
        response = client.get("/test", headers={"Origin": "http://localhost:3000"})
        exposed_headers = response.headers.get("access-control-expose-headers", "")
        # FastAPI/Starlette may lowercase header names
        assert "x-request-id" in exposed_headers.lower() or "X-Request-ID" in exposed_headers


class TestStagingPreset:
    """Test staging CORS preset."""

    def test_staging_generates_container_app_origins(self, app):
        """Test staging preset generates Azure Container Apps origins."""
        middleware = CORSPreset.staging(container_apps=["test-app"], region="eastus2")
        app.add_middleware(middleware)
        client = TestClient(app)

        @app.get("/test")
        def test_endpoint():
            return {"status": "ok"}

        # Test localhost origin (allowed in staging)
        response = client.get("/test", headers={"Origin": "https://localhost:3000"})
        assert response.status_code == 200

    def test_staging_allows_additional_origins(self, app):
        """Test staging preset accepts additional origins."""
        middleware = CORSPreset.staging(
            container_apps=["test-app"],
            additional_origins=["https://staging.example.com"],
        )
        app.add_middleware(middleware)
        client = TestClient(app)

        @app.get("/test")
        def test_endpoint():
            return {"status": "ok"}

        response = client.get("/test", headers={"Origin": "https://staging.example.com"})
        assert response.status_code == 200


class TestProductionPreset:
    """Test production CORS preset."""

    def test_production_allows_explicit_origins(self, app, test_origins):
        """Test production preset only allows specified origins."""
        middleware = CORSPreset.production(origins=test_origins)
        app.add_middleware(middleware)
        client = TestClient(app)

        @app.get("/test")
        def test_endpoint():
            return {"status": "ok"}

        response = client.get("/test", headers={"Origin": "https://app.example.com"})
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == "https://app.example.com"

    def test_production_blocks_localhost(self, app, test_origins):
        """Test production preset blocks localhost origins."""
        middleware = CORSPreset.production(origins=test_origins)
        app.add_middleware(middleware)
        client = TestClient(app)

        @app.get("/test")
        def test_endpoint():
            return {"status": "ok"}

        response = client.get("/test", headers={"Origin": "http://localhost:3000"})
        assert "access-control-allow-origin" not in response.headers

    def test_production_blocks_unauthorized_origin(self, app, test_origins):
        """Test production preset blocks non-whitelisted origins."""
        middleware = CORSPreset.production(origins=test_origins)
        app.add_middleware(middleware)
        client = TestClient(app)

        @app.get("/test")
        def test_endpoint():
            return {"status": "ok"}

        response = client.get("/test", headers={"Origin": "https://evil.com"})
        assert "access-control-allow-origin" not in response.headers


class TestOAuthPreset:
    """Test OAuth CORS preset."""

    def test_oauth_includes_app_origins(self, app, test_origins, oauth_platforms):
        """Test OAuth preset includes application origins."""
        middleware = CORSPreset.oauth(app_origins=test_origins, platforms=oauth_platforms)
        app.add_middleware(middleware)
        client = TestClient(app)

        @app.get("/test")
        def test_endpoint():
            return {"status": "ok"}

        response = client.get("/test", headers={"Origin": "https://app.example.com"})
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == "https://app.example.com"

    def test_oauth_includes_google_platform(self, app, test_origins):
        """Test OAuth preset includes Google OAuth domain."""
        middleware = CORSPreset.oauth(app_origins=test_origins, platforms=["google"])
        app.add_middleware(middleware)
        client = TestClient(app)

        @app.get("/test")
        def test_endpoint():
            return {"status": "ok"}

        response = client.get("/test", headers={"Origin": "https://accounts.google.com"})
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == "https://accounts.google.com"

    def test_oauth_includes_twitter_platform(self, app, test_origins):
        """Test OAuth preset includes Twitter OAuth domain."""
        middleware = CORSPreset.oauth(app_origins=test_origins, platforms=["twitter"])
        app.add_middleware(middleware)
        client = TestClient(app)

        @app.get("/test")
        def test_endpoint():
            return {"status": "ok"}

        response = client.get("/test", headers={"Origin": "https://twitter.com"})
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == "https://twitter.com"

    def test_oauth_includes_linkedin_platform(self, app, test_origins):
        """Test OAuth preset includes LinkedIn OAuth domain."""
        middleware = CORSPreset.oauth(app_origins=test_origins, platforms=["linkedin"])
        app.add_middleware(middleware)
        client = TestClient(app)

        @app.get("/test")
        def test_endpoint():
            return {"status": "ok"}

        response = client.get("/test", headers={"Origin": "https://www.linkedin.com"})
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == "https://www.linkedin.com"

    def test_oauth_includes_facebook_platform(self, app, test_origins):
        """Test OAuth preset includes Facebook OAuth domain."""
        middleware = CORSPreset.oauth(app_origins=test_origins, platforms=["facebook"])
        app.add_middleware(middleware)
        client = TestClient(app)

        @app.get("/test")
        def test_endpoint():
            return {"status": "ok"}

        response = client.get("/test", headers={"Origin": "https://www.facebook.com"})
        assert response.status_code == 200

    def test_oauth_rejects_invalid_platform(self, test_origins):
        """Test OAuth preset raises ValueError for invalid platform."""
        with pytest.raises(ValueError, match="Invalid OAuth platform"):
            CORSPreset.oauth(app_origins=test_origins, platforms=["invalid_platform"])

    def test_oauth_supports_all_platforms(self, app, test_origins):
        """Test OAuth preset supports all 8 social platforms."""
        all_platforms = ["google", "twitter", "linkedin", "facebook", "tiktok", "instagram", "pinterest", "threads"]
        middleware = CORSPreset.oauth(app_origins=test_origins, platforms=all_platforms)
        app.add_middleware(middleware)
        client = TestClient(app)

        @app.get("/test")
        def test_endpoint():
            return {"status": "ok"}

        # Test a few representative platforms
        test_cases = [
            "https://accounts.google.com",
            "https://www.tiktok.com",
            "https://www.threads.net",
        ]

        for origin in test_cases:
            response = client.get("/test", headers={"Origin": origin})
            assert response.status_code == 200
            assert response.headers.get("access-control-allow-origin") == origin


class TestCustomPreset:
    """Test custom CORS preset."""

    def test_custom_allows_configuration(self, app, test_origins):
        """Test custom preset accepts custom configuration."""
        middleware = CORSPreset.custom(
            allow_origins=test_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST"],
            max_age=1200,
        )
        app.add_middleware(middleware)
        client = TestClient(app)

        @app.get("/test")
        def test_endpoint():
            return {"status": "ok"}

        response = client.get("/test", headers={"Origin": "https://app.example.com"})
        assert response.status_code == 200

    def test_custom_validates_owasp_compliance(self, app):
        """Test custom preset validates OWASP compliance (no wildcard + credentials)."""
        from netrun_cors.middleware import CORSMiddleware
        # Test the middleware directly (validation happens in __init__)
        with pytest.raises(ValueError, match="OWASP Violation"):
            CORSMiddleware(
                app=app,
                allow_origins=["*"],
                allow_credentials=True
            )

    def test_custom_allows_wildcard_without_credentials(self, app):
        """Test custom preset allows wildcard when credentials disabled."""
        middleware = CORSPreset.custom(allow_origins=["*"], allow_credentials=False)
        app.add_middleware(middleware)
        client = TestClient(app)

        @app.get("/test")
        def test_endpoint():
            return {"status": "ok"}

        response = client.get("/test", headers={"Origin": "https://any-origin.com"})
        assert response.status_code == 200


class TestPreflightRequests:
    """Test CORS preflight (OPTIONS) requests."""

    def test_production_preflight_success(self, app, test_origins):
        """Test production preset handles preflight requests."""
        middleware = CORSPreset.production(origins=test_origins)
        app.add_middleware(middleware)
        client = TestClient(app)

        @app.post("/api/test")
        def test_endpoint():
            return {"status": "ok"}

        response = client.options(
            "/api/test",
            headers={
                "Origin": "https://app.example.com",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Authorization",
            },
        )
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == "https://app.example.com"
        assert "POST" in response.headers.get("access-control-allow-methods", "")

    def test_development_preflight_all_methods(self, app):
        """Test development preset allows all methods in preflight."""
        middleware = CORSPreset.development()
        app.add_middleware(middleware)
        client = TestClient(app)

        @app.post("/api/test")
        def test_endpoint():
            return {"status": "ok"}

        response = client.options(
            "/api/test",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "DELETE",
            },
        )
        assert response.status_code == 200
        allowed_methods = response.headers.get("access-control-allow-methods", "")
        # Development preset allows all methods
        assert "DELETE" in allowed_methods or "*" in allowed_methods
