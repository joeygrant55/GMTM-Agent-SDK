"""Entry point for the SPARQ job image (Dockerfile.research-job). SPARQ_JOB picks the job:
'research' (default; weekly college research) or 'site_check' (daily signed-out site checks). Arguments pass through.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

if __name__ == "__main__":
    job = os.environ.get("SPARQ_JOB")
    job = "research" if job is None else job  # unset = the weekly research service; any other value must match exactly
    if job == "research":
        import college_research_job as module
    elif job == "site_check":
        import site_check_job as module
    else:
        print(f'{{"status": "failed", "error": "unknown SPARQ_JOB"}}')
        sys.exit(0)  # never a restart loop
    module.main(sys.argv[1:])
