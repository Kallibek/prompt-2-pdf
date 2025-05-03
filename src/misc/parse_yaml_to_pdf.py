import yaml
from markdown_pdf import MarkdownPdf, Section

def load_yaml(path):
    with open(path, 'r') as f:
        return yaml.safe_load(f)

def build_markdown(node, depth=1):
    """
    depth=1 → H2    (since H1 is already printed by outer loop)
    depth=2 → H3
    …
    leaf scalar → plain text
    """
    md = []
    if isinstance(node, dict):
        for key, val in node.items():
            # print deeper headings as ##, ###, etc.
            md.append(f"{'#' * (depth + 1)} {key}\n")
            md.append(build_markdown(val, depth + 1))
    elif isinstance(node, list):
        for item in node:
            md.append(build_markdown(item, depth))
    else:
        # leaf: just the value
        md.append(f"{node}\n\n---\n\n")
    return "\n".join(md)

if __name__ == "__main__":
    pdf = MarkdownPdf(toc_level=3, optimize=True)
    data = load_yaml("prompts copy.yaml")

    # For each top-level key (H1), we open a new Section/page.
    for top_key, subtree in data.items():
        # 1) Start with the H1 heading
        section_md = f"# {top_key}\n\n"
        # 2) Append everything below it in one blob
        section_md += build_markdown(subtree, depth=1)
        # 3) Add exactly one Section → one page break before it
        pdf.add_section(Section(section_md, toc=True))

    pdf.save("guide.pdf")
