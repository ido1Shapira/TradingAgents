"""Chat router with auto-generated tool discovery and proxy endpoint."""

from __future__ import annotations

import json
import os
import re
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

router = APIRouter(prefix="/api/chat", tags=["chat"])

TOOL_GUIDANCE: dict[str, dict[str, str]] = {
    "runs_post": {
        "what": "Start a new deep analysis run for a ticker symbol. This runs the full trading agent analysis pipeline.",
        "when": "Use this when user asks to analyze a stock, get recommendations, or investigate a ticker. This is the PRIMARY tool for stock analysis.",
        "output": "Returns {run_id}. The analysis runs asynchronously - poll get_runs_run_id or get_runs_run_id_health to check progress.",
        "next": "After starting, use get_runs_run_id_health to check if analysis is complete. Do NOT call this repeatedly for the same ticker.",
    },
    "tickers_ticker_runs_get": {
        "what": "List all previous analysis runs for a specific ticker.",
        "when": "Use to see historical analysis results or check if analysis already exists for a ticker.",
        "output": "Returns array of {run_id, status, created_at} objects. Use get_runs_run_id to get full results.",
        "next": "If analysis exists, use get_runs_run_id to retrieve results.",
    },
    "tickers_ticker_history_get": {
        "what": "Get historical price data and charts for a ticker.",
        "when": "Use when user wants to see price trends, charts, or historical performance. Good for 'what's the trend?' or 'how has it performed?' questions.",
        "output": "Returns {bars: [...], range: '1mo', ticker: 'SPY'}. Bars contain {date, open, high, low, close, volume}.",
        "next": "Summarize the trend for the user. Look for higher highs, higher lows, volume patterns.",
    },
    "runs_run_id_get": {
        "what": "Get the full results of a completed analysis run.",
        "when": "Use after analysis completes to retrieve the trading recommendation, sentiment, and reasoning.",
        "output": "Returns {run_id, status, final_decision, sentiment, confidence, key_themes: [...], events: [...]}.",
        "next": "Present the recommendation to user: BUY/SELL/HOLD with confidence level and key reasons.",
    },
    "runs_run_id_health_get": {
        "what": "Check if an analysis run is still running or has completed.",
        "when": "Use after post_runs to poll for completion. Wait a few seconds between checks.",
        "output": "Returns {status: 'running'|'completed'|'failed', progress: 0-100}. When status='completed', use get_runs_run_id.",
        "next": "If status='completed', call get_runs_run_id. If 'running', wait and check again.",
    },
    "runs_run_id_cancel_post": {
        "what": "Cancel a running analysis.",
        "when": "Use if analysis is taking too long or user wants to stop.",
        "output": "Returns {cancelled: true}.",
        "next": "Inform user the analysis was cancelled.",
    },
    "watchlist_get": {
        "what": "Get the user's watchlist - all tickers being tracked.",
        "when": "Use at start of conversation or when user asks 'what am I tracking?' or 'show my watchlist'.",
        "output": "Returns array of {ticker, company_name, exchange, group}.",
        "next": "Present as a list. User can ask about any ticker on the watchlist.",
    },
    "prices_get": {
        "what": "Get current prices for all tickers on the watchlist.",
        "when": "Use when user asks for current prices, 'how are my stocks doing?' or 'show prices'.",
        "output": "Returns {snapshot: {ticker: {price, change, change_percent, volume}}}. May be empty if no data.",
        "next": "Display as price list with change percentages. Green = up, Red = down.",
    },
    "indicators_get": {
        "what": "List all configured price alerts and indicators.",
        "when": "Use to show user their active alerts or check existing conditions.",
        "output": "Returns {indicators: [{id, kind, ticker, threshold, comparator, enabled}]}.",
        "next": "Show active alerts. User can ask to add/remove alerts.",
    },
    "indicators_post": {
        "what": "Create a new price alert for a ticker.",
        "when": "Use when user says 'alert me when MSFT hits $500' or 'set a price alert'.",
        "output": "Returns {id, kind: 'ticker_price', ticker, threshold, comparator}. Alert triggers once then deactivates.",
        "next": "Confirm the alert was created. User will be notified when triggered.",
    },
    "indicators_indicator_id_delete": {
        "what": "Delete/remove a price alert by its ID.",
        "when": "Use when user wants to remove an alert.",
        "output": "Returns 204 No Content on success.",
        "next": "Confirm the alert was removed.",
    },
    "indicators_indicator_id_patch": {
        "what": "Update alert parameters (threshold, comparator, enabled).",
        "when": "Use when user wants to modify an existing alert.",
        "output": "Returns updated indicator object.",
        "next": "Confirm the changes.",
    },
    "indicators_check_post": {
        "what": "Manually trigger a check of all price alerts against current prices.",
        "when": "Use when user wants to manually check if any alerts have been triggered.",
        "output": "Returns {triggered: [...], checked: [...]} showing which alerts fired.",
        "next": "Report any triggered alerts to the user.",
    },
    "watchlist_post": {
        "what": "Add a ticker to the watchlist.",
        "when": "Use when user says 'track MSFT' or 'add to watchlist'.",
        "output": "Returns {ticker, company_name, exchange}. Fails if already exists.",
        "next": "Confirm added. Then user can ask to analyze it.",
    },
    "watchlist_ticker_delete": {
        "what": "Remove a ticker from the watchlist.",
        "when": "Use when user says 'stop tracking MSFT' or 'remove from watchlist'.",
        "output": "Returns 204 No Content.",
        "next": "Confirm removed.",
    },
    "watchlist_ticker_patch": {
        "what": "Update a watchlist item (change group/category).",
        "when": "Use when user wants to reorganize their watchlist.",
        "output": "Returns updated watchlist item.",
        "next": "Confirm changes.",
    },
    "background_runs_get": {
        "what": "List all background analysis jobs.",
        "when": "Use to check status of long-running analyses.",
        "output": "Returns array of {job_id, ticker, status, created_at}.",
        "next": "Show job statuses.",
    },
    "background_runs_job_id_delete": {
        "what": "Cancel and remove a background job.",
        "when": "Use to clean up a background job.",
        "output": "Returns 204 No Content.",
        "next": "Confirm cancelled.",
    },
    "tickers_ticker_download_get": {
        "what": "Download historical data for a ticker as CSV/JSON.",
        "when": "Use when user wants to export data for a ticker.",
        "output": "Returns downloadable file with historical price data.",
        "next": "File is downloaded automatically.",
    },
}


