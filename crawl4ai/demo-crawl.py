from crawl4ai import AsyncWebCrawler, CacheMode, CrawlerRunConfig
from crawl4ai import (
    DefaultMarkdownGenerator,
    PruningContentFilter,
    LLMExtractionStrategy,
    LLMConfig,
    JsonCssExtractionStrategy,
    DomainFilter,
    FilterChain,
    BFSDeepCrawlStrategy,
)
import json
import asyncio
import base64
import os
from pathlib import Path


async def demo_basic_crawl():
    """Basic crawling example"""
    print("\n=== 1. Basic crawling ===")
    async with AsyncWebCrawler() as crawler:
        results = await crawler.arun(
            url="https://news.ycombinator.com/",
        )
        for i, result in enumerate(results):
            print(f"Result {i + 1}: {result.url}")
            print(f"Success: {result.success}")
            if result.success:
                if result.markdown:
                    print(f"Markdown length: {len(result.markdown.raw_markdown)} chars")
                    if result.markdown.raw_markdown:
                        print(
                            f"First 100 chars: {result.markdown.raw_markdown[:100]}..."
                        )
            else:
                print("Failed to crawwl the URL")


async def demo_parallel_crawl():
    """Crawl multiple URLs in parallel"""
    print("\n=== 2. Crawl multiple URLs in parallel ===")
    urls = [
        "https://news.ycombinator.com/",
        "https://example.com/",
        "https://httpbin.org/html",
    ]
    async with AsyncWebCrawler() as crawler:
        results = await crawler.arun_many(urls=urls)
        for i, result in enumerate(results):
            print(
                f"  {i + 1}. {result.url} - {'Success' if result.success else 'Failed'}"
            )


async def demo_fit_markdown():
    """Generate focused markdown with LLM content filter"""
    print("\n=== 3. Generate focused markdown with LLM content filter ===")
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(
            url="https://en.wikipedia.org/wiki/Python_(programming_language)",
            config=CrawlerRunConfig(
                markdown_generator=DefaultMarkdownGenerator(
                    content_filter=PruningContentFilter()
                )
            ),
        )
    print(f"Raw: {(len(result.markdown.raw_markdown))} chars")
    print(f"Fit: {(len(result.markdown.fit_markdown))} chars")


async def demo_llm_structured_extraction_no_schema():
    """Create a simple LLM extraction strategy (no schema required)"""
    print("\n=== 4. Create a simple LLM extraction strategy (no schema required) ===")
    extraction_strategy = LLMExtractionStrategy(
        llm_config=LLMConfig(
            provider="openrouter/deepseek/deepseek-r1-0528-qwen3-8b:free",
            api_token=os.environ["OPEN_ROUTER_KEY"],
        ),
        instruction="This is news.ycombinator.com. Extract all news and for each "
        "I want title, source url, number of comments.",
        extract_type="schema",
        schema="{title: string, url: string, comments: int}",
        extra_args={
            "max_tokens": 4096,
            "temperature": 0.0,
        },
        verbose=True,
    )
    config = CrawlerRunConfig(extraction_strategy=extraction_strategy)
    async with AsyncWebCrawler() as crawler:
        results = await crawler.arun("https://news.ycombinator.com/", config=config)
        for result in results:
            print(f"Success: {result.success}")
            print(f"URL: {result.url}")
            if result.success:
                data = json.loads(result.extracted_content)
                print(json.dumps(data, indent=2))
            else:
                print("Failed to extract structured data")


async def demo_css_structured_extraction_schema():
    schema_file_path = os.getcwd() + "tmp/schema.json"
    if os.path.exists(schema_file_path):
        with open(schema_file_path, "r") as f:
            schema = json.load(f)
    else:
        with open("scrape.html", "r") as f:
            html = f.read()
        schema = JsonCssExtractionStrategy.generate_schema(
            html=html,
            llm_config=LLMConfig(
                provider="openrouter/deepseek/deepseek-r1-0528-qwen3-8b:free",
                api_token=os.environ["OPEN_ROUTER_KEY"],
            ),
            query="from https://thehackernew.com/, I have shared a sample html of one of the news div"
            "with a title, date, description. Generate a schema for this news div",
        )
        with open(schema_file_path, "w") as f:
            json.dump(schema, f, indent=2)

    print(f"Generated schema: {json.dumps(schema, indent=2)}")

    extraction_strategy = JsonCssExtractionStrategy(schema)
    config = CrawlerRunConfig(extraction_strategy=extraction_strategy)
    async with AsyncWebCrawler() as crawler:
        results = await crawler.arun("https://thehackernews.com/", config=config)
        for result in results:
            print(f"Success: {result.success}")
            print(f"URL: {result.url}")
            if result.success:
                data = json.loads(result.extracted_content)
                print(json.dumps(data, indent=2))
            else:
                print("Failed to extract structured data")


