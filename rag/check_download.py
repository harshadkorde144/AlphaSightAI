import httpx

url = "https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/resolve/main/model.safetensors"
headers = {"Range": "bytes=0-1023"}

with httpx.stream("GET", url, follow_redirects=True, timeout=30, headers=headers) as response:
    print("Status:", response.status_code)
    print("Content-Range:", response.headers.get("content-range"))
    print("Content-Length:", response.headers.get("content-length"))
    print("Final host:", httpx.URL(str(response.url)).host)
    print("First chunk bytes:", len(next(response.iter_bytes(1024), b"")))
