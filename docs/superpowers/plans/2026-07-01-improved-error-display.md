# Improved Error Display Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace unhelpful error messages (like "No response") with structured, user-friendly error components that provide context and actionable suggestions.

**Architecture:** Create a reusable `ErrorMessage` component, then integrate it into `AgentChatBubble`, `IndicatorRailView`, and `ErrorBoundary` to replace raw error strings.

**Tech Stack:** React, TypeScript, Tailwind CSS, lucide-react icons

## Global Constraints

- Follow existing code conventions in `web/frontend/src/components/`
- Use Tailwind classes matching existing UI theme (slate, red, sky colors)
- Use lucide-react for icons (already imported in relevant files)
- No new dependencies required

---

## File Structure

| File | Purpose |
|------|---------|
| `src/components/ErrorMessage.tsx` | **New** - Reusable error display component |
| `src/components/AgentChatBubble.tsx` | **Modify** - Replace error string formatting |
| `src/components/IndicatorRailView.tsx` | **Modify** - Replace error string formatting |
| `src/components/ErrorBoundary.tsx` | **Modify** - Use ErrorMessage in fallback |

---

### Task 1: Create ErrorMessage Component

**Files:**
- Create: `web/frontend/src/components/ErrorMessage.tsx`

**Interfaces:**
- Produces: `<ErrorMessage type, message, details?, suggestion? />` component

- [ ] **Step 1: Create the ErrorMessage component**

```tsx
import { useState } from "react";
import { AlertCircle, ChevronDown, ChevronRight, Wifi, Bot, Warnings, Stream, HelpCircle } from "lucide-react";

type ErrorType = "network" | "llm" | "tool" | "stream" | "unknown";

interface ErrorMessageProps {
  type: ErrorType;
  message: string;
  details?: string;
  suggestion?: string;
}

const TYPE_CONFIG: Record<ErrorType, { icon: typeof AlertCircle; label: string; iconClass: string }> = {
  network: { icon: Wifi, label: "Connection Error", iconClass: "text-red-400" },
  llm: { icon: Bot, label: "AI Model Error", iconClass: "text-red-400" },
  tool: { icon: AlertCircle, label: "Tool Error", iconClass: "text-red-400" },
  stream: { icon: AlertCircle, label: "Response Error", iconClass: "text-red-400" },
  unknown: { icon: HelpCircle, label: "Error", iconClass: "text-red-400" },
};

export function ErrorMessage({ type, message, details, suggestion }: ErrorMessageProps) {
  const [expanded, setExpanded] = useState(false);
  const config = TYPE_CONFIG[type];
  const Icon = config.icon;

  return (
    <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm">
      <div className="flex items-start gap-2">
        <Icon className={`h-4 w-4 mt-0.5 shrink-0 ${config.iconClass}`} />
        <div className="flex-1 min-w-0">
          <div className="font-semibold text-red-300 text-xs uppercase tracking-wider mb-0.5">
            {config.label}
          </div>
          <div className="text-red-200">{message}</div>
          {suggestion && (
            <div className="text-red-300/70 text-xs mt-1">{suggestion}</div>
          )}
        </div>
      </div>
      {details && (
        <div className="mt-2 border-t border-red-500/20 pt-2">
          <button
            onClick={() => setExpanded(!expanded)}
            className="flex items-center gap-1 text-xs text-red-400 hover:text-red-300 transition-colors"
          >
            {expanded ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
            {expanded ? "Hide details" : "Show details"}
          </button>
          {expanded && (
            <pre className="mt-2 text-xs text-red-300/60 bg-red-900/20 rounded p-2 overflow-x-auto whitespace-pre-wrap break-all">
              {details}
            </pre>
          )}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Verify component compiles**

Run: `cd web/frontend && npx tsc --noEmit src/components/ErrorMessage.tsx`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add web/frontend/src/components/ErrorMessage.tsx
git commit -m "feat: add ErrorMessage component for structured error display"
```

---

### Task 2: Integrate ErrorMessage into AgentChatBubble

**Files:**
- Modify: `web/frontend/src/components/AgentChatBubble.tsx`

**Interfaces:**
- Consumes: `ErrorMessage` from `./ErrorMessage`

