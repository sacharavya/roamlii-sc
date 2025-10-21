from pydantic import BaseModel, Field
from typing import Optional


class ExtractEventDetailsFromMultipleMainUrlsBody(BaseModel):
    links: list[str]


class ExtractEventDetailsFromSingleMainUrlBody(BaseModel):
    url: str


class MainLinkSchema(BaseModel):
    """Schema for extracting event links from main pages"""
    links: list[str] = Field(
        ...,
        description="List of URLs that link to individual event pages"
    )


class EventDetail(BaseModel):
    """Schema for individual event details"""
    title: str = Field(..., description="The title of the event.")
    description: str = Field(...,
                             description="A detailed description of the event.")
    event_link: str = Field(..., description="Direct link to the event page")
    price: Optional[str] = Field(
        None, description="The price of the event. Can be a number or text like 'Free'")
    display_photo: Optional[str] = Field(
        None, description="The main photo URL for the event listing.")
    photos: Optional[list[str]] = Field(
        default_factory=list, description="List of additional photo URLs.")
    time_zone: Optional[str] = Field(
        None, description="The time zone for the event (e.g., America/Regina).")
    hosts: Optional[list[str]] = Field(
        default_factory=list, description="The names of the event hosts")
    sponsors: Optional[list[str]] = Field(
        default_factory=list, description="The names of the event sponsors")
    address_line_1: Optional[str] = Field(
        None, description="The primary street address.")
    city: Optional[str] = Field(
        None, description="The city where the event is located.")
    province_state: Optional[str] = Field(
        None, description="The province or state.")
    postal_zip_code: Optional[str] = Field(
        None, description="The postal or zip code.")
    country: Optional[str] = Field(None, description="Country")
    lat: Optional[float] = Field(
        None, description="The latitude of the location.")
    lng: Optional[float] = Field(
        None, description="The longitude of the location.")
    contact_email: Optional[str] = Field(
        None, description="A contact email for the event.")
    contact_website: Optional[str] = Field(
        None, description="A contact website for the event.")
    contact_primary_phone: Optional[str] = Field(
        None, description="A contact phone number.")
    time_slots: Optional[list[str]] = Field(
        default_factory=list, description="The date and time slots for the event.")


class EventDetailsSchema(BaseModel):
    """Schema for multiple event details extraction"""
    events: list[EventDetail] = Field(
        ...,
        description="List of extracted event details"
    )


class FestivalDetail(BaseModel):
    """Schema for individual festival details"""
    title: str = Field(..., description="The title of the festival.")
    description: str = Field(...,
                             description="A detailed description of the festival.")
    display_photo: Optional[str] = Field(
        None, description="The main photo URL for the festival listing.")
    photos: Optional[list[str]] = Field(
        default_factory=list, description="List of additional photo URLs.")
    start_date: str = Field(..., description="The start date of the festival.")
    end_date: str = Field(..., description="The end date of the festival.")
    time_zone: str = Field(...,
                           description="The time zone for the festival (e.g., America/Regina).")
    event_link: str = Field(..., description="Direct link to the event page")
    price: Optional[str] = Field(
        None, description="The price of the festival.")
    hosts: Optional[list[str]] = Field(
        default_factory=list, description="The names of the festival hosts.")
    sponsors: Optional[list[str]] = Field(
        default_factory=list, description="The names of the festival sponsors.")
    address_line_1: Optional[str] = Field(
        None, description="The primary street address.")
    city: Optional[str] = Field(
        None, description="The city where the festival is located.")
    province_state: Optional[str] = Field(
        None, description="The province or state.")
    postal_zip_code: Optional[str] = Field(
        None, description="The postal or zip code.")
    country: Optional[str] = Field(None, description="Country")
    lat: Optional[float] = Field(
        None, description="The latitude of the location.")
    lng: Optional[float] = Field(
        None, description="The longitude of the location.")
    contact_email: Optional[str] = Field(
        None, description="A contact email for the festival.")
    contact_website: Optional[str] = Field(
        None, description="A contact website for the festival.")
    contact_primary_phone: Optional[str] = Field(
        None, description="A contact phone number.")


class FestivalsDetailsSchema(BaseModel):
    """Schema for multiple festivals details extraction"""
    festivals: list[FestivalDetail] = Field(
        ...,
        description="List of extracted festivals details"
    )


class SportDetail(BaseModel):
    """Schema for individual sport event details"""
    title: str = Field(..., description="The title of the sport event.")
    description: str = Field(...,
                             description="A detailed description of the sport event.")
    sport_type: str = Field(...,
                            description="The type of sport (e.g., Basketball, Hockey).")
    venue: str = Field(...,
                       description="The name of the venue where the event takes place.")
    display_photo: Optional[str] = Field(
        None, description="Main sport event photo URL")
    photos: Optional[list[str]] = Field(
        default_factory=list, description="Additional sport event photos")
    time_zone: str = Field(...,
                           description="The time zone for the festival (e.g., America/Regina).")
    event_link: str = Field(...,
                            description="Direct link to the sport event page")
    price: Optional[str] = Field(
        None, description="The price of the event. Can be a number or text like 'Free'")
    hosts: Optional[list[str]] = Field(
        default_factory=list, description="The names of the event hosts")
    sponsors: Optional[list[str]] = Field(
        default_factory=list, description="The names of the event sponsors")
    address_line_1: Optional[str] = Field(
        None, description="The primary street address")
    city: Optional[str] = Field(
        None, description="The city where the event is located.")
    province_state: Optional[str] = Field(
        None, description="The province or state.")
    postal_zip_code: Optional[str] = Field(
        None, description="The postal or zip code.")
    country: Optional[str] = Field(None, description="Country")
    lat: Optional[float] = Field(
        None, description="The latitude of the location.")
    lng: Optional[float] = Field(
        None, description="The longitude of the location")
    contact_email: Optional[str] = Field(
        None, description="A contact email for the event")
    contact_website: Optional[str] = Field(
        None, description="A contact website for the event")
    contact_primary_phone: Optional[str] = Field(
        None, description="A contact phone number.")
    time_slots: Optional[list[str]] = Field(
        default_factory=list, description="The date and time slots for the sport event.")


class SportsDetailsSchema(BaseModel):
    """Schema for multiple sports details extraction"""
    sports: list[SportDetail] = Field(
        ...,
        description="List of extracted sports event details"
    )


# For backward compatibility and JSON schema format for Firecrawl
EVENT_DETAILS_SCHEMA = {
    "type": "object",
    "required": ["events"],
    "properties": {
        "events": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["title", "description", "event_link"],
                "properties": {
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "price": {"type": "string"},
                    "event_link": {"type": "string"},
                    "display_photo": {"type": "string"},
                    "photos": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "time_zone": {"type": "string"},
                    "hosts": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "sponsors": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "address_line_1": {"type": "string"},
                    "city": {"type": "string"},
                    "province_state": {"type": "string"},
                    "postal_zip_code": {"type": "string"},
                    "country": {"type": "string"},
                    "lat": {"type": "number"},
                    "lng": {"type": "number"},
                    "contact_email": {"type": "string"},
                    "contact_website": {"type": "string"},
                    "contact_primary_phone": {"type": "string"},
                    "time_slots": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                }
            }
        }
    }
}
