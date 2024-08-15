import re
import json
import xml.etree.ElementTree as ET
from typing import Union
import spacy

# Load Spacy NLP model
nlp = spacy.load("ru_core_news_lg")


class Scrub:
    def __init__(self):
        self.patterns = {
            "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            "phone": r"\b\+\d{1,3}\s*\(\d{2,3}\)\s*\d{3}-\d{2}-\d{2}\b",
            "passport": r"\b[A-ZА-Я]{2}\d{6}\b",
            "credit_card": r"\b\d{4}\s*\d{4}\s*\d{4}\s*\d{4}\b",
            "inn": r"\b\d{3}\s*\d{2}\s*\d{3}\s*\d{2}\s*\d{2}\.?\d?\b",
            "date": r"\d{2}\.\d{2}\.\d{4}",
            "id_number": r"\b(I|ID)\s*\d+\b",
            "address": r"\b[A-ZА-ЯЁ][a-zа-яё]+\s*\d+\s*[A-ZА-ЯЁ][a-zа-яё]+\s*\d+\b",
            "number": r"\b\d+\b",
            "bank_account": r"\b\d{16,19}\b",
        }

    def scrub_text(self, text: str) -> str:
        scrubbed_text = text
        scrubbed_text = self.scrub_pii_with_nlp(scrubbed_text)
        for category, pattern in self.patterns.items():
            if category == "phone":
                matches = re.finditer(pattern, scrubbed_text)
                for match in matches:
                    matched_phone = match.group(0)

                    # Remove parentheses from matched phone numbers
                    matched_phone = re.sub(r"^\((\d{3})\)$", r"\1", matched_phone)
                    scrubbed_text = scrubbed_text.replace(matched_phone, "[Скрыто]")
            else:
                scrubbed_text = re.sub(pattern, "[Скрыто]", scrubbed_text)

        return scrubbed_text

    def scrub_pii_with_nlp(self, text: str) -> str:
        nlp_doc = nlp(text)
        final_text = text

        for name in nlp_doc.ents:
            print(name.text, name.label_)
            if name.label_ == "PER":
                final_text = re.sub(re.escape(name.text), "[Скрыто]", final_text)
            if name.label_ == "LOC":
                final_text = re.sub(re.escape(name.text), "[Скрыто]", final_text)
            if name.label_ == "ORG":
                final_text = re.sub(re.escape(name.text), "[Скрыто]", final_text)

        return final_text

    def scrub(
        self, input_data: Union[str, dict], original_format: str = "txt"
    ) -> Union[str, dict]:
        if original_format == "json":
            scrubbed_data = json.loads(input_data)
            scrubbed_data = self.scrub_dict(scrubbed_data)
        elif original_format == "ndjson":
            scrubbed_data = [
                self.scrub_dict(json.loads(line)) for line in input_data.splitlines()
            ]
        elif original_format == "xml":
            root = ET.fromstring(input_data)
            self.scrub_xml(root)
            scrubbed_data = ET.tostring(root, encoding="unicode")
        else:
            scrubbed_data = self.scrub_text(input_data)
        return scrubbed_data

    def scrub_dict(self, data: dict) -> dict:
        for key, value in data.items():
            if isinstance(value, dict):
                data[key] = self.scrub_dict(value)
            elif isinstance(value, list):
                data[key] = [
                    self.scrub_dict(item) if isinstance(item, dict) else item
                    for item in value
                ]
            elif isinstance(value, str):
                data[key] = self.scrub_text(value)
        return data

    def scrub_xml(self, node: ET.Element) -> None:
        if node.text is not None:
            node.text = self.scrub_text(node.text)
        for child in node:
            self.scrub_xml(child)


if __name__ == "__main__":
    pii_scrubber = Scrub()
    file = "<some file path>"
    format = "<one of 'json', 'ndjson', 'xml' or 'txt'>"

    with open(file, "r") as f:
        input_data = f.read()

    scrubbed_data = pii_scrubber.scrub(input_data, format)
    print("Original data:")
    print(input_data)
    print("Scrubbed data:")
    print(scrubbed_data)