def _get_tool_description(tool_name: str, method: str, path_params: list[str], route_description: str) -> str:
    key = f"{tool_name}_{method.lower()}"
    if key in TOOL_GUIDANCE:
        guidance = TOOL_GUIDANCE[key]
        return f"{guidance['what']}\n\nWHEN TO USE: {guidance['when']}\n\nOUTPUT: {guidance['output']}\n\nNEXT STEP: {guidance['next']}"
    if path_params:
        return f"{route_description}\n\nParameters: {', '.join(path_params)}"
    return route_description


class ProxyRequest(BaseModel):
    method: str
    path: str
    params: dict[str, Any] | None = None
    body: dict[str, Any] | None = None


class ChatCompletionRequest(BaseModel):
    messages: list[dict[str, Any]]
    tools: list[dict[str, Any]] | None = None
    stream: bool = False


def extract_tool_definitions(app) -> list[dict[str, Any]]:
    """Extract tool definitions from FastAPI routes."""
    tools: list[dict[str, Any]] = []
    for route in app.routes:
        if not (hasattr(route, "methods") and hasattr(route, "path")):
            continue
        # Skip chat routes and websocket routes
        if route.path.startswith("/api/chat") or route.path.startswith("/ws"):
            continue

        for method in route.methods:
            if method not in ("GET", "POST", "PUT", "PATCH", "DELETE"):
                continue

            # Replace {param} with just param (removing braces) before building tool name
            path_for_name = re.sub(r"\{(\w+)\}", r"\1", route.path.replace("/api/", ""))
            tool_name = path_for_name.replace("/", "_").strip("_")
            # Replace any remaining non-alphanumeric chars (but keep underscores)
            tool_name = re.sub(r"[^a-zA-Z0-9_]", "_", tool_name)
            # Clean up any double underscores
            tool_name = re.sub(r"__+", "_", tool_name).strip("_")
            # Ensure it starts with a letter
            if tool_name and not tool_name[0].isalpha():
                tool_name = "action_" + tool_name
            if not tool_name:
                tool_name = "root"

            # Extract path parameters first
            path_params = re.findall(r"\{(\w+)\}", route.path)

            # Get description from route or generate one
            description = ""
            if hasattr(route, "endpoint") and route.endpoint.__doc__:
                route_desc = route.endpoint.__doc__.strip().split("\n")[0]
            elif path_params:
                sig_parts = []
                for p in path_params:
                    sig_parts.append(f"{p}: string")
                sig = f"{method.lower()}_{tool_name}({', '.join(sig_parts)})"
                main_param = path_params[0]
                route_desc = f"{sig} - Fetch data for {main_param}. Examples: {main_param.upper()}=\"SPY\", \"AAPL\", \"QQQ\""
            else:
                route_desc = f"Execute {method} on {route.path}"

            description = _get_tool_description(tool_name, method, path_params, route_desc)

            # Extract parameters from path and known query params
            parameters: dict[str, dict[str, Any]] = {}
            required: list[str] = []

            for param in path_params:
                param_desc = "REQUIRED. The ticker symbol (e.g. 'SPY', 'AAPL', 'MSFT'). Extract from conversation context."
                if param == "indicator_id":
                    param_desc = "REQUIRED. The unique ID of the indicator/alert. Get this from get_indicators response."
                elif param == "run_id":
                    param_desc = "REQUIRED. The run identifier returned from post_runs or get_tickers_ticker_runs."
                elif param == "job_id":
                    param_desc = "REQUIRED. The background job ID to manage."
                parameters[param] = {
                    "type": "string",
                    "description": param_desc,
                }
                required.append(param)

            # Add known query parameters for commonly used endpoints
            if tool_name == "prices":
                parameters["ticker"] = {
                    "type": "string",
                    "description": "Optional ticker to get specific price. If omitted, returns all tracked tickers.",
                }
            if tool_name == "tickers_ticker_history":
                parameters["range"] = {
                    "type": "string",
                    "description": "Time range: '1d', '5d', '1mo', '3mo', '6mo', '1y'. Default: 'auto'. '1mo' = 1 month of data.",
                }
            if tool_name == "indicators" and method == "POST":
                parameters["kind"] = {
                    "type": "string",
                    "enum": ["ticker_price"],
                    "description": "Alert type. Always use 'ticker_price' for price alerts.",
                }
                parameters["ticker"] = {
                    "type": "string",
                    "description": "REQUIRED. The ticker symbol to alert on (e.g. 'SPY', 'AAPL', 'MSFT').",
                }
                parameters["threshold"] = {
                    "type": "number",
                    "description": "REQUIRED. Price level to trigger alert (e.g. 500.00 for $500).",
                }
                parameters["comparator"] = {
                    "type": "string",
                    "enum": ["above", "below", "at_least", "within"],
                    "description": "REQUIRED. 'above'=price>threshold, 'below'=price<threshold, 'at_least'=price>=threshold, 'within'=within X% of threshold.",
                }
                parameters["name"] = {
                    "type": "string",
                    "description": "Optional friendly name for this alert (e.g. 'MSFT earnings support').",
                }
                parameters["enabled"] = {
                    "type": "boolean",
                    "description": "Optional. Set to false to disable without deleting. Default: true.",
                }
            if tool_name == "runs" and method == "POST":
                parameters["ticker"] = {
                    "type": "string",
                    "description": "REQUIRED. Ticker to analyze. Must already be on the watchlist.",
                }
                parameters["force"] = {
                    "type": "boolean",
                    "description": "Optional. Force new analysis even if one is running. Use sparingly - wastes resources.",
                }
                required.append("ticker")
            if tool_name == "indicators" and method == "POST":
                required.extend(["ticker", "threshold", "comparator"])
            if tool_name == "watchlist" and method == "POST":
                required.append("ticker")
            if tool_name == "watchlist" and method == "PATCH":
                parameters["group"] = {
                    "type": "string",
                    "description": "Optional group/category name to organize tickers (e.g. 'tech', 'earnings', 'long-term').",
                }

            tools.append(
                {
                    "name": f"{method.lower()}_{tool_name}",
                    "description": description,
                    "method": method,
                    "path": route.path,
                    "parameters": parameters,
                    "required": required,
                }
            )
    return tools


