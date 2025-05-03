# PDF Guide Generator using LLM

A simple command-line tool that reads a YAML specification of prompts, uses OpenAI’s API to generate Markdown content for each prompt, and bundles everything into a styled PDF guide.

---

## Table of Contents

- [Features](#features)  
- [Prerequisites](#prerequisites)  
- [Installation](#installation)  
- [Configuration](#configuration)  
- [Usage](#usage)  
- [Project Structure](#project-structure)  
- [prompts.yaml Format](#promptsyaml-format)  
- [Output](#output)  
- [Requirements](#requirements)  
- [License](#license)  

---

## Features

- Load a tree of prompts from a YAML file  
- For each leaf prompt, call the OpenAI API to generate concise Markdown  
- Automatically assemble a table of contents  
- Export a clean, paginated PDF  
- Options to adjust model, toc depth, PDF optimization, and web-search usage  
- Verbose logging for debugging  

---

## Prerequisites

- Python 3.8+  
- An OpenAI API key (see [Configuration](#configuration))  

---

## Installation

1. Clone the repo:  
    ```bash
    git clone https://github.com/your-username/pdf-guide-generator.git
    cd pdf-guide-generator
    ```

2. Create a virtual environment and activate it:

   ```bash
   python3 -m venv venv
   source venv/bin/activate   # Unix/macOS
   venv\Scripts\activate      # Windows
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

---

## Configuration

Create a `.env` file in the project root containing your OpenAI API key:

```dotenv
OPENAI_API_KEY=sk-your-actual-key-here
```

The script uses `python-dotenv` to load this key at runtime.

---

## Usage

```bash
python src/main.py \
  --input prompts.yaml \
  --output result.pdf \
  [--model gpt-4o-mini] \
  [--toc-level 3] \
  [--optimize] \
  [--no-web-search] \
  [--verbose]
```

* `-i, --input`  Path to YAML file of prompts (default: `prompts.yaml`)
* `-o, --output`  Path to write the PDF (default: `result.pdf`)
* `--model`  OpenAI model to use (default: `gpt-4o-mini`)
* `--toc-level`  Depth of headings in the table of contents (default: `3`)
* `--optimize`  Minify and optimize the PDF size
* `--no-web-search`  Disable web-search tool in AI prompts
* `--verbose`  Enable DEBUG-level logging

Example:

```bash
python src/main.py -i prompts.yaml -o my-guide.pdf --model gpt-4o-mini --optimize --verbose
```

---

## Project Structure

```
.
├── src/
│   └── main.py       # Core script that drives PDF generation
├── prompts.yaml      # YAML spec of domains, sections, and prompt texts
├── result.pdf        # Example/generated PDF output
├── .env              # Environment file with OPENAI_API_KEY
└── requirements.txt  # Python dependencies
```

---

## `prompts.yaml` Format

The YAML file defines a nested mapping of domains, section titles, and a list of prompt strings.
Example:

```yaml
Domain 1:
  "Network Connectivity Strategies":
    - "Explain the differences between AWS Direct Connect, AWS VPN, and Transit Gateway in large-scale, multi-region architectures."
Domain 2:
  "Compute & Serverless Architectures":
    - "Compare EC2 Auto Scaling with Lambda provisioning in unpredictable traffic patterns."
```

* Top-level keys (e.g. `Domain 1`) become H1 sections.
* Second-level keys (e.g. `Network Connectivity Strategies`) become H2 headings.
* Each array item is a prompt sent to the AI, whose Markdown response is captured and inserted.

---

## Output

* **result.pdf** (or your chosen output file)
* Includes a clickable Table of Contents and each AI-generated section styled in Markdown.

---

## Requirements

All dependencies are listed in `requirements.txt`. Install them via:

```bash
pip install -r requirements.txt
```

Typical entries include:

* `PyYAML`
* `python-dotenv`
* `openai`
* `markdown-pdf`