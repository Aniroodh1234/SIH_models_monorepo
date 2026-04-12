# Streaming Implementation Plan — SwarajDesk AI Report Generator

## Why Streaming?

Both `/survey-report` and `/analyze-report` take **60–190 seconds** to respond because:
1. RAG retrieval + reranking is slow (~3–8 s)
2. Gemini 2.5 Pro generates large JSON tokens progressively internally but we wait for the full response
3. For `/survey-report`, all three phases (survey, backend, fusion) complete silently before anything is returned

With streaming, the client receives meaningful output **as it is generated** — progress updates between phases and raw token chunks from Gemini as the LLM writes the JSON. The user sees something happening instead of a blank screen.

---

## Chosen Approach: Server-Sent Events (SSE)

| Option | Pros | Cons | Verdict |
|---|---|---|---|
| **SSE** (`text/event-stream`) | Native browser support, works over HTTP/1.1, simple to implement in FastAPI | One-way only | ✅ Best fit |
| WebSocket | Bi-directional | Overkill; requires WS upgrade; harder to use with REST clients | ❌ Too complex |
| HTTP chunked transfer (raw) | Simplest | No structured event types; hard to parse partial JSON | ❌ Messy |

SSE is the right choice because:
- `google.generativeai` supports `generate_content(stream=True)` natively
- FastAPI's `StreamingResponse` supports SSE out-of-the-box
- Browsers can consume it with `EventSource`; any HTTP client (curl, requests, fetch) works

---

## SSE Event Protocol

Every streamed response will emit **structured SSE events** with a `event:` type and a `data:` JSON payload. The client knows what is happening at each stage.

```
event: progress
data: {"phase": "retrieval", "message": "Retrieving survey documents...", "elapsed_s": 1.2}

event: progress
data: {"phase": "rerank", "message": "Reranking documents...", "elapsed_s": 4.5}

event: token
data: {"report": "survey_report", "chunk": "{\n  \"report_type\": \"survey_repor"}

event: token
data: {"report": "survey_report", "chunk": "t\",\n  \"category\": \"Health\","}

event: phase_complete
data: {"phase": "survey_report", "elapsed_s": 62.0}

event: complete
data: {"success": true, "total_time_seconds": 143.2}

event: error
data: {"error": "Pipeline failed", "detail": "..."}
```

---

## Files to Touch — Full Diff Map

```
models/
  llm/
    llm_loader.py              ← ADD generate_json_stream() method

services/
  report_generator/
    survey_report_generator.py  ← ADD generate_stream() method
    backend_report_generator.py ← ADD generate_stream() method
    fusion_report_generator.py  ← ADD generate_stream() method
    analyze_report_generator.py ← ADD generate_stream() method

pipelines/
  survey_pipeline.py           ← ADD run_stream() generator method
  backend_pipeline.py          ← ADD run_stream() generator method
  fusion_pipeline.py           ← ADD run_stream() generator method
  analyze_pipeline.py          ← ADD run_stream() generator method

app/
  routes/
    survey_report.py           ← ADD POST /survey-report/stream route
    analyze_report.py          ← ADD GET  /analyze-report/stream route

utils/
  sse_helpers.py               ← NEW: format_sse() helper function
```

> The **existing** non-streaming endpoints are untouched. New `/stream` sub-routes are added.

---

## Step-by-Step Implementation

---

### Step 1 — Add `generate_json_stream()` to `GeminiLLM`

**File:** `models/llm/llm_loader.py`

The `google.generativeai` SDK supports streaming by passing `stream=True` to `generate_content()`. When enabled, it returns an iterable of `GenerateContentResponse` chunks, each having a `.text` attribute containing the next token batch.

**Important:** When streaming, you **cannot** use `response_mime_type="application/json"` in the generation config — that forces a buffered response. You must use the plain text config and parse JSON from the full accumulated string at the end. But tokens still stream out live.

Add a new `GenerativeModel` instance for streaming (plain text, no mime type) and a new method:

