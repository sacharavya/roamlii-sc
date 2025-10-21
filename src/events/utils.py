from pathlib import Path
from pydantic import BaseModel
import shutil
from typing import Dict, Any, List
import json
import pandas as pd
from fastapi import UploadFile, File

from src.logging import logger


def write_events_to_csv(event: Dict[str, Any], csv_file_path: str):
    """
    Write events to CSV file using pandas with a single header row.
    Creates the file with headers if it doesn't exist, otherwise appends data.

    Args:
        events: List of event dictionaries to write
        csv_file_path: Path to the CSV file
    """

    try:
        # Ensure the directory exists
        csv_path = Path(csv_file_path)
        csv_path.parent.mkdir(parents=True, exist_ok=True)

        # Field mapping: normalize inconsistent field names from scraper to schema
        field_mapping = {
            'address': 'address_line_1',
            'province/state': 'province_state',
            'postal/zip code': 'postal_zip_code',
            'latitude': 'lat',
            'longitude': 'lng',
            'contact email': 'contact_email',
            'contact website': 'contact_website',
            'contact primary phone': 'contact_primary_phone',
            'time slots': 'time_slots'
        }

        # Convert list fields to JSON strings for CSV storage and normalize field names
        events_processed = []
        # for event in events:
        # event_copy = event.copy()

        # Normalize field names
        for old_name, new_name in field_mapping.items():
            if old_name in event:
                event[new_name] = event.pop(old_name)

            # Convert list fields to JSON strings
        for field in ['photos', 'hosts', 'sponsors', 'time_slots']:
            if field in event and isinstance(event[field], list):
                event[field] = json.dumps(event[field])

        events_processed.append(event)

        # Create DataFrame from events
        df = pd.DataFrame(events_processed)

        # Define the column order matching EventDetail schema
        columns = [
            'title', 'description', 'event_link', 'price', 'display_photo',
            'photos', 'time_zone', 'hosts', 'sponsors', 'address_line_1',
            'city', 'province_state', 'postal_zip_code', 'country',
            'lat', 'lng', 'contact_email', 'contact_website',
            'contact_primary_phone', 'time_slots'
        ]

        # Ensure all columns exist in the DataFrame (add missing ones with empty values)
        for col in columns:
            if col not in df.columns:
                df[col] = ''

        # Reorder columns to match the schema
        df = df[columns]

        # Check if file exists
        file_exists = csv_path.exists()

        # Write to CSV (append mode if file exists, otherwise create new)
        df.to_csv(
            csv_file_path,
            mode='a' if file_exists else 'w',
            header=not file_exists,
            index=False,
            encoding='utf-8'
        )

        if not file_exists:
            logger.info(
                f"[CSV] Created new CSV file with headers: {csv_file_path}")
        else:
            logger.info(
                f"[CSV] Appended event to: {csv_file_path}")

    except Exception as e:
        logger.error(f"[CSV] Error writing to CSV file {csv_file_path}: {e}")
        raise


def write_festivals_to_csv(event: Dict[str, Any], csv_file_path: str):
    """
    Write events to CSV file using pandas with a single header row.
    Creates the file with headers if it doesn't exist, otherwise appends data.

    Args:
        events: List of event dictionaries to write
        csv_file_path: Path to the CSV file
    """

    try:
        # Ensure the directory exists
        csv_path = Path(csv_file_path)
        csv_path.parent.mkdir(parents=True, exist_ok=True)

        # Field mapping: normalize inconsistent field names from scraper to schema
        field_mapping = {
            'address': 'address_line_1',
            'province/state': 'province_state',
            'postal/zip code': 'postal_zip_code',
            'latitude': 'lat',
            'longitude': 'lng',
            'contact email': 'contact_email',
            'contact website': 'contact_website',
            'contact primary phone': 'contact_primary_phone',
            # 'time slots': 'time_slots'
        }

        # Convert list fields to JSON strings for CSV storage and normalize field names
        events_processed = []
        # for event in events:
        # event_copy = event.copy()

        # Normalize field names
        for old_name, new_name in field_mapping.items():
            if old_name in event:
                event[new_name] = event.pop(old_name)

            # Convert list fields to JSON strings
        for field in ['photos', 'hosts', 'sponsors']:
            if field in event and isinstance(event[field], list):
                event[field] = json.dumps(event[field])

        events_processed.append(event)

        # Create DataFrame from events
        df = pd.DataFrame(events_processed)

        # Define the column order matching EventDetail schema
        columns = [
            'title', 'description', 'event_link', 'price', 'display_photo',
            'photos', 'time_zone', 'hosts', 'sponsors', 'address_line_1',
            'city', 'province_state', 'postal_zip_code', 'country',
            'lat', 'lng', 'contact_email', 'contact_website',
            'contact_primary_phone', 'start_date', 'end_date'
        ]

        # Ensure all columns exist in the DataFrame (add missing ones with empty values)
        for col in columns:
            if col not in df.columns:
                df[col] = ''

        # Reorder columns to match the schema
        df = df[columns]

        # Check if file exists
        file_exists = csv_path.exists()

        # Write to CSV (append mode if file exists, otherwise create new)
        df.to_csv(
            csv_file_path,
            mode='a' if file_exists else 'w',
            header=not file_exists,
            index=False,
            encoding='utf-8'
        )

        if not file_exists:
            logger.info(
                f"[CSV] Created new CSV file with headers: {csv_file_path}")
        else:
            logger.info(
                f"[CSV] Appended event to: {csv_file_path}")

    except Exception as e:
        logger.error(f"[CSV] Error writing to CSV file {csv_file_path}: {e}")
        raise