@router.get("/tools")
async def get_tools(request: Request):
    """Get available tool definitions auto-generated from API routes."""
    app = request.app
    tools = extract_tool_definitions(app)
    return {"tools": tools}


@router.api_route(
    "/proxy", methods=["GET", "POST", "PUT", "PATCH", "DELETE"]
)
async def proxy_request(proxy_req: ProxyRequest, request: Request):
    """Forward requests to any backend endpoint."""
    print(f"[proxy] INCOMING REQUEST: {proxy_req.method} {proxy_req.path}")
    print(f"[proxy]   params: {proxy_req.params}")
    print(f"[proxy]   body: {proxy_req.body}")

    base_url = str(request.base_url).rstrip("/")

    # Substitute path parameters (e.g. {ticker}) with actual values from params
    import re as _re_path
    path = proxy_req.path
    params = dict(proxy_req.params or {})

    print(f"[proxy] Original path: {path}")
    print(f"[proxy] Params before substitution: {params}")

    def _sub_path_param(m: _re_path.Match) -> str:
        param_name = m.group(1)
        value = params.pop(param_name, None)
        print(f"[proxy]   Substituting path param {{{param_name}}} -> {value}")
        if value is not None:
            return str(value)
        raise HTTPException(
            status_code=400,
            detail=f"Missing required path parameter '{param_name}' in the request.",
        )

    resolved_path = _re_path.sub(r'\{(\w+)\}', _sub_path_param, path)
    print(f"[proxy] Resolved path: {resolved_path}")
    print(f"[proxy] Remaining params: {params}")

    target_url = f"{base_url}{resolved_path}"
    print(f"[proxy] Target URL: {target_url}")

    async with httpx.AsyncClient() as client:
        response = await client.request(
            method=proxy_req.method.upper(),
            url=target_url,
            params=params,
            json=proxy_req.body
            if proxy_req.method.upper() in ("POST", "PUT", "PATCH")
            else None,
            headers={"Cookie": request.headers.get("cookie", "")},
        )

    print(f"[proxy] Response status: {response.status_code}")

    content = (
        response.json()
        if response.headers.get("content-type", "").startswith("application/json")
        else response.text
    )
    return JSONResponse(content=content, status_code=response.status_code)


