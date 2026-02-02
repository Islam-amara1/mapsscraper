"""
Geographic utility to fetch real neighborhoods/districts from OpenStreetMap (Overpass API).
"""

import httpx
from rich.console import Console

console = Console()

async def fetch_neighborhoods(city_name: str) -> list:
    """
    Fetch real neighborhoods for a city using OpenStreetMap's Overpass API.
    """
    console.print(f"[cyan]🌐 Fetching official districts for {city_name} from OpenStreetMap...[/cyan]")
    
    # Overpass API Query
    # This looks for boundaries of type 'neighborhood' or 'suburb' within the area of the city name
    query = f"""
    [out:json][timeout:25];
    area[name="{city_name}"]->.searchArea;
    (
      node["place"~"neighborhood|suburb"](area.searchArea);
      way["place"~"neighborhood|suburb"](area.searchArea);
      relation["place"~"neighborhood|suburb"](area.searchArea);
    );
    out tags;
    """
    
    url = "https://overpass-api.de/api/interpreter"
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, data={"data": query})
            response.raise_for_status()
            data = response.json()
            
            neighborhoods = []
            for element in data.get("elements", []):
                tags = element.get("tags", {})
                name = tags.get("name")
                if name and name not in neighborhoods:
                    neighborhoods.append(name)
            
            # If we didn't find specific 'neighborhood' tags, try a broader search for 'quarter'
            if not neighborhoods:
                query_alt = f"""
                [out:json][timeout:25];
                area[name="{city_name}"]->.searchArea;
                (
                  node["place"~"quarter|district"](area.searchArea);
                );
                out tags;
                """
                response = await client.post(url, data={"data": query_alt})
                data = response.json()
                for element in data.get("elements", []):
                    name = element.get("tags", {}).get("name")
                    if name and name not in neighborhoods:
                        neighborhoods.append(name)

            # Clean and filter
            neighborhoods = sorted(list(set(neighborhoods)))
            console.print(f"[green]✅ Found {len(neighborhoods)} real districts![/green]")
            return neighborhoods

    except Exception as e:
        console.print(f"[yellow]⚠ Could not fetch districts from API: {e}[/yellow]")
        return []

if __name__ == "__main__":
    import asyncio
    async def test():
        n = await fetch_neighborhoods("Miami")
        print(f"Miami neighborhoods: {n}")
    asyncio.run(test())
