# %% [markdown]
# # Imports and environment

# %%
import os
import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from markdown_pdf import MarkdownPdf, Section

# Load environment variables (e.g. OPENAI_API_KEY)
load_dotenv()

# %% [markdown]
# # User‐configurable variables

# %%
model                     = "gpt-4.1-mini"
toc_level                 = 3
optimize                  = False
use_web_search            = True
max_output_tokens         = 2000
prompts_filename          = r"prompts\personal_development_dialog_prompts.txt"
output_file               = r"results\personal_development_dialog_prompts.pdf"
test_output_file          = output_file
max_concurrent_requests   = 20   # default concurrency

# %% [markdown]
# # Helper function definitions

# %%
def generate_markdown_from_prompt(user_prompt, client):
    """
    Synchronous call to OpenAI – returns a Markdown section.
    """
    try:
        prompt = [
            {"role": "system", "content":
                "Provide output in Markdown. "
                "Use **bold** text for headers and no need for h1, h2, h3 headers. "
                "Don't add line separators in response. "
                # "No need for diagrams. "
                f"Aim at about {max_output_tokens} token-output."
            },
            {"role": "user", "content": user_prompt + "\n\n"},
        ]
        tools = [{"type": "web_search_preview"}] if use_web_search else []
        response = client.responses.create(
            model=model,
            tools=tools,
            input=prompt,
            max_output_tokens=max_output_tokens
        )
        text = f"Prompt: {user_prompt}\n\n" + response.output_text.strip()
        return f"\n---\n=========================\n\n{text}"
    except Exception as e:
        print(f"AI request failed for prompt '{user_prompt}': {e}")
        return f"{user_prompt}\n\n---\n\n"

async def process_prompts_async(prompts_text, client, pdf, css, concurrency, dry_run=False):
    """
    Splits prompts into lines, then for each non-header line runs
    either a dummy 'test' or an async-openai call (via run_in_executor),
    limited by an asyncio.Semaphore.
    Prints progress before each real OpenAI call.
    Finally, adds each piece of markdown to the PDF.
    """
    lines = [ln for ln in prompts_text.splitlines() if ln.strip()]
    total = len(lines)
    semaphore = asyncio.Semaphore(concurrency)

    async def fetch_markdown(stripped, idx):
        if stripped.startswith("#"):
            return stripped
        async with semaphore:
            if dry_run:
                return "test"
            print(f"Processing AI call {idx}/{total}…")
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(
                None,
                generate_markdown_from_prompt,
                stripped,
                client
            )

    tasks = [
        asyncio.create_task(fetch_markdown(line.lstrip(), idx))
        for idx, line in enumerate(lines, start=1)
    ]
    results = await asyncio.gather(*tasks)

    section_md = ""
    for idx, (line, md) in enumerate(zip(lines, results), start=1):
        stripped = line.lstrip()
        if stripped.startswith("#"):
            section_md = f"{section_md}\n\n{stripped}"
        else:
            print(f"Adding section {idx}/{total} to PDF…")
            section_md += f"\n\n{md}\n\n"
            pdf.add_section(Section(section_md), user_css=css)
            section_md = ""

# %% [markdown]
# # Prompts

# %%
with open(prompts_filename, "r", encoding="utf-8") as f:
    chatgpt_prompts = f.read()

print(chatgpt_prompts[:400])  # Optional preview

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

    # 1) Dry run
    print("🚧  Starting dry run with 'test' placeholders…")
    pdf_test = MarkdownPdf(toc_level=toc_level, optimize=optimize)
    await process_prompts_async(
        chatgpt_prompts, client, pdf_test, css,
        concurrency=max_concurrent_requests,
        dry_run=True
    )
    try:
        pdf_test.save(test_output_file)
        print(f"✔️  Dry-run PDF saved to {test_output_file}")
        # Delete the test file now that it was created successfully
        os.remove(test_output_file)
        print(f"🗑️  Deleted test file: {test_output_file}")
    except Exception as e:
        print(f"❌  Dry run failed: {e}")
        sys.exit(1)

    # 2) Real run
    print("✅  Dry run successful — now running real generation…")
    pdf = MarkdownPdf(toc_level=toc_level, optimize=optimize)
    await process_prompts_async(
        chatgpt_prompts, client, pdf, css,
        concurrency=max_concurrent_requests,
        dry_run=False
    )
    try:
        pdf.save(output_file)
        print(f"🎉  Final PDF successfully saved to {output_file}")
    except Exception as e:
        print(f"❌  Failed to save final PDF: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