- [ ] **Step 1: Add ErrorMessage import**

Add to imports at top of file:
```tsx
import { ErrorMessage } from "./ErrorMessage";
```

- [ ] **Step 2: Add error classification helper**

Add after `formatDateTime` function:
```tsx
function classifyError(errorStr: string): { type: "network" | "llm" | "tool" | "stream" | "unknown"; message: string; suggestion: string } {
  const lower = errorStr.toLowerCase();
  if (lower.includes("network") || lower.includes("fetch") || lower.includes("connection")) {
    return { type: "network", message: "Could not connect to the server", suggestion: "Check your connection and try again." };
  }
  if (lower.includes("stream") || lower.includes("sse")) {
    return { type: "stream", message: "Received an invalid response from the server", suggestion: "Try again." };
  }
  if (lower.includes("tool") || lower.includes("execute")) {
    return { type: "tool", message: errorStr, suggestion: "Verify the ticker symbol is correct." };
  }
  if (lower.includes("llm") || lower.includes("model") || lower.includes("api key")) {
    return { type: "llm", message: "The AI model encountered an error", suggestion: "Check your API key and try again." };
  }
  return { type: "unknown", message: errorStr, suggestion: "Try again." };
}
```

- [ ] **Step 3: Replace "No response" handling**

In `AgentChatBubble.tsx`, find and replace lines 568-578:

**Before:**
```tsx
if (toolCallsFromResponse.length === 0) {
  if (!fullResponse || !fullResponse.trim()) {
    if (hadExecutedTools) {
      updateMessage(currentMsgId, { isStreaming: false });
    } else {
      updateMessage(currentMsgId, { content: "No response", isStreaming: false });
    }
  } else {
    updateMessage(currentMsgId, { isStreaming: false });
  }
  break;
}
```

**After:**
```tsx
if (toolCallsFromResponse.length === 0) {
  if (!fullResponse || !fullResponse.trim()) {
    if (hadExecutedTools) {
      updateMessage(currentMsgId, { content: "__ERROR__tool_no_summary|The analysis completed but returned no summary.|Check the tool results above for data.", isStreaming: false });
    } else {
      updateMessage(currentMsgId, { content: "__ERROR__llm_no_response|No response received from the AI model.|Check your API key and connection, then try again.", isStreaming: false });
    }
  } else {
    updateMessage(currentMsgId, { isStreaming: false });
  }
  break;
}
```

- [ ] **Step 4: Replace network error handling**

Find and replace lines 456-461:

**Before:**
```tsx
} catch (fetchErr) {
  updateMessage(currentMsgId, {
    content: `Network error: ${fetchErr instanceof Error ? fetchErr.message : String(fetchErr)}`,
    isStreaming: false,
  });
  break;
}
```

**After:**
```tsx
} catch (fetchErr) {
  const errDetail = fetchErr instanceof Error ? fetchErr.message : String(fetchErr);
  updateMessage(currentMsgId, {
    content: `__ERROR__network|Could not connect to the server|${errDetail}`,
    isStreaming: false,
  });
  break;
}
```

- [ ] **Step 5: Replace HTTP error handling**

Find and replace lines 464-468:

**Before:**
```tsx
if (!response.ok) {
  let errText = "Chat completion failed";
  try { errText = (await response.json()).error || errText; } catch {}
  updateMessage(currentMsgId, { content: `Error: ${errText}`, isStreaming: false });
  break;
}
```

**After:**
```tsx
if (!response.ok) {
  let errText = "Chat completion failed";
  try { errText = (await response.json()).error || errText; } catch {}
  const classified = classifyError(errText);
  updateMessage(currentMsgId, { content: `__ERROR__${classified.type}|${classified.message}|${classified.suggestion}`, isStreaming: false });
  break;
}
```

- [ ] **Step 6: Replace stream error handling**

Find and replace lines 507-508:

**Before:**
```tsx
if (parsed.type === "error") {
  throw new Error(parsed.error || "Stream error");
}
```

**After:**
```tsx
if (parsed.type === "error") {
  const streamErr = parsed.error || "Stream error";
  const classified = classifyError(streamErr);
  updateMessage(currentMsgId, { content: `__ERROR__${classified.type}|${classified.message}|${classified.suggestion}`, isStreaming: false });
  break;
}
```