async def save_uploaded_file(file: UploadFile = File(...), filename: str = "links.csv"):
    uploads_dir = Path("uploads")
    uploads_dir.mkdir(exist_ok=True)

    # Define file path - always save as links.csv (will overwrite if exists)
    file_path = uploads_dir / filename

    # Save the uploaded file locally
    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    logger.info(f"CSV file saved locally as: {file_path}")

    # Reset file pointer to beginning for further processing
    await file.seek(0)


async def parse_urls_from_csv(file: UploadFile) -> List[str]:
    """
    Parse URLs from uploaded CSV file.

    Accepts CSV with either:
    - Single column named 'url' or 'website'
    - Multiple columns where first column contains URLs
    - Header-less CSV where first column contains URLs

    Args:
        file: Uploaded CSV file from FastAPI

    Returns:
        List[str]: List of extracted URLs

    Raises:
        ValueError: If CSV is invalid or contains no URLs
    """
    try:
        # Read the uploaded file content
        contents = await file.read()

        # Try to read CSV with pandas
        try:
            # First, try reading with header
            df = pd.read_csv(pd.io.common.BytesIO(contents))

            # print('df', df)

            # Look for common URL column names
            url_column = None
            for col_name in ['url', 'website', 'link', 'URL', 'Base URL', 'Website', 'Link']:
                if col_name in df.columns:
                    url_column = col_name
                    break

            # If no named column found, use first column
            if url_column is None:
                url_column = df.columns[0]
                logger.info(
                    f"[CSV] No URL column found, using first column: {url_column}")
            else:
                logger.info(f"[CSV] Using column: {url_column}")

            urls = df[url_column].dropna().astype(str).tolist()

        except Exception as e:
            # If reading with header fails, try without header
            logger.warning(
                f"[CSV] Failed to read with header, trying without: {e}")
            df = pd.read_csv(pd.io.common.BytesIO(contents), header=None)
            urls = df[0].dropna().astype(str).tolist()

        # Filter out empty strings and strip whitespace
        urls = [url.strip() for url in urls if url.strip()]

        # Basic URL validation
        valid_urls = []
        for url in urls:
            if url.startswith('http://') or url.startswith('https://'):
                valid_urls.append(url)
            else:
                logger.warning(f"[CSV] Skipping invalid URL: {url}")

        if not valid_urls:
            raise ValueError(
                "No valid URLs found in CSV file. URLs must start with http:// or https://")

        logger.info(
            f"[CSV] Successfully parsed {len(valid_urls)} valid URLs from uploaded file")
        return valid_urls

    except pd.errors.EmptyDataError:
        raise ValueError("CSV file is empty")
    except Exception as e:
        logger.error(f"[CSV] Error parsing CSV file: {e}")
        raise ValueError(f"Failed to parse CSV file: {str(e)}")


class TypeFromCSVResponse(BaseModel):
    events_list: List[str]
    festivals_list: List[str]
    sports_list: List[str]
    success: bool


