"""
CORS preset configurations for common deployment scenarios.

Provides factory methods for development, staging, production, and OAuth environments.
"""

from typing import List, Optional
from netrun_cors.middleware import CORSMiddleware


class CORSPreset:
    """
    Factory class for standardized CORS middleware configurations.

    Provides 4 preset configurations:
    - development(): Local development (localhost:3000, 5173, permissive)
    - staging(): Azure Container Apps staging environments (wildcard support)
    - production(): Production deployments (explicit origin whitelist)
    - oauth(): OAuth-enabled applications (social platform callback domains)

    Example:
        >>> from netrun_cors import CORSPreset
        >>> app.add_middleware(CORSPreset.development())

        >>> app.add_middleware(
        ...     CORSPreset.production(origins=["https://app.example.com"])
        ... )

        >>> app.add_middleware(
        ...     CORSPreset.oauth(
        ...         app_origins=["https://app.example.com"],
        ...         platforms=["google", "twitter"]
        ...     )
        ... )
    """

    # OAuth platform domain mapping
    OAUTH_PLATFORM_DOMAINS = {
        "google": "https://accounts.google.com",
        "twitter": "https://twitter.com",
        "linkedin": "https://www.linkedin.com",
        "facebook": "https://www.facebook.com",
        "tiktok": "https://www.tiktok.com",
        "instagram": "https://www.instagram.com",
        "pinterest": "https://www.pinterest.com",
        "threads": "https://www.threads.net",
    }

    @staticmethod
    def development() -> type[CORSMiddleware]:
        """
        Development preset: Permissive CORS for local development.

        Configuration:
        - Origins: localhost:3000, localhost:5173, 127.0.0.1:3000 (HTTP)
        - Credentials: Enabled
        - Methods: All (*)
        - Headers: All (*)
        - Expose Headers: X-Request-ID, X-Process-Time
        - Max Age: 600s (10 minutes)

        Returns:
            CORSMiddleware configured for development

        Example:
            >>> app.add_middleware(CORSPreset.development())
        """
        return lambda app: CORSMiddleware(
            app=app,
            allow_origins=[
                "http://localhost:3000",
                "http://localhost:5173",
                "http://127.0.0.1:3000",
                "http://127.0.0.1:5173",
            ],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
            expose_headers=["X-Request-ID", "X-Process-Time"],
            max_age=600,
        )

    @staticmethod
    def staging(
        container_apps: List[str],
        region: str = "eastus2",
        additional_origins: Optional[List[str]] = None,
    ) -> type[CORSMiddleware]:
        """
        Staging preset: Azure Container Apps with wildcard support.

        Configuration:
        - Origins: https://localhost:3000, 5173 + Azure Container Apps wildcards
        - Credentials: Enabled
        - Methods: GET, POST, PUT, DELETE, OPTIONS, PATCH
        - Headers: Authorization, Content-Type, Accept, X-Requested-With, X-Request-ID
        - Expose Headers: X-Request-ID, X-Process-Time
        - Max Age: 1800s (30 minutes)

        Args:
            container_apps: List of Azure Container App names (e.g., ["intirkast-frontend"])
            region: Azure region (default: "eastus2")
            additional_origins: Optional additional origins to whitelist

        Returns:
            CORSMiddleware configured for staging

        Example:
            >>> app.add_middleware(
            ...     CORSPreset.staging(
            ...         container_apps=["intirkast-frontend"],
            ...         region="eastus2"
            ...     )
            ... )
        """
        # Base staging origins (HTTPS localhost for staging tests)
        origins = [
            "https://localhost:3000",
            "https://localhost:5173",
        ]

        # Add Azure Container Apps wildcard patterns
        for app_name in container_apps:
            # Pattern: https://<app-name>-*.eastus2.azurecontainerapps.io
            # Note: Actual wildcard support depends on Starlette implementation
            # For strict matching, enumerate known environment hashes
            origins.append(f"https://{app_name}.*.{region}.azurecontainerapps.io")

        # Add additional origins if provided
        if additional_origins:
            origins.extend(additional_origins)

        return lambda app: CORSMiddleware(
            app=app,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
            allow_headers=[
                "Authorization",
                "Content-Type",
                "Accept",
                "X-Requested-With",
                "X-Request-ID",
            ],
            expose_headers=["X-Request-ID", "X-Process-Time"],
            max_age=1800,
        )

    @staticmethod
    def production(origins: List[str]) -> type[CORSMiddleware]:
        """
        Production preset: Strict origin whitelisting.

        Configuration:
        - Origins: Explicit whitelist (user-provided)
        - Credentials: Enabled
        - Methods: GET, POST, PUT, DELETE, OPTIONS, PATCH
        - Headers: Authorization, Content-Type, Accept, X-Request-ID
        - Expose Headers: X-Request-ID
        - Max Age: 3600s (1 hour)

        Args:
            origins: List of allowed production origins (HTTPS only recommended)

        Returns:
            CORSMiddleware configured for production

        Example:
            >>> app.add_middleware(
            ...     CORSPreset.production(
            ...         origins=[
            ...             "https://app.intirkast.com",
            ...             "https://www.intirkast.com"
            ...         ]
            ...     )
            ... )
        """
        return lambda app: CORSMiddleware(
            app=app,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
            allow_headers=["Authorization", "Content-Type", "Accept", "X-Request-ID"],
            expose_headers=["X-Request-ID"],
            max_age=3600,
        )

    @staticmethod
    def oauth(
        app_origins: List[str],
        platforms: List[str],
    ) -> type[CORSMiddleware]:
        """
        OAuth preset: Application origins + social platform callback domains.

        Configuration:
        - Origins: App origins + OAuth platform domains
        - Credentials: Enabled
        - Methods: All (*)
        - Headers: All (*)
        - Expose Headers: All (*)
        - Max Age: 3600s (1 hour)

        Supported platforms:
        - google: https://accounts.google.com (YouTube/Google OAuth)
        - twitter: https://twitter.com (Twitter/X OAuth)
        - linkedin: https://www.linkedin.com (LinkedIn OAuth)
        - facebook: https://www.facebook.com (Facebook OAuth)
        - tiktok: https://www.tiktok.com (TikTok OAuth)
        - instagram: https://www.instagram.com (Instagram OAuth)
        - pinterest: https://www.pinterest.com (Pinterest OAuth)
        - threads: https://www.threads.net (Threads OAuth)

        Args:
            app_origins: List of application origins
            platforms: List of OAuth platform identifiers (e.g., ["google", "twitter"])

        Returns:
            CORSMiddleware configured for OAuth

        Raises:
            ValueError: If invalid platform identifier provided

        Example:
            >>> app.add_middleware(
            ...     CORSPreset.oauth(
            ...         app_origins=["https://app.intirkast.com"],
            ...         platforms=["google", "twitter", "linkedin"]
            ...     )
            ... )
        """
        # Validate platforms
        invalid_platforms = [p for p in platforms if p not in CORSPreset.OAUTH_PLATFORM_DOMAINS]
        if invalid_platforms:
            raise ValueError(
                f"Invalid OAuth platform(s): {invalid_platforms}. "
                f"Supported platforms: {list(CORSPreset.OAUTH_PLATFORM_DOMAINS.keys())}"
            )

        # Build origins list: app origins + OAuth platform domains
        origins = app_origins.copy()
        for platform in platforms:
            origins.append(CORSPreset.OAUTH_PLATFORM_DOMAINS[platform])

        return lambda app: CORSMiddleware(
            app=app,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
            expose_headers=["*"],
            max_age=3600,
        )

    @staticmethod
    def custom(
        allow_origins: List[str],
        allow_credentials: bool = True,
        allow_methods: Optional[List[str]] = None,
        allow_headers: Optional[List[str]] = None,
        expose_headers: Optional[List[str]] = None,
        max_age: int = 3600,
    ) -> type[CORSMiddleware]:
        """
        Custom preset: Full control over CORS configuration.

        Use this when presets don't match your requirements.
        Subject to OWASP compliance validation (no wildcard + credentials).

        Args:
            allow_origins: List of allowed origins
            allow_credentials: Allow credentials in CORS requests
            allow_methods: List of allowed HTTP methods (default: standard set)
            allow_headers: List of allowed headers (default: all)
            expose_headers: List of exposed headers (default: X-Request-ID, X-Process-Time)
            max_age: Preflight cache duration in seconds

        Returns:
            CORSMiddleware with custom configuration

        Raises:
            ValueError: If wildcard origins combined with credentials

        Example:
            >>> app.add_middleware(
            ...     CORSPreset.custom(
            ...         allow_origins=["https://app.example.com"],
            ...         allow_credentials=False,
            ...         allow_methods=["GET", "POST"]
            ...     )
            ... )
        """
        return lambda app: CORSMiddleware(
            app=app,
            allow_origins=allow_origins,
            allow_credentials=allow_credentials,
            allow_methods=allow_methods,
            allow_headers=allow_headers,
            expose_headers=expose_headers,
            max_age=max_age,
        )
