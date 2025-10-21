# CSV Upload Guide for Event Scraper

## Overview
The Event Scraper now supports CSV file upload to process multiple URLs for event extraction. This feature allows you to upload a CSV file containing URLs instead of manually providing them in a JSON request.

## API Endpoint

### POST `/api/events/extract_events_from_csv`

Upload a CSV file containing URLs to scrape for event details.

## CSV File Format

The CSV file should contain URLs in one of the following formats:

### Option 1: Single column with header
```csv
url
https://example.com/events
https://example2.com/calendar
https://example3.com/festivals
```

### Option 2: Multiple columns (uses 'url', 'website', or 'link' column)
```csv
website,name,category
https://example.com/events,Event Site 1,Music
https://example2.com/calendar,Event Site 2,Sports
https://example3.com/festivals,Event Site 3,Culture
```

### Option 3: No header (uses first column)
```csv
https://example.com/events
https://example2.com/calendar
https://example3.com/festivals
```

## Requirements

- File must be in CSV format (`.csv` extension)
- URLs must start with `http://` or `https://`
- Accepted column names: `url`, `website`, `link` (case-insensitive)
- If no recognized column name is found, the first column will be used

## Usage Examples

### Using cURL
```bash
curl -X POST "http://localhost:8000/api/events/extract_events_from_csv" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@sample_urls.csv"
```

### Using Python requests
```python
import requests

url = "http://localhost:8000/api/events/extract_events_from_csv"
files = {'file': open('sample_urls.csv', 'rb')}

response = requests.post(url, files=files)
print(response.json())
```

### Using Postman
1. Select POST method
2. Enter URL: `http://localhost:8000/api/events/extract_events_from_csv`
3. Go to "Body" tab
4. Select "form-data"
5. Add a key named `file` with type "File"
6. Choose your CSV file
7. Click "Send"

### Using HTTPie
```bash
http -f POST http://localhost:8000/api/events/extract_events_from_csv file@sample_urls.csv
```

## Response Format

Successful upload returns:
```json
{
  "status": "queued",
  "method": "single",
  "message": "Successfully queued 3 URLs for scraping (single URL method)",
  "urls_queued": 3,
  "job_ids": ["uuid-1", "uuid-2", "uuid-3"],
  "source": "csv_upload",
  "filename": "sample_urls.csv",
  "urls_extracted": 3
}
```

## Error Handling

### Invalid file type
```json
{
  "detail": "Invalid file type. Please upload a CSV file (.csv)"
}
```

### No valid URLs found
```json
{
  "detail": "No valid URLs found in the CSV file"
}
```

### Invalid CSV format
```json
{
  "detail": "Failed to parse CSV file: [error details]"
}
```

## Processing Flow

1. **Upload CSV** → API receives and validates the file
2. **Parse URLs** → Extracts and validates URLs from CSV
3. **Queue Jobs** → Each URL is queued as an ARQ background job
4. **Scrape Events** → Workers scrape event links from each main URL
5. **Extract Details** → Workers extract detailed event information
6. **Store Results** → Events are saved to Redis and exported to CSV

## Monitoring Progress

After uploading, you can monitor the scraping progress using:

### Get Queue Statistics
```bash
GET /api/firecrawl/queue/stats
```

### Get Extracted Events
```bash
GET /api/events/all?limit=10&offset=0
```

## Notes

- All processing happens asynchronously via ARQ workers
- The endpoint returns immediately after queuing jobs
- Results are stored in Redis and exported to `events_details.csv`
- Invalid URLs in the CSV are logged and skipped
- The existing URL-based endpoints remain available for backward compatibility

## Existing Endpoints (Still Available)

### Single URL
```bash
POST /api/events/extract_event_from_single_main_url
Body: {"url": "https://example.com/events"}
```

### Multiple URLs (JSON)
```bash
POST /api/events/extract_events_from_multiple_main_urls
Body: {"links": ["https://example.com/events", "https://example2.com/calendar"]}
```

## Sample CSV File

A sample CSV file (`sample_urls.csv`) is included in the project root for testing purposes.