async def demo_deep_crawl():
    """Deep crawling with BFS strategy"""
    print("\n=== 6. Deep crawling with BFS strategy ===")
    filter_chain = FilterChain([DomainFilter(allowed_domains=["pawsey.atlassian.net"])])
    deep_crawl_strategy = BFSDeepCrawlStrategy(
        max_depth=4, max_pages=40, filter_chain=filter_chain
    )
    async with AsyncWebCrawler() as crawler:
        results = await crawler.arun(
            url="https://pawsey.atlassian.net/wiki/spaces/US/pages/51923228/Visualisation+Documentation",
            config=CrawlerRunConfig(
                deep_crawl_strategy=deep_crawl_strategy,
            ),
        )
        print(f"Deep crawl returned {len(results)} pages")
        for i, result in enumerate(results):
            depth = result.metadata.get("depth", 0)
            print(f"Result {i + 1}: {result.url} - Depth: {depth}")


async def demo_media_and_links():
    """Extract media and links from a webpage"""
    print("\n=== 8. Extract media and links from a webpage ===")
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun("https://en.wikipedia.org/wiki/Computer_graphics")
        for i, r in enumerate(result):
            images = result.media.get("images", [])
            print(f"Found {len(images)} imagees")

            internal_links = result.links.get("internal", [])
            print(f"Found {len(internal_links)} internal links")

            external_links = result.links.get("external", [])
            print(f"Found {len(external_links)} external links")

            with open("images.json", "w") as f:
                json.dump(images, f, indent=2)
            with open("links.json", "w") as f:
                json.dump(
                    {"internal": internal_links, "external": external_links},
                    f,
                    indent=2,
                )


async def demo_screenshot_and_pdf():
    """Capture screenshots and PDFs from a webpage"""
    print("\n=== 9. Capture screenshots and PDFs from a webpage ===")
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(
            "https://en.wikipedia.org/wiki/Giant_anteater",
            config=CrawlerRunConfig(
                screenshot=True,
                pdf=True,
            ),
        )
    cur_dir = os.getcwd()
    for i, r in enumerate(result):
        if result.screenshot:
            screenshot_path = f"{cur_dir}/tmp/example-screenshot-{i}.png"
            with open(screenshot_path, "wb") as f:
                f.write(base64.b64decode(result.screenshot))
            print(f"Screenshot saved to {screenshot_path}")
        if result.pdf:
            pdf_path = f"{cur_dir}/tmp/example-pdf-{i}.pdf"
            with open(pdf_path, "wb") as f:
                f.write(result.pdf)
                print(f"PDF saved to {pdf_path}")


async def demo_raw_html_and_file():
    """Process raw HTML and local files"""
    print("\n=== 11. Process raw HTML and local files ===")
    raw_html = """
    <html><body>
        <h1>Hello World</h1>
        <p>This is a paragraph.</p>
        <img src="https://example.com/image.png" alt="Example image" />
    </body></html>
    """
    file_path = Path(os.getcwd() + "/tmp/sample.html")
    with open(file_path, "w") as f:
        f.write(raw_html)

    async with AsyncWebCrawler() as crawler:
        raw_result = await crawler.arun(
            url="raw://" + raw_html,
            config=CrawlerRunConfig(cache_mode=CacheMode.BYPASS),
        )
        print(f"Success: {raw_result.success}")
        print("Raw HTML processing")
        print(f"  Markdown: {raw_result.markdown.raw_markdown[:50]}")
        print(file_path)
        file_result = await crawler.arun(
            url=f"file://{file_path}",
            config=CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS, capture_console_messages=True
            ),
        )
        print(f"Success: {file_result.success}")
        print("Local file processing")
        print(f"  Markdown: {file_result.markdown.raw_markdown[:50]}")

    os.remove(file_path)
    print(f"Processsed both raw HTML and local file ({file_path})")


def main():
    # asyncio.run(demo_basic_crawl())
    # asyncio.run(demo_parallel_crawl())
    # asyncio.run(demo_fit_markdown())
    # asyncio.run(demo_llm_structured_extraction_no_schema())
    # asyncio.run(demo_css_structured_extraction_schema())
    # asyncio.run(demo_media_and_links())
    # asyncio.run(demo_screenshot_and_pdf())
    # asyncio.run(demo_raw_html_and_file())
    asyncio.run(demo_deep_crawl())


if __name__ == "__main__":
    main()
