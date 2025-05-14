#!/usr/bin/env python3
"""
Generate a PDF guide from a YAML specification of prompts.

Usage:
    python main.py --input prompts.yaml --output result.pdf \
        [--model gpt-4.1-mini] [--toc-level 3] [--optimize] [--no-web-search] [--verbose]
"""

import argparse
import logging
from pathlib import Path
import os
import sys
from typing import Any, Dict, List, Union

import yaml
from dotenv import load_dotenv
from openai import OpenAI
from markdown_pdf import MarkdownPdf, Section

# Type alias for YAML data
YamlNode = Union[Dict[str, Any], List[Any], str]

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a PDF guide from a YAML specification of prompts."
    )
    parser.add_argument(
        "-i", "--input", default="prompts.yaml",
        help="Path to the input YAML file (default: prompts.yaml)",
    )
    parser.add_argument(
        "-o", "--output", default="result.pdf",
        help="Path to the output PDF file (default: result.pdf)",
    )
    parser.add_argument(
        "--model", default="gpt-4.1-mini",
        help="OpenAI model name to use (default: gpt-4.1-mini)",
    )
    parser.add_argument(
        "--toc-level", type=int, default=3,
        help="Table of contents depth level (default: 3)",
    )
    parser.add_argument(
        "-f", "--format",
        choices=["pdf", "md"],
        default="pdf",
        help="Output format: 'pdf' (default) or 'md'",
    )
    parser.add_argument(
        "--optimize", action="store_true",
        help="Optimize the PDF size",
    )
    parser.add_argument(
        "--no-web-search", action="store_false", dest="use_web_search",
        help="Disable web search in AI prompts",
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Enable verbose logging",
    )
    return parser.parse_args()

def setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        format="%(asctime)s %(levelname)s: %(message)s",
        level=level,
    )

def load_yaml_file(path: str) -> Dict[str, YamlNode]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception as e:
        logging.error("Failed to load YAML file %s: %s", path, e)
        sys.exit(1)

def generate_markdown_from_node(
    node: YamlNode,
    client: OpenAI,
    model: str,
    use_web_search: bool,
    depth: int = 1
) -> str:
    """
    Recursively convert a YAML node into Markdown, using AI for leaf strings.
    """
    lines: List[str] = []
    if isinstance(node, dict):
        for key, val in node.items():
            heading = "#" * (depth + 1) + f" {key}"
            lines.append(heading + "\n")
            lines.append(generate_markdown_from_node(val, client, model, use_web_search, depth + 1))
    elif isinstance(node, list):
        for item in node:
            lines.append(generate_markdown_from_node(item, client, model, use_web_search, depth))
    else:
        # Leaf node (string)
        try:
            prompt = [
                {"role": "system", "content": (
                    "You are a tutor preparing me to the SnowPro® Advanced: Data Engineer (DEA-C02) certification. "
                    "Provide output in Markdown. "
                    "Use **bold** for headers. "
                    "Don't add line separators in response. "
                )},
                {"role": "user", "content": node},
            ]
            tools = [{"type": "web_search_preview"}] if use_web_search else []
            response = client.responses.create(
                model=model,
                tools=tools,
                input=prompt,
            )
            text = f"Prompt: {node}\n\n" + response.output_text.strip()
            lines.append(text + "\n\n---\n\n")
        except Exception as e:
            logging.error("AI request failed for node '%s': %s", node, e)
            lines.append(node + "\n\n---\n\n")
    return "".join(lines)

def main() -> None:
    args = parse_args()
    setup_logging(args.verbose)
    load_dotenv()

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logging.error("Environment variable OPENAI_API_KEY is not set.")
        sys.exit(1)

    client = OpenAI(api_key=api_key)

    logging.info("Loading YAML from %s", args.input)
    data = load_yaml_file(args.input)

    total_sections = len(data)
    logging.info("Found %d top-level sections", total_sections)  # ← summary

    css = Path("src/custom.css").read_text(encoding="utf-8")

    # Generate content for each top-level section
    all_sections_md: List[str] = []
    for idx, (title, subtree) in enumerate(data.items(), start=1):
        logging.info("=== Starting section %d/%d: %s ===", idx, total_sections, title)
        section_md = f"# {title}\n\n"
        section_md += generate_markdown_from_node(
            subtree,
            client=client,
            model=args.model,
            use_web_search=args.use_web_search,
            depth=1
        )
        all_sections_md.append(section_md)
        logging.info("=== Completed section %d/%d: %s ===", idx, total_sections, title)

    if args.format == "md":
        # Dump raw Markdown
        out_path = args.output
        if not out_path.lower().endswith(".md"):
            out_path += ".md"
        logging.info("Saving Markdown to %s", out_path)
        try:
            with open(out_path, "w", encoding="utf-8") as f:
                f.write("\n\n---\n\n".join(all_sections_md))
            logging.info("Markdown written successfully.")
        except Exception as e:
            logging.error("Failed to save Markdown: %s", e)
            sys.exit(1)
    else:
        # Existing PDF flow
        pdf = MarkdownPdf(toc_level=args.toc_level, optimize=args.optimize)
        for section_md in all_sections_md:
            pdf.add_section(Section(section_md, toc=True), user_css=css)

        logging.info("Saving PDF to %s", args.output)
        try:
            pdf.save(args.output)
            logging.info("PDF successfully saved.")
        except Exception as e:
            logging.error("Failed to save PDF: %s", e)
            sys.exit(1)

if __name__ == "__main__":
    main()
