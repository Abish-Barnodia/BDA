#!/usr/bin/env python3
"""
generate_sample_data.py — Generate sample E-commerce clickstream data.
ponytail: zero external dependencies, pure standard library csv + random.
Matches Kaggle eCommerce multi-category store dataset schema with status codes.
"""

import csv
import os
import random
from datetime import datetime, timedelta

SCHEMA = [
    "event_time",
    "event_type",
    "product_id",
    "category_id",
    "category_code",
    "brand",
    "price",
    "user_id",
    "user_session",
    "status_code"  # ponytail: included to satisfy both clickstream & error rate requirements
]

EVENT_TYPES = ["view", "view", "view", "cart", "purchase"]
CATEGORIES = [
    ("2053013555631882655", "electronics.smartphone", "samsung"),
    ("2053013555631882656", "electronics.smartphone", "apple"),
    ("2053013555631882657", "electronics.audio.headphone", "sony"),
    ("2053013554415534427", "computers.notebook", "lenovo"),
    ("2053013554415534428", "computers.notebook", "hp"),
    ("2053013552359990379", "appliances.kitchen.refrigerators", "lg"),
    ("2053013553559191699", "apparel.shoes", "nike"),
    ("2053013553559191700", "apparel.shoes", "adidas"),
    ("2053013552259326987", "appliances.environment.vacuum", "dyson"),
    ("2053013552259326988", "furniture.living_room.sofa", "ikea"),
]
PRODUCTS = [1004856, 1004767, 1005115, 4804056, 1002544, 1005212, 1003306, 1004249, 1307067, 5100816]
STATUS_CODES = [200, 200, 200, 200, 200, 200, 200, 304, 404, 500]  # ~10% error/warning

def generate(num_rows: int = 10000, output_path: str = "data/clickstream_sample.csv"):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    base_time = datetime(2019, 11, 1, 0, 0, 0)
    
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(SCHEMA)
        
        for i in range(num_rows):
            # Distribute time across 48 hours with midday peaks
            hour_offset = random.randint(0, 47)
            # Add bias toward peak business hours (14:00 - 18:00)
            if random.random() < 0.4:
                hour_offset = (hour_offset // 24) * 24 + random.randint(14, 18)
                
            minute = random.randint(0, 59)
            second = random.randint(0, 59)
            event_time = (base_time + timedelta(hours=hour_offset, minutes=minute, seconds=second)).strftime("%Y-%m-%d %H:%M:%S UTC")
            
            cat_id, cat_code, brand = random.choice(CATEGORIES)
            prod_id = random.choice(PRODUCTS)
            event_type = random.choice(EVENT_TYPES)
            price = round(random.uniform(20.0, 1500.0), 2)
            user_id = random.randint(50000000, 50099999)
            session_id = f"{random.randint(10000000, 99999999):x}-{random.randint(1000, 9999):x}"
            status = random.choice(STATUS_CODES)
            
            writer.writerow([event_time, event_type, prod_id, cat_id, cat_code, brand, price, user_id, session_id, status])
            
    print(f"[+] Successfully generated {num_rows} sample records -> {output_path}")

if __name__ == "__main__":
    generate()
