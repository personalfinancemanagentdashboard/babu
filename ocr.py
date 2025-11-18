import os
import json
import re
from typing import Dict
from openai import OpenAI
from models import CATEGORIES

class OCRResult:
    def __init__(self, title: str, amount: str, category: str, date: str, type: str):
        self.title = title
        self.amount = amount
        self.category = category
        self.date = date
        self.type = type
    
    def to_dict(self):
        return {
            "title": self.title,
            "amount": self.amount,
            "category": self.category,
            "date": self.date,
            "type": self.type
        }

def extract_transaction_from_image(image_base64: str, openai_client: OpenAI) -> OCRResult:
    categories_str = ", ".join(CATEGORIES)
    system_prompt = f"""You are a financial receipt/bill analyzer. Extract transaction information from images and return it in JSON format.

Extract the following:
- title: A brief description of the transaction (e.g., "Grocery Shopping at Walmart", "Electricity Bill")
- amount: The total amount as a number (no currency symbols, just the number)
- category: One of these categories: {categories_str}
- date: The transaction date in YYYY-MM-DD format (if not visible, use today's date)
- type: Either "income" or "expense" (receipts are usually expenses)

Rules:
1. Be accurate with the amount - look for "Total", "Amount Due", or similar
2. Choose the most appropriate category
3. For bills, use "Bills" category
4. For shopping receipts, categorize based on items (Food for groceries, etc.)
5. If you can't determine something, make a reasonable guess

Return ONLY valid JSON in this exact format:
{{
  "title": "Description here",
  "amount": "1234.56",
  "category": "Food",
  "date": "2024-01-15",
  "type": "expense"
}}"""
    
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Extract the transaction details from this receipt/bill image:"
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=500,
            temperature=0.2
        )
        
        content = response.choices[0].message.content
        if not content:
            raise Exception("No response from OpenAI")
        
        json_match = re.search(r'\{[\s\S]*\}', content)
        if not json_match:
            raise Exception("Could not parse JSON from response")
        
        result_data = json.loads(json_match.group(0))
        
        if not all(key in result_data for key in ["title", "amount", "category", "date", "type"]):
            raise Exception("Incomplete transaction data extracted")
        
        if result_data["category"] not in CATEGORIES:
            result_data["category"] = "Other"
        
        if result_data["type"] not in ["income", "expense"]:
            result_data["type"] = "expense"
        
        return OCRResult(**result_data)
        
    except Exception as error:
        print(f"OCR extraction error: {error}")
        raise Exception(f"Failed to extract transaction from image: {str(error)}")
