#!/usr/bin/env python3
"""
Simple stress test for LLMeQueue - quick and lightweight.

Usage:
    python simple_stress_test.py --requests 10
    python simple_stress_test.py --requests 50 --concurrency 10
"""

import asyncio
import aiohttp
import time
import argparse
import random


# Test questions dataset - randomly selected for each request
TEST_QUESTIONS = [
    "What is the meaning of life?",
    "How does machine learning work?",
    "Explain quantum computing in simple terms",
    "What are the benefits of renewable energy?",
    "How do neural networks learn patterns?",
    "What is the difference between AI and ML?",
    "Explain the concept of blockchain technology",
    "How does photosynthesis work in plants?",
    "What causes climate change?",
    "Describe the theory of relativity",
    "How do vaccines work in the human body?",
    "What is the purpose of DNA in living organisms?",
    "Explain how the internet works",
    "What are the main principles of democracy?",
    "How does cryptocurrency mining work?",
    "What is natural language processing?",
    "Explain the water cycle on Earth",
    "How do black holes form in space?",
    "What is the greenhouse effect?",
    "Describe how a computer processor works",
    "What are the key components of a healthy diet?",
    "How does memory work in the human brain?",
    "Explain the concept of supply and demand",
    "What is the difference between weather and climate?",
    "How do antibiotics fight bacterial infections?",
    "What is artificial general intelligence?",
    "Explain the concept of evolution",
    "How does GPS technology work?",
    "What are the different types of clouds?",
    "Describe the process of nuclear fusion",
    "How do solar panels generate electricity?",
    "What is the importance of biodiversity?",
    "Explain how language models are trained",
    "What causes earthquakes to occur?",
    "How does the human immune system work?",
    "What is the difference between RNA and DNA?",
    "Explain the concept of entropy in physics",
    "How do ocean currents affect climate?",
    "What is the role of mitochondria in cells?",
    "Describe how satellites stay in orbit",
    "What are the different layers of the atmosphere?",
    "How does fiber optic communication work?",
    "What is the carbon cycle in nature?",
    "Explain the concept of machine vision",
    "How do magnets work at the atomic level?",
    "What is the difference between weather forecasting and climate modeling?",
    "Describe the process of protein synthesis",
    "How does radar technology detect objects?",
    "What are the main causes of deforestation?",
    "Explain the concept of dark matter and dark energy",
    "How do electric motors convert energy?",
    "What is the nitrogen cycle in ecosystems?",
    "Describe how holograms are created",
    "What are the different states of matter?",
    "How does wireless charging technology work?",
]


async def submit_request(session, url, headers, task_num, task_type="embedding"):
    """Submit a single request and return response."""
    start = time.time()
    
    # Select a random question from the test set
    question = random.choice(TEST_QUESTIONS)
    
    if task_type == "embedding":
        payload = {"input": question}
    else:  # chat
        payload = {
            "model": "llama3.2:3b",
            "messages": [
                {"role": "user", "content": question}
            ]
        }
    
    try:
        # Use a longer timeout for chat completions to match the server's 180s wait time
        request_timeout = 185 if task_type == "chat" else 120
        async with session.post(url, 
            json=payload,
            headers=headers,
            timeout=request_timeout) as resp:
            elapsed = time.time() - start
            data = await resp.json()
            if resp.status == 200:
                if task_type == "embedding":
                    # Check if we got a result or just task ID
                    if "data" in data:  # Full embedding result
                        return {
                            "num": task_num,
                            "status": "completed",
                            "result": f"{len(data['data'][0]['embedding'])} dims",
                            "elapsed": elapsed,
                        }
                    elif "id" in data:  # Task ID (not yet complete)
                        return {
                            "num": task_num,
                            "status": "pending",
                            "task_id": data.get("id"),
                            "elapsed": elapsed,
                        }
                else:  # chat
                    # Check if we got a result or task ID
                    if "choices" in data:  # Full chat result
                        content = data["choices"][0]["message"]["content"]
                        return {
                            "num": task_num,
                            "status": "completed",
                            "result": f"{len(content)} chars",
                            "content": content,  # Store full content
                            "elapsed": elapsed,
                        }
                    elif "id" in data:  # Task ID (not yet complete)
                        return {
                            "num": task_num,
                            "status": "pending",
                            "task_id": data.get("id"),
                            "elapsed": elapsed,
                        }
                return {
                    "num": task_num,
                    "status": "unknown",
                    "data": str(data)[:50],
                    "elapsed": elapsed,
                }
            else:
                return {
                    "num": task_num,
                    "status": f"error_{resp.status}",
                    "elapsed": elapsed,
                }
    except Exception as e:
        elapsed = time.time() - start
        return {
            "num": task_num,
            "status": "exception",
            "error": str(e),
            "elapsed": elapsed,
        }