@router.post("/completions")
async def chat_completions(req: ChatCompletionRequest, request: Request):
    """Handle chat completions using the backend's LLM configuration."""
    if req.stream:
        return StreamingResponse(
            _stream_chat(req, request),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    try:
        return await _non_stream_chat(req, request)
    except Exception as e:
        return JSONResponse(
            content={"error": str(e)},
            status_code=500,
        )


async def _stream_chat(req: ChatCompletionRequest, request: Request):
    """Generator for SSE streaming chat completions."""
    import re as _re
    import uuid as _uuid

    try:
        from pathlib import Path

        from tradingagents.llm_clients import create_llm_client

        # Read .env
        env = {}
        env_path = Path(__file__).resolve().parent.parent.parent / ".env"
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                if "=" in stripped:
                    key, _, val = stripped.partition("=")
                    env[key.strip()] = val.strip()

        provider = env.get("TRADINGAGENTS_LLM_PROVIDER", "ollama").replace("-", "_")
        model_name = env.get("TRADINGAGENTS_QUICK_THINK_LLM", "gpt-4o-mini")
        backend_url = env.get("TRADINGAGENTS_LLM_BACKEND_URL") or None

        for k, v in env.items():
            if v and k not in os.environ:
                os.environ[k] = v

        base_url = backend_url
        if provider == "ollama":
            base_url = None

        client = create_llm_client(provider=provider, model=model_name, base_url=base_url)
        llm = client.get_llm()


        langchain_messages = _build_langchain_messages(req)

        # Try streaming with tools; fall back to non-streaming on failure
        use_tools = bool(req.tools)
        lc_tools = []
        if use_tools:
            from langchain_core.tools import StructuredTool
            from pydantic import create_model

            for tool in req.tools:
                func_info = tool.get("function", {})
                tool_name = func_info.get("name", "unnamed_tool")
                tool_desc = func_info.get("description", "")
                params_obj = func_info.get("parameters", {})

                # Create dynamic args_schema from OpenAI-style parameters
                schema_fields = {}
                required_params = params_obj.get("required", [])
                properties = params_obj.get("properties", {})

                for param_name, param_spec in properties.items():
                    is_required = param_name in required_params
                    param_type = param_spec.get("type", "string")
                    # Map to Python types
                    if param_type == "string":
                        py_type = str
                    elif param_type in ("integer", "number"):
                        py_type = float
                    elif param_type == "boolean":
                        py_type = bool
                    else:
                        py_type = str
                    # Default to ... (ellipsis) for required, None for optional
                    default = ... if is_required else None
                    schema_fields[param_name] = (py_type, default)

                if schema_fields:
                    # Create dynamic Pydantic model
                    model_name = f"{tool_name}Args"
                    args_schema = create_model(model_name, **schema_fields)
                    # Enhance description with explicit required params list and JSON example
                    required_str = ", ".join(required_params) if required_params else "none"
                    example_args = {k: k.upper() if k == "ticker" else "value" for k in required_params}
                    tool_desc = f"{tool_desc}\n\nREQUIRED PARAMETERS: {required_str}\nJSON EXAMPLE: {json.dumps(example_args)}"
                else:
                    args_schema = None

                lc_tools.append(StructuredTool(
                    name=tool_name,
                    description=tool_desc,
                    args_schema=args_schema,
                    func=None,
                ))

        # Attempt streaming
        stream_iter = None
        try:
            if use_tools:
                llm_with_tools = llm.bind_tools(lc_tools)
                stream_iter = llm_with_tools.stream(langchain_messages)
            else:
                stream_iter = llm.stream(langchain_messages)
        except Exception:
            # Streaming not supported - fall back to non-streaming with simulated chunks
            stream_iter = None

        if stream_iter is not None:
            full_text = ""
            tool_calls_buffer: list[dict] = []

            try:
                for chunk in stream_iter:
                    chunk_content = chunk.content if hasattr(chunk, "content") else ""
                    chunk_tool_calls = getattr(chunk, "tool_calls", None) or []

                    if chunk_content:
                        full_text += chunk_content
                        yield f"data: {json.dumps({'type': 'text', 'text': chunk_content})}\n\n"

                    if chunk_tool_calls:
                        for tc in chunk_tool_calls:
                            tc_id = tc.get("id", f"call_{_uuid.uuid4().hex[:12]}")
                            tc_func = tc.get("function", tc)
                            tc_name = tc_func.get("name", "")
                            tc_args = tc_func.get("arguments", "")

                            existing = next((t for t in tool_calls_buffer if t["id"] == tc_id), None)
                            if existing:
                                existing["function"]["arguments"] += tc_args
                            else:
                                tool_calls_buffer.append({
                                    "id": tc_id,
                                    "type": "function",
                                    "function": {"name": tc_name, "arguments": tc_args},
                                })
                        yield f"data: {json.dumps({'type': 'tool_calls', 'tool_calls': tool_calls_buffer})}\n\n"
            except Exception as stream_err:
                yield f"data: {json.dumps({'type': 'error', 'error': str(stream_err)})}\n\n"

            # Parse text-based tool calls
            if not tool_calls_buffer and full_text:
                tool_pattern = _re.compile(
                    r'<tool_call>\s*<name>(.*?)</name>\s*<parameters>(.*?)</parameters>\s*</tool_call>',
                    _re.DOTALL,
                )
                matches = tool_pattern.findall(full_text)
                if matches:
                    full_text = tool_pattern.sub("", full_text).strip()
                    for name, params_str in matches:
                        try:
                            params = json.loads(params_str)
                        except json.JSONDecodeError:
                            params = {}
                        tool_calls_buffer.append({
                            "id": f"call_{_uuid.uuid4().hex[:12]}",
                            "type": "function",
                            "function": {"name": name, "arguments": json.dumps(params)},
                        })

            finish_reason = "tool_calls" if tool_calls_buffer else "stop"
            yield f"data: {json.dumps({'type': 'done', 'finish_reason': finish_reason, 'tool_calls': tool_calls_buffer, 'content': full_text})}\n\n"
        else:
            # Non-streaming fallback
            if use_tools:
                llm_with_tools = llm.bind_tools(lc_tools)
                response = llm_with_tools.invoke(langchain_messages)
            else:
                response = llm.invoke(langchain_messages)

            text = response.content if hasattr(response, "content") else str(response)
            tool_calls_from_llm = getattr(response, "tool_calls", None) or []

            if text:
                yield f"data: {json.dumps({'type': 'text', 'text': text})}\n\n"

            if tool_calls_from_llm:
                yield f"data: {json.dumps({'type': 'tool_calls', 'tool_calls': tool_calls_from_llm})}\n\n"

            finish_reason = "tool_calls" if tool_calls_from_llm else "stop"
            yield f"data: {json.dumps({'type': 'done', 'finish_reason': finish_reason, 'tool_calls': tool_calls_from_llm, 'content': text})}\n\n"

    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

    yield "data: [DONE]\n\n"


async def _non_stream_chat(req: ChatCompletionRequest, request: Request):
    """Non-streaming chat completion."""
    from pathlib import Path

    from tradingagents.llm_clients import create_llm_client

    env = {}
    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if "=" in stripped:
                key, _, val = stripped.partition("=")
                env[key.strip()] = val.strip()

    provider = env.get("TRADINGAGENTS_LLM_PROVIDER", "ollama").replace("-", "_")
    model_name = env.get("TRADINGAGENTS_QUICK_THINK_LLM", "gpt-4o-mini")
    backend_url = env.get("TRADINGAGENTS_LLM_BACKEND_URL") or None

    for k, v in env.items():
        if v and k not in os.environ:
            os.environ[k] = v

    base_url = backend_url
    if provider == "ollama":
        base_url = None

    client = create_llm_client(provider=provider, model=model_name, base_url=base_url)
    llm = client.get_llm()

    langchain_messages = _build_langchain_messages(req)

    if req.tools:
        from langchain_core.tools import StructuredTool
        lc_tools = []
        for tool in req.tools:
            func_info = tool.get("function", {})
            lc_tools.append(StructuredTool(
                name=func_info["name"],
                description=func_info.get("description", ""),
                args_schema=None,
                func=None,
            ))
        llm_with_tools = llm.bind_tools(lc_tools)
        response = llm_with_tools.invoke(langchain_messages)
    else:
        response = llm.invoke(langchain_messages)

    text = response.content if hasattr(response, "content") else str(response)
    tool_calls_from_llm = getattr(response, "tool_calls", None) or []

    # Fallback: parse text-based tool calls
    if not tool_calls_from_llm and text:
        import re as _re
        import uuid as _uuid
        tool_pattern = _re.compile(
            r'<tool_call>\s*<name>(.*?)</name>\s*<parameters>(.*?)</parameters>\s*</tool_call>',
            _re.DOTALL,
        )
        matches = tool_pattern.findall(text)
        if matches:
            clean_text = tool_pattern.sub("", text).strip()
            for name, params_str in matches:
                try:
                    params = json.loads(params_str)
                except json.JSONDecodeError:
                    params = {}
                tool_calls_from_llm.append({
                    "id": f"call_{_uuid.uuid4().hex[:12]}",
                    "type": "function",
                    "function": {"name": name, "arguments": json.dumps(params)},
                })
            if clean_text:
                text = clean_text

    if not tool_calls_from_llm and text:
        import re as _re
        import uuid as _uuid
        block_pattern = _re.compile(r'```tool_call\s*(.*?)\s*```', _re.DOTALL)
        block_matches = block_pattern.findall(text)
        if block_matches:
            for block in block_matches:
                try:
                    tc = json.loads(block)
                    tool_calls_from_llm.append({
                        "id": f"call_{_uuid.uuid4().hex[:12]}",
                        "type": "function",
                        "function": {
                            "name": tc.get("name", ""),
                            "arguments": json.dumps(tc.get("arguments", tc.get("parameters", {}))),
                        },
                    })
                except json.JSONDecodeError:
                    name_match = _re.search(r'name="([^"]*)"', block)
                    params_match = _re.search(r'parameters="({.*?})"', block, _re.DOTALL)
                    if name_match:
                        name = name_match.group(1)
                        params_str = params_match.group(1) if params_match else "{}"
                        try:
                            params = json.loads(params_str)
                        except json.JSONDecodeError:
                            params = {}
                        tool_calls_from_llm.append({
                            "id": f"call_{_uuid.uuid4().hex[:12]}",
                            "type": "function",
                            "function": {"name": name, "arguments": json.dumps(params)},
                        })
            text = block_pattern.sub("", text).strip()

    result_msg: dict[str, Any] = {"role": "assistant"}
    if tool_calls_from_llm:
        result_msg["content"] = text or None
        result_msg["tool_calls"] = tool_calls_from_llm
        finish_reason = "tool_calls"
    else:
        result_msg["content"] = text
        finish_reason = "stop"

    return {
        "id": "chatcmpl-backend",
        "object": "chat.completion",
        "choices": [{"index": 0, "message": result_msg, "finish_reason": finish_reason}],
        "model": model_name,
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }


def _build_langchain_messages(req: ChatCompletionRequest):
    """Convert OpenAI-format messages to LangChain format."""
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

    messages = []
    for msg in req.messages:
        role = msg.get("role", "")
        content = msg.get("content", "")

        if role == "system":
            messages.append(SystemMessage(content=content))
        elif role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "assistant":
            if msg.get("tool_calls"):
                tool_calls = []
                for tc in msg["tool_calls"]:
                    func = tc.get("function", {})
                    raw_args = func.get("arguments", "{}")
                    try:
                        parsed_args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                    except json.JSONDecodeError:
                        parsed_args = {}
                    tool_calls.append({
                        "name": func.get("name", ""),
                        "args": parsed_args,
                        "id": tc.get("id", ""),
                    })
                messages.append(AIMessage(content=content or "", tool_calls=tool_calls))
            else:
                messages.append(AIMessage(content=content))
        elif role == "tool":
            messages.append(ToolMessage(
                content=content,
                tool_call_id=msg.get("tool_call_id", ""),
            ))
    return messages