```python
def generate_json_stream(self, prompt: str):
    """
    Stream raw token chunks from Gemini as they are generated.

    Yields:
        str — successive token chunks (partial JSON text)

    After all chunks are yielded, the caller is responsible for
    assembling and parsing the full JSON via extract_json().
    """
    # Use the text model (no response_mime_type — streaming incompatible with it)
    stream = self._stream_model.generate_content(prompt, stream=True)
    for chunk in stream:
        try:
            text = chunk.text
            if text:
                yield text
        except (ValueError, AttributeError):
            # Skip thought/metadata chunks from thinking model
            continue
```

Also add `self._stream_model` in `__init__()` alongside `self._model`:

```python
# Streaming config — plain text, no mime type (required for stream=True)
self._stream_generation_config = genai.types.GenerationConfig(
    temperature=LLM_TEMPERATURE,
    max_output_tokens=LLM_MAX_OUTPUT_TOKENS,
    top_p=LLM_TOP_P,
    top_k=LLM_TOP_K,
    # NOTE: response_mime_type is intentionally absent — incompatible with streaming
)

self._stream_model = genai.GenerativeModel(
    model_name=self.model_name,
    generation_config=self._stream_generation_config,
    safety_settings=self._safety_settings,
)
```

---

### Step 2 — Create `utils/sse_helpers.py`

**File:** `utils/sse_helpers.py` *(new file)*

A tiny helper to format Python dicts into valid SSE wire format:

```python
import json

def format_sse(event: str, data: dict) -> str:
    """
    Format a Server-Sent Event string.

    Args:
        event: SSE event type (e.g. "progress", "token", "complete", "error")
        data:  Dict payload — will be JSON-serialised into the data field

    Returns:
        A correctly formatted SSE string ready to be sent over the wire.
        The trailing double-newline is included (SSE spec requirement).

    Example output:
        event: progress
        data: {"phase": "retrieval", "message": "Retrieving documents..."}

    """
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"
```

---

### Step 3 — Add `generate_stream()` to each Report Generator

**Files:**
- `services/report_generator/survey_report_generator.py`
- `services/report_generator/backend_report_generator.py`
- `services/report_generator/fusion_report_generator.py`
- `services/report_generator/analyze_report_generator.py`

Pattern is identical for all four. Add a `generate_stream()` method that:
1. Builds the prompt (same as `generate()`)
2. Calls `self.llm.generate_json_stream(prompt)` — a generator
3. Yields raw text chunks
4. Accumulates chunks into a buffer
5. After iteration ends, parses the full buffer with `extract_json()`
6. Yields one final `"__result__"` sentinel chunk containing the parsed dict

```python
def generate_stream(self, category: str, documents: list):
    """
    Same as generate() but yields token chunks for streaming.

    Yields:
        str — raw LLM token chunks
        After all tokens: yields the sentinel string "__RESULT__:<json>"
    """
    if not documents:
        result = self._empty_report(category)
        yield f"__RESULT__:{json.dumps(result)}"
        return

    context = self.clusterer.build_context(documents)
    timestamp = datetime.now(timezone.utc).isoformat()
    prompt = SURVEY_REPORT_PROMPT.format(
        category=category,
        context=context,
        timestamp=timestamp,
    )

    buffer = ""
    for chunk in self.llm.generate_json_stream(prompt):
        buffer += chunk
        yield chunk   # pass raw tokens upstream

    # Parse final JSON from buffer
    result = extract_json(buffer) or self._empty_report(category)
    yield f"__RESULT__:{json.dumps(result)}"
```

---

### Step 4 — Add `run_stream()` to each Pipeline

**Files:**
- `pipelines/survey_pipeline.py`
- `pipelines/backend_pipeline.py`
- `pipelines/fusion_pipeline.py`
- `pipelines/analyze_pipeline.py`

Each pipeline's `run_stream()` is an **async generator** that:
- Yields SSE-formatted progress events for each non-LLM step (retrieval, dedup, rerank)
- Delegates to `report_generator.generate_stream()` for LLM token chunks
- Yields SSE token events for each LLM chunk
- Captures the `__RESULT__:` sentinel to extract the parsed dict
- Yields a `phase_complete` SSE event with the final parsed dict

