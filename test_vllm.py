import asyncio, os, sys, time
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

BASE_URL = os.environ.get("LITELLM_BASE_URL", "http://localhost:4000/v1")
API_KEY = os.environ.get("LITELLM_API_KEY")
if not API_KEY:
    sys.exit("Set LITELLM_API_KEY first")

N = int(os.environ.get("N", 200))             # total requests
CONCURRENCY = int(os.environ.get("C", 50))    # requests in flight at once

client = AsyncOpenAI(base_url=BASE_URL, api_key=API_KEY, max_retries=0, timeout=300)
sem = asyncio.Semaphore(CONCURRENCY)

async def one(i):
    async with sem:
        t = time.perf_counter()
        try:
            r = await client.chat.completions.create(
                model="local-llm",  # fixed name of model
                messages=[{"role": "user", "content": f"Request {i}: explain how a rainbow forms."}],
                max_tokens=128,
            )
            return time.perf_counter() - t, r.usage.completion_tokens, None
        except Exception as e:
            return time.perf_counter() - t, 0, type(e).__name__

async def main():
    start = time.perf_counter()
    results = await asyncio.gather(*(one(i) for i in range(N)))
    wall = time.perf_counter() - start
    ok = sorted(lat for lat, _, err in results if not err)
    errors = [err for _, _, err in results if err]
    tokens = sum(tok for _, tok, _ in results)
    print(f"{len(ok)}/{N} ok, {len(errors)} failed {set(errors) or ''}")
    print(f"{wall:.1f}s total | {len(ok) / wall:.1f} req/s | {tokens / wall:.0f} tokens/s")
    if ok:
        print(f"latency p50 {ok[len(ok) // 2]:.2f}s | p95 {ok[int(len(ok) * 0.95)]:.2f}s | max {ok[-1]:.2f}s")

asyncio.run(main())