#!/usr/bin/env python
"""Diagnostisches Script für Tunnel-Probleme."""

import sys
import time
from urllib import request as url_request
from urllib import error as url_error

def check_local_url(url: str, timeout: float = 2.0) -> tuple[bool, str]:
    """Überprüft, ob die lokale URL erreichbar ist."""
    for method in ("HEAD", "GET"):
        req = url_request.Request(url, method=method)
        try:
            with url_request.urlopen(req, timeout=timeout) as resp:
                status = getattr(resp, "status", 200)
                if 200 <= status < 500:
                    return True, f"✓ {method}: Status {status}"
        except url_error.HTTPError as exc:
            if 200 <= exc.code < 500:
                return True, f"✓ {method}: HTTPError {exc.code} (aber gültig)"
            return False, f"✗ {method}: HTTPError {exc.code}"
        except url_error.URLError as exc:
            return False, f"✗ {method}: URLError - {exc.reason}"
        except Exception as exc:
            return False, f"✗ {method}: {type(exc).__name__} - {exc}"
    return False, "✗ Keine erfolgreiche Verbindung"

if __name__ == "__main__":
    print("=" * 70)
    print("TUNNEL DIAGNOSTICS")
    print("=" * 70)

    # 1. Check local Streamlit
    print("\n1. Checking local Streamlit (http://localhost:8501)...")
    is_local_ok, local_msg = check_local_url("http://localhost:8501", timeout=2.0)
    print(f"   {local_msg}")

    if not is_local_ok:
        print("\n   ⚠️  LOCAL URL NOT REACHABLE!")
        print("   Make sure Streamlit is running on port 8501")
        print("   Run: streamlit run streamlit_app.py")
        sys.exit(1)

    # 2. Check if tunnel is configured
    print("\n2. Checking tunnel configuration...")
    try:
        from src.config.settings import load_settings
        settings = load_settings()
        print(f"   ENABLE_PUBLIC_SHARE: {settings.public_share.enabled}")
        print(f"   provider: {settings.public_share.provider}")
        print(f"   local_url: {settings.public_share.local_url}")
        print(f"   cloudflared_bin: {settings.public_share.cloudflared_bin}")
        print(f"   startup_timeout: {settings.public_share.startup_timeout_seconds}s")
        print(f"   healthcheck_timeout: {settings.public_share.healthcheck_timeout_seconds}s")
    except Exception as exc:
        print(f"   ✗ Error loading settings: {exc}")
        sys.exit(1)

    # 3. Check cloudflared binary
    print("\n3. Checking cloudflared binary...")
    from src.services.public_share_service import CloudflareQuickTunnelProvider
    provider = CloudflareQuickTunnelProvider(
        cloudflared_bin=settings.public_share.cloudflared_bin,
        startup_timeout_seconds=settings.public_share.startup_timeout_seconds,
        healthcheck_timeout_seconds=settings.public_share.healthcheck_timeout_seconds,
    )
    resolved_bin = provider._resolve_bin()
    if resolved_bin:
        print(f"   ✓ Found: {resolved_bin}")
    else:
        print(f"   ✗ NOT FOUND")
        print(f"   Tried: {settings.public_share.cloudflared_bin}")
        sys.exit(1)

    # 4. Test tunnel startup (but don't keep it running)
    print("\n4. Testing tunnel startup (10 second test)...")
    print("   Starting tunnel...")
    session = provider.start(settings.public_share.local_url)
    print(f"   Status: {session.status.value}")
    print(f"   Public URL: {session.public_url}")
    if session.error_message:
        print(f"   Error: {session.error_message}")
    if session.raw_log_tail:
        print(f"   Last log lines:")
        for line in session.raw_log_tail[-5:]:
            print(f"     {line}")

    if session.public_url:
        print(f"\n   ✓ Tunnel started successfully!")
        print(f"   Public URL: {session.public_url}")

        # Test reachability after small delay
        time.sleep(2)
        print("\n5. Checking if public URL is reachable...")
        is_public_ok, public_msg = check_local_url(session.public_url, timeout=5.0)
        print(f"   {public_msg}")

        if not is_public_ok:
            print(f"\n   ⚠️  PUBLIC URL NOT REACHABLE!")
            print(f"   URL: {session.public_url}")
            print("\n   Possible causes:")
            print("   - Cloudflare routing timeout")
            print("   - Local URL not accessible to tunneling service")
            print("   - Network/firewall issues")
            print("   - Try increasing healthcheck_timeout_seconds")
        else:
            print(f"\n   ✓ Public URL is reachable!")
    else:
        print(f"\n   ✗ Tunnel failed to start")
        print(f"   Error: {session.error_message}")

    # Clean up
    if session.process:
        provider.stop(session)
        print("\n6. Tunnel stopped.")

    print("\n" + "=" * 70)