async def parse_urls_by_type_from_csv(file: UploadFile) -> TypeFromCSVResponse:
    """
    Parse URLs from uploaded CSV file and group them by type.

    Expects CSV with columns:
    - 'Website URL': The URL to scrape
    - 'Type (event | festival | sport)': The type of content

    Args:
        file: Uploaded CSV file from FastAPI

    Returns:
        Dict[str, List[str]]: Dictionary with keys 'events_list', 'festivals_list', 'sports_list'
                              containing their respective URLs

    Raises:
        ValueError: If CSV is invalid, missing required columns, or contains no valid URLs
    """
    try:
        # Read the uploaded file content
        contents = await file.read()
        # print('contents', contents)
        # Read CSV with pandas
        try:
            df = pd.read_csv(pd.io.common.BytesIO(contents))
        except Exception as e:
            raise ValueError(f"Failed to read CSV file: {str(e)}")

        # Check for required columns
        url_column = None
        type_column = None

        # Find URL column
        for col_name in ['Base URL', 'url', 'website', 'link', 'URL', 'Website URL', 'Link']:
            if col_name in df.columns:
                url_column = col_name  # Website URL
                break

        # Find Type column
        for col_name in ['Type', 'type']:
            if col_name in df.columns:
                type_column = col_name  # Type
                break

        if url_column is None:
            raise ValueError(
                "CSV must contain a URL column (e.g., 'Base URL', 'url', 'website')")

        if type_column is None:
            raise ValueError(
                "CSV must contain a Type column (e.g., 'Type (event | festival| sport)', 'Type')")

        logger.info(
            f"[CSV] Using URL column: {url_column}, Type column: {type_column}")

        # Initialize result dictionaries
        events_list = []
        festivals_list = []
        sports_list = []

        # Process each row
        for _, row in df.iterrows():
            url = row.get(url_column)
            url_type = row.get(type_column)

            # Skip if URL or type is missing/empty
            if pd.isna(url) or pd.isna(url_type):
                continue

            url = str(url).strip()
            url_type = str(url_type).strip().lower()

            # Validate URL format
            if not (url.startswith('http://') or url.startswith('https://')):
                logger.warning(f"[CSV] Skipping invalid URL: {url}")
                continue

            # Categorize by type
            if 'event' in url_type:
                events_list.append(url)
            elif 'festival' in url_type:
                festivals_list.append(url)
            elif 'sport' in url_type:
                sports_list.append(url)
            else:
                logger.warning(
                    f"[CSV] Unknown type '{url_type}' for URL: {url}, skipping")

        # Create result dictionary
        result = {
            'events_list': events_list,
            'festivals_list': festivals_list,
            'sports_list': sports_list,
            'success': True
        }

        # Validate that we have at least some URLs
        total_urls = len(events_list) + len(festivals_list) + len(sports_list)
        if total_urls == 0:
            raise ValueError(
                "No valid URLs found in CSV file. URLs must start with http:// or https:// and have a valid type")

        logger.info(
            f"[CSV] Successfully parsed URLs by type: "
            f"{len(events_list)} events, {len(festivals_list)} festivals, {len(sports_list)} sports"
        )

        return result

    except pd.errors.EmptyDataError:
        raise ValueError("CSV file is empty")
    except ValueError:
        raise
    except Exception as e:
        logger.error(f"[CSV] Error parsing CSV file: {e}")
        raise ValueError(f"Failed to parse CSV file: {str(e)}")


async def process_csv_file(file_path: str):
    """
    Process CSV file from local filesystem and extract URLs by type.

    Args:
        file_path: Path to the CSV file

    Returns:
        dict: Dictionary with events_list, festivals_list, sports_list
    """
    try:
        csv_path = Path(file_path)

        if not csv_path.exists():
            logger.warning(f"[Auto-Scrape] CSV file not found: {file_path}")
            return {
                "events_list": [],
                "festivals_list": [],
                "sports_list": [],
                "success": False,
                "error": "CSV file not found"
            }

        # Read CSV file
        df = pd.read_csv(csv_path)

        # Find URL and Type columns
        url_column = None
        type_column = None

        for col_name in ['Base URL', 'url', 'website', 'link', 'URL', 'Website URL', 'Link']:
            if col_name in df.columns:
                url_column = col_name
                break

        for col_name in ['Type', 'type']:
            if col_name in df.columns:
                type_column = col_name
                break

        if url_column is None or type_column is None:
            logger.error(
                f"[Auto-Scrape] CSV missing required columns. Found: {df.columns.tolist()}")
            return {
                "events_list": [],
                "festivals_list": [],
                "sports_list": [],
                "success": False,
                "error": "Missing required columns (URL and Type)"
            }

        # Initialize result lists
        events_list = []
        festivals_list = []
        sports_list = []

        # Process each row
        for _, row in df.iterrows():
            url = row.get(url_column)
            url_type = row.get(type_column)

            if pd.isna(url) or pd.isna(url_type):
                continue

            url = str(url).strip()
            url_type = str(url_type).strip().lower()

            # Validate URL format
            if not (url.startswith('http://') or url.startswith('https://')):
                logger.warning(f"[Auto-Scrape] Skipping invalid URL: {url}")
                continue

            # Categorize by type
            if 'event' in url_type:
                events_list.append(url)
            elif 'festival' in url_type:
                festivals_list.append(url)
            elif 'sport' in url_type:
                sports_list.append(url)
            else:
                logger.warning(
                    f"[CSV] Unknown type '{url_type}' for URL: {url}, skipping")

        total_urls = len(events_list) + len(festivals_list) + len(sports_list)
        logger.info(
            f"[Auto-Scrape] Parsed {total_urls} URLs: "
            f"{len(events_list)} events, {len(festivals_list)} festivals, {len(sports_list)} sports"
        )

        return {
            "events_list": events_list,
            "festivals_list": festivals_list,
            "sports_list": sports_list,
            "success": True
        }

    except pd.errors.EmptyDataError:
        raise ValueError("CSV file is empty")
    except ValueError:
        raise
    except Exception as e:
        logger.error(f"[CSV] Error parsing CSV file: {e}")
        raise ValueError(f"Failed to parse CSV file: {str(e)}")
