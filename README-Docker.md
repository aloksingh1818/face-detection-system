# Docker / Production Notes

This repository contains a small Dockerfile to help run the project in a reproducible container.

Notes:
- The base image installs `cmake` and `build-essential` so `dlib` can be built inside the image if required.
- Building `dlib` can be slow and may need additional tuning or dependencies depending on the platform.

Quick build & run:

```bash
# Build image
docker build -t face-attendai:dev .

# Run container (expose port 5000)
docker run -p 5000:5000 --rm face-attendai:dev
```

If you want production-level deployment, consider:
- Using a lightweight WSGI server (gunicorn/uvicorn) instead of Flask's dev server.
- Adding healthchecks, logging, and a process manager.
- Preparing prebuilt dlib wheels for your target platform or using a base image that already contains dlib.
