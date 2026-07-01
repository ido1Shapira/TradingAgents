# Improved Error Display Design

## Problem

Errors in the chat interface are displayed as plain text with minimal context:
- "No response" when LLM returns empty content
- Raw error messages with stack traces
- No visual distinction between error types
- No actionable guidance for users

## Goals

1. Replace unhelpful "No response" with informative messaging
2. Visually distinguish error types (network, LLM, tool, stream)
3. Hide raw stack traces and technical details from users
4. Provide actionable suggestions where possible
5. Maintain consistent styling with existing UI

## Design

### 1. Error Message Component

Create a reusable `ErrorMessage` component in `src/components/ErrorMessage.tsx`:

```tsx
interface ErrorMessageProps {
  type: "network" | "llm" | "tool" | "stream" | "unknown";
  message: string;
  details?: string; // hidden by default, expandable
  suggestion?: string;
}
```

**Visual design:**
- Red-tinted background (`bg-red-500/10`)
- Red border (`border-red-500/30`)
- Icon: `AlertCircle` from lucide-react
- Type label (e.g., "Network Error", "Analysis Failed")
- Message text
- Optional expandable details section
- Optional suggestion text

### 2. Error Type Mapping

| Error Source | Type | User-Friendly Message | Suggestion |
|--------------|------|----------------------|------------|
| Network fetch failure | `network` | "Could not connect to the server" | "Check your connection and try again" |
| HTTP 4xx/5xx | `network` | "Server returned an error" | "Try again in a moment" |
| LLM stream error | `llm` | "The AI model encountered an error" | "Try rephrasing your question" |
| Empty LLM response | `llm` | "The AI model returned an empty response" | "Try a different question or check your API key" |
| Tool execution failure | `tool` | "Failed to fetch data for {ticker}" | "Verify the ticker symbol is correct" |
| SSE parse error | `stream` | "Received an invalid response" | "Try again" |
| Unknown error | `unknown` | "Something went wrong" | "Try again" |

### 3. "No response" Replacement

**Current behavior** (`AgentChatBubble.tsx:573`, `IndicatorRailView.tsx:361`):
```tsx
updateMessage(currentMsgId, { content: "No response", isStreaming: false });
```

**New behavior:**
- If `hadExecutedTools` is true: "The analysis completed but returned no summary. Check the tool results above for data."
- If `hadExecutedTools` is false: "No response received. The AI model may be unavailable. Check your API key and connection."

### 4. Error Details Expansion

The `details` prop contains technical info (stack traces, raw errors). Hidden by default with a "Show details" toggle. Users can expand to see technical details for debugging.

### 5. Files to Modify

1. **New:** `src/components/ErrorMessage.tsx` - Reusable error component
2. **Edit:** `src/components/AgentChatBubble.tsx` - Replace error string formatting with ErrorMessage
3. **Edit:** `src/components/IndicatorRailView.tsx` - Replace error string formatting with ErrorMessage
4. **Edit:** `src/components/ErrorBoundary.tsx` - Use ErrorMessage in fallback

### 6. Testing

- Verify error component renders with all error types
- Verify "No response" is replaced with informative messages
- Verify expandable details toggle works
- Verify styling matches existing UI theme