```python
async def run_stream(self, category: str):
    """
    Async generator — yields SSE-formatted strings.

    Yields:
        SSE strings of event types: progress, token, phase_complete
    """
    from utils.sse_helpers import format_sse
    import asyncio

    start = time.perf_counter()

    # Step 1: Query Expansion
    yield format_sse("progress", {"phase": "query_expansion", "message": "Expanding query...", "elapsed_s": 0})
    keywords = CATEGORY_MAP.get(category, {}).get("keywords", [])
    expanded_query = await asyncio.get_event_loop().run_in_executor(
        None, self.llm.expand_query, category, keywords
    )

    # Step 2: Retrieval
    yield format_sse("progress", {"phase": "retrieval", "message": "Retrieving documents from vector store...", "elapsed_s": round(time.perf_counter() - start, 1)})
    raw_docs = await asyncio.get_event_loop().run_in_executor(
        None, self.retriever.retrieve, category, expanded_query, RETRIEVAL_TOP_K, "survey"
    )

    # Step 3: Deduplication
    yield format_sse("progress", {"phase": "deduplication", "message": "Deduplicating documents...", "elapsed_s": round(time.perf_counter() - start, 1)})
    unique_docs = self.deduplicator.remove(raw_docs)

    # Step 4: Severity tagging
    yield format_sse("progress", {"phase": "severity_tagging", "message": "Tagging severity levels...", "elapsed_s": round(time.perf_counter() - start, 1)})
    tagged_docs = self.severity_tagger.tag(unique_docs)

    # Step 5: Reranking
    yield format_sse("progress", {"phase": "reranking", "message": "Reranking documents...", "elapsed_s": round(time.perf_counter() - start, 1)})
    reranked_docs = await asyncio.get_event_loop().run_in_executor(
        None, self.reranker.rerank, expanded_query, tagged_docs, RERANKER_TOP_K
    )

    # Step 6: LLM generation — stream tokens
    yield format_sse("progress", {"phase": "llm_generation", "message": "Generating survey report with Gemini...", "elapsed_s": round(time.perf_counter() - start, 1)})

    result_dict = {}
    async for chunk in self._stream_report(self.report_generator, category, reranked_docs):
        if chunk.startswith("__RESULT__:"):
            result_dict = json.loads(chunk[len("__RESULT__:"):])
        else:
            yield format_sse("token", {"report": "survey_report", "chunk": chunk})

    elapsed = round(time.perf_counter() - start, 2)
    yield format_sse("phase_complete", {"phase": "survey_report", "elapsed_s": elapsed, "report": result_dict})
```

Where `_stream_report()` is a small helper that wraps the synchronous generator in `run_in_executor` using a queue-based pattern to bridge sync generators and async generators (see Step 5).

---

### Step 5 — Bridge Sync Generator → Async Generator

The `generate_stream()` methods on report generators are **synchronous generators** (they call a blocking Gemini stream). To yield their output from an `async def` route without blocking the event loop, use `run_in_executor` with a thread + `asyncio.Queue`:

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

_stream_executor = ThreadPoolExecutor(max_workers=4)

async def sync_gen_to_async(sync_gen):
    """
    Convert a synchronous generator to an async generator using a queue.
    Runs the sync generator in a thread pool, puts chunks on a queue,
    and yields them in the async context.
    """
    queue = asyncio.Queue()
    loop = asyncio.get_event_loop()
    SENTINEL = object()

    def producer():
        try:
            for item in sync_gen:
                loop.call_soon_threadsafe(queue.put_nowait, item)
        finally:
            loop.call_soon_threadsafe(queue.put_nowait, SENTINEL)

    loop.run_in_executor(_stream_executor, producer)

    while True:
        item = await queue.get()
        if item is SENTINEL:
            break
        yield item
