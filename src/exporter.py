"""
Data export functionality for Google Maps Scraper.
Supports CSV, JSON, and Excel formats.
"""

import pandas as pd
import json
import os
from datetime import datetime
from src.config import Settings


class Exporter:
    def __init__(self, output_dir: str = None):
        self.output_dir = output_dir or Settings.OUTPUT_DIR
        os.makedirs(self.output_dir, exist_ok=True)
    
    def _generate_filename(self, query: str, location: str, extension: str) -> str:
        """Generate filename with timestamp"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Clean query and location for filename
        clean_query = query.replace(" ", "_").lower()[:20]
        clean_location = location.replace(" ", "_").replace(",", "").lower()[:20]
        return os.path.join(
            self.output_dir,
            f"{clean_query}_{clean_location}_{timestamp}.{extension}"
        )
    
    def to_csv(self, data: list, query: str, location: str) -> str:
        """Export to CSV file"""
        if not data:
            print("No data to export")
            return None
        
        df = pd.DataFrame(data)
        filepath = self._generate_filename(query, location, "csv")
        df.to_csv(filepath, index=False, encoding='utf-8-sig')
        print(f"💾 Saved CSV: {filepath}")
        return filepath
    
    def to_json(self, data: list, query: str, location: str) -> str:
        """Export to JSON file"""
        if not data:
            print("No data to export")
            return None
        
        filepath = self._generate_filename(query, location, "json")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"💾 Saved JSON: {filepath}")
        return filepath
    
    def to_excel(self, data: list, query: str, location: str) -> str:
        """Export to Excel file"""
        if not data:
            print("No data to export")
            return None
        
        df = pd.DataFrame(data)
        filepath = self._generate_filename(query, location, "xlsx")
        df.to_excel(filepath, index=False, engine='openpyxl')
        print(f"💾 Saved Excel: {filepath}")
        return filepath
    
    def export_all(self, data: list, query: str, location: str) -> dict:
        """Export to all formats"""
        return {
            'csv': self.to_csv(data, query, location),
            'json': self.to_json(data, query, location),
            'excel': self.to_excel(data, query, location)
        }


# Test
if __name__ == "__main__":
    test_data = [
        {"name": "Test Cafe", "rating": 4.5, "address": "123 Main St", "phone": "+1 555-1234"},
        {"name": "Another Place", "rating": 4.2, "address": "456 Oak Ave", "phone": "+1 555-5678"},
    ]
    
    exporter = Exporter()
    exporter.export_all(test_data, "coffee shops", "Manhattan")