- [ ] **Step 7: Replace catch block error handling**

Find and replace lines 631-644:

**Before:**
```tsx
} catch (error) {
  console.error("AgentChat error:", error);
  let errorMessage: string;
  if (error instanceof Error) {
    errorMessage = `${error.message}\n${error.stack || ""}`;
  } else if (typeof error === "object" && error !== null) {
    errorMessage = JSON.stringify(error, null, 2);
  } else {
    errorMessage = String(error);
  }
  addMessage({
    role: "assistant",
    content: `Error: ${errorMessage}`
  });
}
```

**After:**
```tsx
} catch (error) {
  console.error("AgentChat error:", error);
  const rawMsg = error instanceof Error ? error.message : String(error);
  const classified = classifyError(rawMsg);
  const details = error instanceof Error ? error.stack : undefined;
  addMessage({
    role: "assistant",
    content: `__ERROR__${classified.type}|${classified.message}|${classified.suggestion}${details ? `|${details}` : ""}`
  });
}
```

- [ ] **Step 8: Update MessageBubble to render ErrorMessage**

In the `MessageBubble` component, find the assistant message rendering (lines 228-229):

**Before:**
```tsx
<div className="whitespace-pre-wrap">{msg.content}</div>
```

**After:**
```tsx
{msg.content.startsWith("__ERROR__") ? (() => {
  const parts = msg.content.split("|");
  const type = (parts[0].replace("__ERROR__", "") || "unknown") as "network" | "llm" | "tool" | "stream" | "unknown";
  return (
    <ErrorMessage
      type={type}
      message={parts[1] || "An error occurred"}
      suggestion={parts[2]}
      details={parts[3]}
    />
  );
})() : (
  <div className="whitespace-pre-wrap">{msg.content}</div>
)}
```

- [ ] **Step 9: Verify compilation**

Run: `cd web/frontend && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 10: Commit**

```bash
git add web/frontend/src/components/AgentChatBubble.tsx
git commit -m "feat: integrate ErrorMessage into AgentChatBubble"
```

---

### Task 3: Integrate ErrorMessage into IndicatorRailView

**Files:**
- Modify: `web/frontend/src/components/IndicatorRailView.tsx`

**Interfaces:**
- Consumes: `ErrorMessage` from `./ErrorMessage`

- [ ] **Step 1: Add ErrorMessage import**

Add to imports at top of file:
```tsx
import { ErrorMessage } from "./ErrorMessage";
```

- [ ] **Step 2: Replace "No response" handling**

Find and replace lines 359-365:

**Before:**
```tsx
if (toolCallsFromResponse.length === 0) {
  if (!fullResponse) {
    updateMessage(currentMsgId, { content: "No response", isStreaming: false });
  } else {
    updateMessage(currentMsgId, { isStreaming: false });
  }
  break;
}
```

**After:**
```tsx
if (toolCallsFromResponse.length === 0) {
  if (!fullResponse) {
    updateMessage(currentMsgId, { content: "__ERROR__llm_no_response|No response received from the AI model.|Check your API key and connection, then try again.", isStreaming: false });
  } else {
    updateMessage(currentMsgId, { isStreaming: false });
  }
  break;
}
```

- [ ] **Step 3: Replace catch block error handling**

Find and replace lines 412-417:

**Before:**
```tsx
} catch (err) {
  addMessage({
    role: "assistant",
    isStreaming: false,
    content: `Error: ${err instanceof Error ? err.message : "Unknown error"}`,
  });
}
```

**After:**
```tsx
} catch (err) {
  const rawMsg = err instanceof Error ? err.message : "Unknown error";
  const lower = rawMsg.toLowerCase();
  let type: "network" | "llm" | "tool" | "stream" | "unknown" = "unknown";
  if (lower.includes("network") || lower.includes("fetch")) type = "network";
  else if (lower.includes("llm") || lower.includes("model")) type = "llm";
  else if (lower.includes("tool")) type = "tool";
  else if (lower.includes("stream")) type = "stream";
  
  addMessage({
    role: "assistant",
    isStreaming: false,
    content: `__ERROR__${type}|${rawMsg}|Try again.`,
  });
}
```

- [ ] **Step 4: Update message rendering to handle errors**

Find the message rendering block (lines 628-649) and update the assistant message rendering:

**Before:**
```tsx
{msg.content}
```

**After:**
```tsx
{msg.content.startsWith("__ERROR__") ? (() => {
  const parts = msg.content.split("|");
  const type = (parts[0].replace("__ERROR__", "") || "unknown") as "network" | "llm" | "tool" | "stream" | "unknown";
  return (
    <ErrorMessage
      type={type}
      message={parts[1] || "An error occurred"}
      suggestion={parts[2]}
      details={parts[3]}
    />
  );
})() : msg.content}
```

- [ ] **Step 5: Verify compilation**

Run: `cd web/frontend && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 6: Commit**