```

Place this utility in `utils/sse_helpers.py` alongside `format_sse()`.

---

### Step 6 — `/survey-report/stream` Route (Special Case)

**File:** `app/routes/survey_report.py`

The survey route is the most complex because all three pipelines are sequential (fusion depends on survey + backend). For streaming:

- Phase 1 (survey) and Phase 2 (backend) **cannot run truly in parallel** when both streaming SSE to the same response — they would interleave tokens confusingly.
- **Strategy:** Run Phase 1 and Phase 2 sequentially for streaming (SSE clearly labeled per phase), then Phase 3.
- The non-streaming `/survey-report` can keep the parallel approach.

```python
from fastapi.responses import StreamingResponse
from utils.sse_helpers import format_sse, sync_gen_to_async
import json, time

@router.post("/survey-report/stream")
async def stream_survey_report(request: SurveyReportRequest):
    resolved = resolve_category(request.category)
    if resolved is None:
        raise HTTPException(status_code=400, detail={"error": f"Unknown category: '{request.category}'"})

    async def event_generator():
        start = time.perf_counter()
        survey_report = {}
        backend_report = {}

        # ── Phase 1: Survey ───────────────────────────────────────
        yield format_sse("pipeline_start", {"phase": "survey_report", "category": resolved})
        async for sse_chunk in get_survey_pipeline().run_stream(resolved):
            if sse_chunk.startswith("event: phase_complete"):
                # Extract the result dict from the phase_complete event
                data_line = sse_chunk.split("data: ", 1)[1].strip()
                survey_report = json.loads(data_line).get("report", {})
            yield sse_chunk

        # ── Phase 2: Backend ──────────────────────────────────────
        yield format_sse("pipeline_start", {"phase": "backend_report", "category": resolved})
        async for sse_chunk in get_backend_pipeline().run_stream(resolved):
            if sse_chunk.startswith("event: phase_complete"):
                data_line = sse_chunk.split("data: ", 1)[1].strip()
                backend_report = json.loads(data_line).get("report", {})
            yield sse_chunk

        # ── Phase 3: Fusion ───────────────────────────────────────
        yield format_sse("pipeline_start", {"phase": "fusion_report", "category": resolved})
        async for sse_chunk in get_fusion_pipeline().run_stream(resolved, survey_report, backend_report):
            yield sse_chunk

        total = round(time.perf_counter() - start, 2)
        yield format_sse("complete", {
            "success": True,
            "category": resolved,
            "total_time_seconds": total,
        })

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

---

### Step 7 — `/analyze-report/stream` Route

**File:** `app/routes/analyze_report.py`

Simpler — only one pipeline:

```python
@router.get("/analyze-report/stream")
async def stream_analyze_report():
    async def event_generator():
        start = time.perf_counter()
        pipeline = get_analyze_pipeline()

        async for sse_chunk in pipeline.run_stream(category="All"):
            yield sse_chunk

        total = round(time.perf_counter() - start, 2)
        yield format_sse("complete", {
            "success": True,
            "total_time_seconds": total,
            "retrieval_strategy": "Multi-Category MMR (Advanced RAG)",
        })

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

---

## SSE Event Reference (Full Protocol)

| Event type | When emitted | Data fields |
|---|---|---|
| `pipeline_start` | Beginning of each phase | `phase`, `category` |
| `progress` | Before each non-LLM step | `phase`, `message`, `elapsed_s` |
| `token` | Each LLM token chunk | `report` (report name), `chunk` (raw text) |
| `phase_complete` | After each full report is done | `phase`, `elapsed_s`, `report` (full JSON dict) |
| `complete` | After everything finishes | `success`, `total_time_seconds` |
| `error` | On any exception | `error`, `detail` |

---

## Client Consumption Examples

### Browser — `EventSource` API

```javascript
const source = new EventSource('/analyze-report/stream');

source.addEventListener('progress', e => {
  const d = JSON.parse(e.data);
  console.log(`[${d.phase}] ${d.message} (${d.elapsed_s}s)`);
});

source.addEventListener('token', e => {
  const d = JSON.parse(e.data);
  process.stdout.write(d.chunk); // stream tokens to UI
});

source.addEventListener('phase_complete', e => {
  const d = JSON.parse(e.data);
  console.log('Report ready:', d.report);
});

