# Urban Flood SIH

## Run locally

Start the backend from the project root:

```powershell
python -m uvicorn backend.main:app --reload --port 8000
```

Serve the frontend from the project root in a second terminal:

```powershell
python -m http.server 5500
```

Open `http://127.0.0.1:5500`. The frontend uses the FastAPI endpoints at
`http://127.0.0.1:8000`, with the mock flood engine used automatically when a
SWMM input file or `pyswmm` is unavailable.