async def run_test(url, token, num_requests, concurrency, task_type="embedding"):
    """Run the stress test."""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    connector = aiohttp.TCPConnector(limit=concurrency)
    
    if task_type == "embedding":
        endpoint = "/v1/embeddings"
        wait_desc = "(120s timeout)"
    else:
        endpoint = "/v1/chat/completions"
        wait_desc = "(185s timeout)"
    
    print(f"\n🔥 SIMPLE STRESS TEST - {task_type.upper()}")
    print(f"   Requests: {num_requests}")
    print(f"   Concurrency: {concurrency}")
    print(f"   Endpoint: {url}{endpoint} {wait_desc}\n")
    
    results = []
    semaphore = asyncio.Semaphore(concurrency)
    completed_count = 0
    pending_count = num_requests
    lock = asyncio.Lock()
    
    async def bounded_request(i, session):
        nonlocal completed_count, pending_count
        async with semaphore:
            result = await submit_request(session, f"{url}{endpoint}", headers, i, task_type)
            results.append(result)
            
            async with lock:
                if result['status'] == 'completed':
                    completed_count += 1
                    pending_count = num_requests - completed_count
                    
            status_str = result['status'].ljust(12)
            result_str = result.get('result', result.get('task_id', ''))[:30]
            if task_type == "chat" and result.get('content'):
                print(f"[{i+1:2d}/{num_requests}] {status_str} {result.get('elapsed', 0):.3f}s → \"{result['content']}\" , load: {pending_count}")
            else:
                print(f"[{i+1:2d}/{num_requests}] {status_str} {result.get('elapsed', 0):.3f}s {result_str}, load: {pending_count}")
    
    start_total = time.time()
    async with aiohttp.ClientSession(connector=connector) as session:
        await asyncio.gather(*[bounded_request(i, session) for i in range(num_requests)])
    total_time = time.time() - start_total
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"RESULTS ({total_time:.1f}s total)")
    print(f"{'='*60}")
    
    completed_count = sum(1 for r in results if r["status"] == "completed")
    pending_count = sum(1 for r in results if r["status"] == "pending")
    error_count = sum(1 for r in results if r["status"] not in ("completed", "pending", "ok"))
    
    print(f"✅ Completed: {completed_count}/{num_requests}")
    if pending_count > 0:
        print(f"⏳ Pending: {pending_count}/{num_requests}")
    if error_count > 0:
        print(f"❌ Failed: {error_count}/{num_requests}")
    
    print(f"📊 Throughput: {num_requests / total_time:.1f} req/s")
    
    if results:
        times = [r["elapsed"] for r in results]
        print(f"⏱️  Response times: min={min(times):.3f}s, max={max(times):.3f}s, avg={sum(times)/len(times):.3f}s")
    
    # Show task IDs for pending tasks
    task_ids = [r.get("task_id") for r in results if r.get("task_id")]
    if task_ids:
        print(f"\n💾 Pending tasks ({len(task_ids)}):")
        for tid in task_ids[:3]:
            print(f"   - {tid}")
        if len(task_ids) > 3:
            print(f"   ... and {len(task_ids) - 3} more")


async def main():
    parser = argparse.ArgumentParser(description="Simple stress test for LLMeQueue")
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--token", default="your-secret-token")
    parser.add_argument("--requests", type=int, default=10)
    parser.add_argument("--concurrency", type=int, default=5)
    parser.add_argument("--task-type", choices=["embedding", "chat", "both"], default="both")
    
    args = parser.parse_args()
    
    try:
        if args.task_type == "both":
            # Run embedding tests first
            await run_test(args.url, args.token, args.requests, args.concurrency, "embedding")
            print("\n")
            # Then run chat tests
            await run_test(args.url, args.token, args.requests, args.concurrency, "chat")
        else:
            await run_test(args.url, args.token, args.requests, args.concurrency, args.task_type)
    except KeyboardInterrupt:
        print("\n⏹️  Test cancelled")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
