# prefillManager.py

import logging
from openai import OpenAI
import json

logger = logging.getLogger(__name__)

class PrefillManager:
    """Manages the prefilling of form data based on case summaries"""

    def __init__(self, openai_client):
        self.openai_client = openai_client

    def extract_form_data(self, case_summary, category, subcategory, form_fields):
        """
        Extract relevant information from case summary for form prefilling
        """
        try:
            # Remove PII from summary first
            cleaned_summary = self._clean_pii(case_summary)

            # Create a prompt for GPT to extract information
            prompt = self._create_extraction_prompt(cleaned_summary, category, subcategory, form_fields)

            # Get response from OpenAI
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": prompt
                    },
                    {
                        "role": "user",
                        "content": cleaned_summary
                    }
                ],
                response_format={"type": "json_object"}
            )

            # Parse the response
            extracted_data = json.loads(response.choices[0].message.content)
            
            # Validate extracted data
            validated_data = self._validate_extracted_data(extracted_data, form_fields)

            return validated_data

        except Exception as e:
            logger.error(f"Error extracting form data: {str(e)}")
            return {}

    def _clean_pii(self, text):
        """
        Remove PII from text
        """
        import re
        
        # Define PII patterns
        pii_patterns = {
            'names': r'\b[A-Z][a-z]+ [A-Z][a-z]+\b',
            'dates': r'\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b',
            'emails': r'\b[\w\.-]+@[\w\.-]+\.\w+\b',
            'phones': r'\b\d{3}[-.)]\d{3}[-.)]\d{4}\b',
            'locations': r'\b\d+\s+[A-Z][a-z]+\s+(?:Street|Avenue|Road|Blvd|Boulevard|Lane|Drive|Way)\b'
        }

        cleaned_text = text
        for pattern_name, pattern in pii_patterns.items():
            cleaned_text = re.sub(pattern, f'[{pattern_name.upper()}]', cleaned_text)

        return cleaned_text

    def _create_extraction_prompt(self, summary, category, subcategory, form_fields):
        """
        Create a prompt for GPT to extract form field information
        """
        return f"""
        You are a legal form data extractor. Based on the following case summary, 
        extract relevant information for a {category} - {subcategory} form.
        
        Required fields: {', '.join(form_fields)}

        Rules:
        1. DO NOT include any personally identifiable information (PII)
        2. Only extract information that matches the required fields
        3. Use generic terms instead of specific names or details
        4. Return data in JSON format with field names as keys
        5. If a field's information is not found, omit it from the output
        6. Use appropriate legal terminology
        7. Ensure all values are appropriate for form fields

        Return format:
        {
            "fieldName": "extracted value",
            ...
        }
        """

    def _validate_extracted_data(self, data, form_fields):
        """
        Validate and clean extracted data
        """
        validated_data = {}
        
        for field in form_fields:
            if field in data:
                value = data[field]
                # Basic validation
                if isinstance(value, str):
                    # Clean the value
                    cleaned_value = value.strip()
                    if cleaned_value:  # Only include non-empty values
                        validated_data[field] = cleaned_value
                elif isinstance(value, (int, float)):
                    validated_data[field] = str(value)

        return validated_data

    def get_default_values(self, case_summary, category, subcategory, form_fields):
        """
        Main method to get default values for form fields
        """
        try:
            # Extract data
            extracted_data = self.extract_form_data(
                case_summary, 
                category, 
                subcategory, 
                form_fields
            )

            return extracted_data

        except Exception as e:
            logger.error(f"Error getting default values: {str(e)}")
            return {}