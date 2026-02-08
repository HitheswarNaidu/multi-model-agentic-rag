from rag.utils.date_extractor import DateExtractor


def test_date_extractor():
    de = DateExtractor()

    text = "Revenue in 2023 vs 2022"
    years = de.extract_years(text)
    assert "2023" in years
    assert "2022" in years

    text2 = "Report from 12/31/2023"
    dates = de.extract_dates(text2)
    assert "12/31/2023" in dates

    assert de.has_temporal_intent("What is the latest version?")
    assert de.has_temporal_intent("Compare with last year")
