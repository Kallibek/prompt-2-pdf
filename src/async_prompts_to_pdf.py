# %% [markdown]
# # Imports and environment

# %%
import os
import sys
import re
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from markdown_pdf import MarkdownPdf, Section

# Optional: for Word/EPUB output
import pypandoc

# Load environment variables (e.g. OPENAI_API_KEY)
load_dotenv()

# %% [markdown]
# # User‐configurable variables

# %%
# List of input prompt files (change as needed)
prompts_filenames      = [
    r"prompts\chief_data_ai_officer_prompts.txt",
    # add more prompt files here...
]

# Desired output format: "pdf", "docx", or "epub"
output_format          = "docx"

# Model and other settings
model                  = "gpt-5-mini"
toc_level              = 3
optimize               = False
use_web_search         = False
max_output_tokens      = 2000
max_concurrent_requests= 20   # concurrency for async calls

# %% [markdown]
# # Helper function definitions

# %%
def extract_system_prompt_and_body(text):
    """
    Extract an OPTIONAL additional system prompt from `text`, supporting two formats:
      1) Fenced block:
            ```system
            ...system text...
            ```

    Returns: (system_prompt_or_None, remaining_text_without_block)
    """
    # Try fenced ```system ... ``` first
    fenced_pattern = re.compile(
        r"```system\s*(.*?)```",
        re.DOTALL | re.IGNORECASE
    )
    m = fenced_pattern.search(text)
    if m:
        sys_prompt = m.group(1).strip()
        remaining = text[:m.start()] + text[m.end():]
        return (sys_prompt, remaining)

    # None found
    return (None, text)

def generate_markdown_from_prompt(user_prompt, client, extra_system_prompt=None):
    """
    Synchronous call to OpenAI – returns a Markdown snippet.
    If extra_system_prompt is provided, it is *added* as an additional system message
    after the hard-coded system prompt.
    """
    try:
        base_system = (
            "Provide output in Markdown. "
            "Use **bold** text for headers and no need for h1, h2, h3 headers. "
            "Don't add line separators in response. "
            f"Aim at about {max_output_tokens} tokens."
        )

        prompt = [
            {"role": "system", "content": base_system},
        ]

        # If the file provided additional system instructions, add them here
        if extra_system_prompt:
            prompt.append({"role": "system", "content": extra_system_prompt})

        prompt.append({"role": "user", "content": user_prompt + "\n\n"})

        tools = [{"type": "web_search_preview"}] if use_web_search else []
        response = client.responses.create(
            model=model,
            tools=tools,
            input=prompt
        )
        separator = "\n\n===========================\n\n"
        text = f"{separator}**Prompt:** {user_prompt}\n\n" + response.output_text.strip()
        return text
    except Exception as e:
        print(f"AI request failed for prompt '{user_prompt}': {e}")
        return f"**Prompt:** {user_prompt}\n\n*Error generating content.*"

async def process_prompts_to_markdown(prompts_text, client, concurrency, dry_run=False, extra_system_prompt=None):
    """
    Turn each non-blank line of prompts_text into either:
      - header lines (starting "#"), passed through
      - AI-generated Markdown for each other line
    Returns the full concatenated Markdown document.
    """
    lines = [ln for ln in prompts_text.splitlines() if ln.strip()]
    total = len(lines)
    semaphore = asyncio.Semaphore(concurrency)

    async def fetch_markdown(stripped, idx):
        if stripped.startswith("#"):
            return stripped
        async with semaphore:
            if dry_run:
                return f"**Prompt:** {stripped}\n\n_test placeholder_\n"
            print(f"Processing AI call {idx}/{total}…")
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(
                None,
                generate_markdown_from_prompt,
                stripped,
                client,
                extra_system_prompt
            )

    tasks = [
        asyncio.create_task(fetch_markdown(line.lstrip(), idx))
        for idx, line in enumerate(lines, start=1)
    ]
    pieces = await asyncio.gather(*tasks)
    return "\n\n".join(pieces)

# %% [markdown]
# # Main

# %%
async def main():
    css = Path("src/custom.css").read_text(encoding="utf-8")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Environment variable OPENAI_API_KEY is not set.")
        sys.exit(1)

    client = OpenAI(api_key=api_key)
    output_dir = Path("results")
    output_dir.mkdir(parents=True, exist_ok=True)

    for prompts_filename in prompts_filenames:
        # Derive paths based on each prompt file
        prompt_path = Path(prompts_filename)
        stem = prompt_path.stem
        output_file = output_dir / f"{stem}.{output_format}"

        # Read prompts
        try:
            with open(prompts_filename, "r", encoding="utf-8") as f:
                full_text = f.read()
        except FileNotFoundError:
            print(f"❌  Prompt file not found: {prompts_filename}")
            continue

        # ⬇️ NEW: Extract optional per-file system prompt
        extra_system_prompt, chatgpt_prompts = extract_system_prompt_and_body(full_text)

        print(f"\n🚧  Starting dry run for '{prompts_filename}'…")
        markdown_dry = await process_prompts_to_markdown(
            chatgpt_prompts, client,
            concurrency=max_concurrent_requests,
            dry_run=True,
            extra_system_prompt=extra_system_prompt
        )
        # Write and delete a tiny sample to verify
        dry_sample = output_dir / f"{stem}_dry.md"
        with open(dry_sample, "w", encoding="utf-8") as f:
            f.write(markdown_dry[:2000])
        print(f"✔️  Dry-run Markdown sample saved to {dry_sample}")
        dry_sample.unlink()
        print(f"🗑️  Deleted dry-run sample")

        print(f"✅  Dry run complete for '{prompts_filename}' — generating real content…")
        full_markdown = await process_prompts_to_markdown(
            chatgpt_prompts, client,
            concurrency=max_concurrent_requests,
            dry_run=False,
            extra_system_prompt=extra_system_prompt
        )

        # Convert and save in the desired format
        if output_format == "pdf":
            pdf = MarkdownPdf(toc_level=toc_level, optimize=optimize)
            pdf.add_section(Section(full_markdown), user_css=css)
            try:
                pdf.save(str(output_file))
                print(f"🎉  Final PDF saved to {output_file}")
            except Exception as e:
                print(f"❌  Failed to save PDF for '{stem}': {e}")
                continue

        elif output_format in ("docx", "epub"):
            try:
                pypandoc.convert_text(
                    full_markdown,
                    to=output_format,
                    format="md",
                    outputfile=str(output_file)
                )
                print(f"🎉  Final {output_format.upper()} saved to {output_file}")
            except Exception as e:
                print(f"❌  Failed to generate {output_format.upper()} for '{stem}': {e}")
                continue

        else:
            print(f"❌  Unknown output_format '{output_format}'. Choose 'pdf', 'docx', or 'epub'.")
            sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