```bash
git add web/frontend/src/components/IndicatorRailView.tsx
git commit -m "feat: integrate ErrorMessage into IndicatorRailView"
```

---

### Task 4: Update ErrorBoundary to use ErrorMessage

**Files:**
- Modify: `web/frontend/src/components/ErrorBoundary.tsx`

**Interfaces:**
- Consumes: `ErrorMessage` from `./ErrorMessage`

- [ ] **Step 1: Add ErrorMessage import**

Add to imports:
```tsx
import { ErrorMessage } from "./ErrorMessage";
```

- [ ] **Step 2: Replace fallback rendering**

Find and replace the fallback rendering (lines 35-48):

**Before:**
```tsx
return (
  this.props.fallback ?? (
    <div className="glass-panel p-6 text-center" role="alert">
      <AlertTriangle className="w-8 h-8 mx-auto mb-3 text-amber-400/60" />
      <p className="text-sm text-slate-400 mb-3">Something went wrong rendering this section.</p>
      <button
        onClick={this.handleRetry}
        className="inline-flex items-center gap-1.5 text-xs font-medium text-sky-400 hover:text-sky-300 bg-sky-500/10 hover:bg-sky-500/20 border border-sky-500/20 rounded-lg px-3 py-1.5 transition-colors"
      >
        <RefreshCw className="w-3 h-3" />
        Try again
      </button>
    </div>
  )
);
```

**After:**
```tsx
return (
  this.props.fallback ?? (
    <div className="p-4" role="alert">
      <ErrorMessage
        type="unknown"
        message="Something went wrong rendering this section."
        details={this.state.error?.stack}
        suggestion="Try again or refresh the page."
      />
      <button
        onClick={this.handleRetry}
        className="mt-3 inline-flex items-center gap-1.5 text-xs font-medium text-sky-400 hover:text-sky-300 bg-sky-500/10 hover:bg-sky-500/20 border border-sky-500/20 rounded-lg px-3 py-1.5 transition-colors"
      >
        <RefreshCw className="w-3 h-3" />
        Try again
      </button>
    </div>
  )
);
```

- [ ] **Step 3: Remove unused AlertTriangle import**

Remove `AlertTriangle` from the lucide-react import since it's no longer used.

- [ ] **Step 4: Verify compilation**

Run: `cd web/frontend && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 5: Commit**

```bash
git add web/frontend/src/components/ErrorBoundary.tsx
git commit -m "feat: update ErrorBoundary to use ErrorMessage component"
```

---

### Task 5: Verify and Test

**Files:**
- Test: Manual verification

- [ ] **Step 1: Run full TypeScript check**

Run: `cd web/frontend && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 2: Run existing tests**

Run: `cd web/frontend && npm test`
Expected: Tests pass (or only pre-existing failures)

- [ ] **Step 3: Manual verification checklist**

Verify in browser:
- [ ] "No response" is replaced with informative error messages
- [ ] Network errors show "Connection Error" with suggestion
- [ ] LLM errors show "AI Model Error" with suggestion
- [ ] Error details are expandable
- [ ] ErrorBoundary shows structured error instead of raw text
- [ ] Styling matches existing UI theme

- [ ] **Step 4: Final commit if needed**

```bash
git add -A
git commit -m "feat: complete improved error display integration"
```
