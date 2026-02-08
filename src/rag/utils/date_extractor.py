import re


class DateExtractor:
    # Matches years 1900-2099
    YEAR_PATTERN = re.compile(r"\b(?:19|20)\d{2}\b")

    # Matches simple MM/DD/YYYY or DD/MM/YYYY
    DATE_PATTERN = re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b")

    def extract_years(self, text: str) -> list[str]:
        return self.YEAR_PATTERN.findall(text)

    def extract_dates(self, text: str) -> list[str]:
        return self.DATE_PATTERN.findall(text)

    def has_temporal_intent(self, text: str) -> bool:
        keywords = {"latest", "recent", "newest", "oldest", "previous", "last year", "this year"}
        text_lower = text.lower()
        if any(kw in text_lower for kw in keywords):
            return True
        if self.extract_years(text):
            return True
        if self.extract_dates(text):
            return True
        return False
