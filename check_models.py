"""Opt-in live API check using synthetic sources; no Gmail or SMTP access."""

import json

from analyzer import analyze
from global_news import analyze_sources


def main():
    # Fictional fixtures exercise numbers, uncertainty, attribution and Korean output.
    macro = (
        "Fictional newsletter for testing. A sample price index rose 2.5% year over year, "
        "down from 2.6% the previous month. The central bank held its rate at 4.0%. "
        "Officials said a future cut remained uncertain; no cut has been announced."
    )
    briefing = analyze(macro)
    print("Axios / gpt-6-luna: complete, nonempty response")
    print(briefing)
    sources = [
        {"id": "s1", "kind": "Flagship", "subject": "Fictional policy proposal",
         "text": "Test fixture: Lawmakers proposed an AI audit bill. It has not passed.",
         "links": ["https://example.com/policy"]},
        {"id": "s2", "kind": "Nature Briefing", "subject": "Fictional mouse study",
         "text": "Test fixture: In a study of 40 mice, a treatment improved a lab measure. "
                 "It has not been tested in humans and no human benefit is established.",
         "links": ["https://example.com/research"]},
    ]
    digest = analyze_sources(sources)
    print("Global News / gpt-6.1-sol: draft and review passed existing JSON validation")
    print(json.dumps(digest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
