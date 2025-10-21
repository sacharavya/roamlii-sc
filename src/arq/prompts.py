SportsDetailsPrompt = """
                            You are given a webpage containing one or more **sports event listings or detail pages**.

                            🎯 Your task:
                            Extract structured information about **individual sports events** and return them in the JSON schema provided.

                            Each extracted event should represent **one specific sporting event** (not a category or listing page).

                            ---

                            ### ✅ Include:
                            - Events that have a specific **title**, **date/time**, and **venue**.
                            - Sports like football, cricket, basketball, hockey, marathon, etc.
                            - Tournaments, matches, championships, leagues, or athletic meets.
                            - Pages or cards that clearly show a link to the event details or registration.
                            - Events mentioning price, tickets, or entry passes.

                            ---

                            ### 🚫 Exclude:
                            - Generic pages like "Upcoming Sports Events", "Top 10 Matches", or category overviews.
                            - News articles, blog posts, or unrelated content.
                            - Advertisements or unrelated promotions.

                            ---

                            ### 🧩 For each event, extract the following fields if available:
                            - **title**: Name of the event (e.g., “Intercity Football Cup 2025”)
                            - **description**: Overview or summary of the event.
                            - **sport_type**: Type of sport (e.g., Basketball, Cricket, Hockey).
                            - **venue**: Exact name or location of the venue.
                            - **display_photo**: The main image URL.
                            - **photos**: List of additional image URLs.
                            - **time_zone**: Time zone of the event (e.g., America/Regina).
                            - **event_link**: Direct URL to the event’s detail or registration page.
                            - **price**: Entry cost (can be numeric or text like "Free" or "Starts at $50").
                            - **hosts / sponsors**: Names of hosts, organizers, or sponsors.
                            - **address_line_1, city, province_state, postal_zip_code, country**: Full address details if available.
                            - **lat / lng**: Extract coordinates if mentioned in the page or metadata.
                            - **contact_email / contact_website / contact_primary_phone**: Organizer’s contact information.
                            - **time_slots**: Date and time or match schedule details.

                            ---

                            ### ⚙️ Notes:
                            - If an event spans multiple days or matches, list all available dates/times under **time_slots**.
                            - Extract full and accurate URLs.
                            - Return all results inside the **sports** list in JSON format.

                            Output should strictly follow the given schema.
                        """


FestivalDetailsPrompt = """
                            You are given a webpage that contains information about one or more festivals.

                            Your task:
                            Extract complete and structured details for each festival found on the page,
                            following the provided schema.

                            Extraction Guidelines:

                            🎯 For each festival, extract as much accurate data as possible for these fields:

                            - **title**: The official name or title of the festival.
                            - **description**: A clear and detailed summary of what the festival is about.
                            - **display_photo**: The main featured image or banner of the festival.
                            - **photos**: A list of additional photo URLs, if available.
                            - **start_date**: The starting date of the festival (use full date format if possible).
                            - **end_date**: The ending date of the festival.
                            - **time_zone**: The time zone in which the festival takes place (e.g., "America/Los_Angeles").
                            - **event_link**: The direct URL to the festival’s main or registration page.
                            - **price**: The cost of entry (e.g., "$50", "Free", "Donation").
                            - **hosts**: The names or organizations hosting the festival.
                            - **sponsors**: The names of any sponsors or partners.
                            - **address_line_1**: The street address or venue name where the festival occurs.
                            - **city**: The city where the festival is located.
                            - **province_state**: The state or province.
                            - **postal_zip_code**: The postal or ZIP code.
                            - **country**: The country of the festival.
                            - **lat / lng**: Latitude and longitude coordinates (if present in metadata or maps).
                            - **contact_email**: The organizer’s contact email.
                            - **contact_website**: The festival’s or organizer’s official website.
                            - **contact_primary_phone**: A phone number for inquiries or bookings.

                            Formatting Rules:
                            - Extract multiple festivals if the page lists more than one; each must be a separate object in `festivals`.
                            - Ensure all URLs (images, links, websites) are **absolute**.
                            - If a field is missing, leave it empty or omit it — do not guess or infer.
                            - Use visible, factual data from the page rather than assumed information.
                            - Dates should be human-readable and complete if possible (e.g., “June 15, 2025” instead of “06/15”).
                        """


EventDetailsPrompt = """
                            You are given a webpage that contains information about one or more events.

                            Your task:
                            Extract structured data for each event found on the page and return it in JSON format
                            following the provided schema.

                            Extraction Guidelines:

                            🎯 For each event, extract as much accurate data as possible for the following fields:

                            - **title**: The official event title or headline.
                            - **description**: A clear summary or detailed explanation of the event.
                            - **event_link**: The direct URL to the event’s main page or registration page.
                            - **price**: The cost of entry (e.g., "$20", "Free", "Donation", etc.).
                            - **display_photo**: The main featured image for the event.
                            - **photos**: A list of additional photo URLs if available.
                            - **time_zone**: The timezone in which the event occurs (e.g., "America/New_York").
                            - **hosts**: Names or organizations hosting the event.
                            - **sponsors**: Companies or individuals sponsoring the event.
                            - **address_line_1**: The street address or venue name.
                            - **city**: The city where the event takes place.
                            - **province_state**: The state, province, or region of the event.
                            - **postal_zip_code**: The postal or ZIP code.
                            - **country**: The country of the event.
                            - **lat / lng**: Latitude and longitude if available on the page or in metadata.
                            - **contact_email**: Any available contact email.
                            - **contact_website**: The event or organizer’s website URL.
                            - **contact_primary_phone**: Contact number for inquiries or reservations.
                            - **time_slots**: All available dates and times the event occurs (e.g., “March 12, 2025, 6:00 PM”).

                            Formatting Rules:
                            - Extract multiple events if the page lists several; each must be a separate object in `events`.
                            - Keep all URLs absolute (not relative).
                            - If a field is missing, omit it or leave it empty — do not guess or fabricate data.
                            - Prioritize accurate details found in the visible content over metadata or summaries.
                        """
