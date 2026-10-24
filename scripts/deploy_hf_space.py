"""Deploy the Django backend to a Hugging Face Docker Space.

The Space is public, so do not run this if the source must stay private.

Usage:
    $env:HF_TOKEN = "hf_..."
    python scripts/deploy_hf_space.py --username <hf-user> \
        --frontend-origin https://your-app.vercel.app

The script creates the Space if needed, sets the runtime variables, uploads a
staging copy of the backend, waits for the build and prints the public URL.
"""

import argparse
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {"__pycache__", "media", "staticfiles"}


def env_file_secret_key():
    path = REPO_ROOT / ".env"
    if not path.exists():
        return ""
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("DJANGO_SECRET_KEY="):
            return line.split("=", 1)[1].strip()
    return ""


def build_staging(target):
    def ignore(directory, names):
        return [n for n in names if n in SKIP_DIRS or n.endswith(".pyc")]

    shutil.copytree(REPO_ROOT / "backend", target / "backend", ignore=ignore)
    download = target / "backend" / "db.sqlite3"
    if download.exists():
        download.unlink()

    shutil.copy2(REPO_ROOT / "requirements.txt", target / "requirements.txt")
    shutil.copy2(REPO_ROOT / "deploy" / "hf-space" / "Dockerfile", target / "Dockerfile")
    shutil.copy2(REPO_ROOT / "deploy" / "hf-space" / "README.md", target / "README.md")


def space_url(username, space_name):
    return f"https://{username.lower()}-{space_name.lower().replace('_', '-')}.hf.space"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--username", required=True, help="Hugging Face username or org")
    parser.add_argument("--space-name", default="layout-preserving-ocr-api")
    parser.add_argument(
        "--frontend-origin",
        default="",
        help="Comma-separated browser origins allowed by CORS, e.g. https://app.vercel.app",
    )
    parser.add_argument("--secret-key", default="", help="Defaults to HF_TOKEN-independent local value")
    parser.add_argument("--token", default=os.environ.get("HF_TOKEN", ""), help="Defaults to $HF_TOKEN")
    parser.add_argument("--timeout", type=int, default=2700, help="Seconds to wait for the build")
    parser.add_argument("--dry-run", action="store_true", help="Only assemble and inspect the upload")
    args = parser.parse_args()

    staging = Path(tempfile.mkdtemp(prefix="hf-space-"))
    try:
        build_staging(staging)
        files = sorted(p.relative_to(staging).as_posix() for p in staging.rglob("*") if p.is_file())
        print(f"staged {len(files)} files in {staging}")

        if args.dry_run:
            for path in files:
                print(f"  {path}")
            return 0

        if not args.token:
            print("error: set HF_TOKEN or pass --token", file=sys.stderr)
            return 2

        secret = args.secret_key or env_file_secret_key()
        if not secret:
            print("error: DJANGO_SECRET_KEY not found; pass --secret-key", file=sys.stderr)
            return 2

        from huggingface_hub import HfApi

        api = HfApi(token=args.token)
        who = api.whoami()
        print(f"authenticated as {who['name']}")

        repo_id = f"{args.username}/{args.space_name}"
        api.create_repo(
            repo_id=repo_id,
            repo_type="space",
            space_sdk="docker",
            private=False,
            exist_ok=True,
        )
        print(f"space ready: {repo_id}")

        variables = {
            "DJANGO_DEBUG": "False",
            "DJANGO_ALLOWED_HOSTS": ".hf.space",
            "DJANGO_SERVE_MEDIA": "True",
            "DJANGO_SECURE_SSL_REDIRECT": "False",
            "PADDLEOCR_MODEL": "mobile",
        }
        if args.frontend_origin:
            variables["CORS_ALLOWED_ORIGINS"] = args.frontend_origin
            if "vercel.app" in args.frontend_origin:
                variables["CORS_ALLOWED_ORIGIN_REGEXES"] = r"https://.*\.vercel\.app"

        for key, value in variables.items():
            api.add_space_variable(repo_id=repo_id, key=key, value=value)
        api.add_space_secret(repo_id=repo_id, key="DJANGO_SECRET_KEY", value=secret)
        print(f"variables set: {', '.join(sorted(variables))}")

        api.upload_folder(
            folder_path=str(staging),
            repo_id=repo_id,
            repo_type="space",
            commit_message="Deploy layout-preserving OCR backend",
        )
        print("upload complete, waiting for the build (first build can take 10-20 min)")

        deadline = time.time() + args.timeout
        last_stage = None
        while time.time() < deadline:
            runtime = api.get_space_runtime(repo_id=repo_id)
            stage = runtime.stage
            if stage != last_stage:
                print(f"  stage: {stage}")
                last_stage = stage

            if stage == "RUNNING":
                url = space_url(args.username, args.space_name)
                print(f"\napi url: {url}")
                print(f"check:   {url}/api/documents/")
                print("\nset VITE_API_BASE_URL to this url and redeploy the frontend")
                return 0

            if stage in ("ERROR", "STOPPED"):
                print(f"\nbuild failed, inspect the logs: https://huggingface.co/spaces/{repo_id}")
                print(f"runtime stage: {stage}")
                return 1

            time.sleep(10)

        print("\nstill building after the timeout; open the Space page to watch it")
        return 1
    finally:
        shutil.rmtree(staging, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
