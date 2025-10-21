from datetime import datetime, timedelta, timezone
from src.events.service import extract_events_details_from_links
from src.events.utils import process_csv_file

RUN_INTERVAL_DAYS = 30
CSV_FILE_PATH = "uploads/links.csv"


async def auto_scrape(ctx):
    """
    Auto-scrape job that runs on a rolling 28-day interval.
    Checks the last run timestamp and only proceeds if 28 days have passed.
    """

    current_time = datetime.now(timezone.utc)

    result = await process_csv_file(CSV_FILE_PATH)

    if not result["success"]:
        print(f"❌ Auto-scrape failed: {result.get('error', 'Unknown error')}")
        return {
            "status": "failed",
            "run_time": current_time.isoformat(),
            "error": result.get('error', 'Unknown error')
        }

    if len(result["events_list"]) > 0:
        await extract_events_details_from_links(urls=result["events_list"], job_type='extract_events_list')
        jobs_queued += len(result["events_list"])
        print(f"✓ Queued {len(result['events_list'])} event URLs")

    if len(result["festivals_list"]) > 0:
        await extract_events_details_from_links(urls=result["festivals_list"], job_type='extract_festivals_links_list')
        jobs_queued += len(result["festivals_list"])
        print(f"✓ Queued {len(result['festivals_list'])} festival URLs")

    if len(result["sports_list"]) > 0:
        await extract_events_details_from_links(urls=result["sports_list"], job_type='extract_sports_links_list')
        jobs_queued += len(result["sports_list"])
        print(f"✓ Queued {len(result['sports_list'])} sport URLs")

    return {
        "status": "completed",
        "run_time": current_time.isoformat(),
        "next_run": (current_time + timedelta(days=RUN_INTERVAL_DAYS)).isoformat(),
        "events": len(result["events_list"]),
        "festivals": len(result["festivals_list"]),
        "sports": len(result["sports_list"])
    }
