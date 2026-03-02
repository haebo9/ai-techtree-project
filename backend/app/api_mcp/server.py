from app.api_mcp.tools import mcp

if __name__ == "__main__":
    import uvicorn
    import sys
    
    # print(f"✅ [MCP] Starting FastMCP (SSE Mode) using uvicorn on port 8200...", flush=True)
    
    # 'sse_app' is the Starlette/FastAPI application exposed by FastMCP
    # Forcefully allow all hosts to prevent 'Invalid Host header' errors (421)
    # We wrap the ASGI app directly since mcp.sse_app might be a function/callable
    from starlette.middleware.trustedhost import TrustedHostMiddleware
    
    # Wrap the app with middleware to allow all hosts
    # mcp.sse_app is a method that returns the ASGI app, so it must be called.
    # Wrap the app with middleware to allow all hosts
    # Wrap the app with middleware to allow all hosts
    # FOUND IT! The correct method is streamable_http_app()
    # This enables Stateless Streamable HTTP transport required by Kakao MCP Player.
    try:
        raw_app = mcp.streamable_http_app()
        # print("✅ [MCP] Using streamable_http_app (Stateless Mode)", flush=True)
    except AttributeError:
        # Fallback (should not happen based on inspection)
        raw_app = mcp.sse_app()
        # print("⚠️ [MCP] Fallback to sse_app", flush=True)

    app = TrustedHostMiddleware(raw_app, allowed_hosts=["*"])

    # We run it directly to ensure stability and control over the port
    # forwarded_allow_ips="*" is required when running behind a reverse proxy (Nginx)
    uvicorn.run(app, host="0.0.0.0", port=8200, forwarded_allow_ips="*", proxy_headers=True)




# run streamlit
# streamlit run frontend/main.py