source.addEventListener('complete', e => {
  const d = JSON.parse(e.data);
  console.log('All done in', d.total_time_seconds, 's');
  source.close();
});

source.addEventListener('error', e => {
  console.error('Stream error:', JSON.parse(e.data));
  source.close();
});
```

> **Note:** `EventSource` only supports `GET`. For the `POST /survey-report/stream` endpoint, use `fetch()` with `ReadableStream` instead (see below).

### Browser — `fetch()` with `ReadableStream` (for POST)

```javascript
const resp = await fetch('/survey-report/stream', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ category: 'Health' }),
});

const reader = resp.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  const text = decoder.decode(value);
  // Parse SSE lines from `text`
  for (const line of text.split('\n')) {
    if (line.startsWith('data: ')) {
      const data = JSON.parse(line.slice(6));
      console.log(data);
    }
  }
}
```

### Python — `requests` (streaming)

```python
import requests, json

with requests.post(
    "http://127.0.0.1:8000/survey-report/stream",
    json={"category": "Health"},
    stream=True
) as resp:
    for line in resp.iter_lines():
        if line:
            line = line.decode()
            if line.startswith("data: "):
                data = json.loads(line[6:])
                print(data)
```

### curl

```bash
curl -N -X POST http://127.0.0.1:8000/survey-report/stream \
  -H "Content-Type: application/json" \
  -d '{"category": "Health"}'

# -N disables buffering so chunks appear in real-time
```

---

## Important Caveats & Gotchas

### 1. `response_mime_type="application/json"` is incompatible with streaming
The current `self._model` in `GeminiLLM` has `response_mime_type="application/json"` set. This forces the Gemini API to buffer the **full** response before returning it — meaning even with `stream=True`, you will get one giant chunk at the end, not incremental tokens. The new `self._stream_model` must omit this setting. You will need to call `extract_json()` on the accumulated buffer after the stream ends.

### 2. Gemini Thinking Model chunks
Gemini 2.5 Pro (thinking model) emits "thought" parts before text parts. In streaming mode, `chunk.text` raises `ValueError` on thought chunks. The `generate_json_stream()` implementation must catch `ValueError` and skip those chunks (already shown in Step 1).

### 3. FastAPI `StreamingResponse` + `asyncio`
FastAPI's `StreamingResponse` accepts any async generator. Do not `await` the generator — just pass it to `StreamingResponse()`. The ASGI server (uvicorn) will pull chunks when the client is ready. This backpressure works correctly out of the box.

### 4. Thread-blocking sync generators
`generate_json_stream()` in `GeminiLLM` calls the Google SDK's synchronous iterator. This **blocks its thread**. The `sync_gen_to_async()` bridge (Step 5) runs it in a thread pool executor so the event loop is never blocked. Without this, no other requests can be handled while one stream is running.

### 5. Timeout on client side
These reports take 60–190 seconds. Ensure the client does not impose a short read timeout. For `requests`, set `timeout=300`. For nginx/reverse proxies, increase `proxy_read_timeout`.

### 6. The `/survey-report/stream` cannot use `asyncio.gather` for Phase 1 + 2
The original non-streaming route runs Phase 1 and Phase 2 in parallel with `asyncio.gather`. In streaming mode, tokens from both phases would be interleaved and confusing for the client. The streaming route runs them **sequentially** — Phase 1 fully completes before Phase 2 starts. This adds ~30–60 s latency compared to the parallel approach, but produces a coherent stream.

---

## Rollout Order (Recommended)

1. `utils/sse_helpers.py` — foundation, no dependencies
2. `models/llm/llm_loader.py` — add `_stream_model` + `generate_json_stream()`
3. All four `services/report_generator/*.py` — add `generate_stream()`
4. All four `pipelines/*.py` — add `run_stream()`
5. `app/routes/analyze_report.py` — simpler route first (GET, single pipeline)
6. `app/routes/survey_report.py` — more complex route (POST, 3 phases)
7. Test with curl using `-N` flag and verify SSE events appear incrementally
