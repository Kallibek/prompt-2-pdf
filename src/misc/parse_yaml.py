import yaml

def load_yaml(path):
    with open(path, 'r') as f:
        return yaml.safe_load(f)

def print_md(node, depth=0):
    """
    depth=0  → top level  → H1
    depth=1  → second      → H2
    …
    leaf scalar → printed as plain text
    """
    if isinstance(node, dict):
        for key, val in node.items():
            # print the key as an H(depth+1)
            print(f"{'#' * (depth + 1)} {key}")
            # recurse into its value
            print_md(val, depth + 1)

    elif isinstance(node, list):
        for item in node:
            # list items have no key, so just recurse
            print_md(item, depth)

    else:
        # leaf scalar: just print it
        print(node)


if __name__ == "__main__":
    data = load_yaml("prompts copy.yaml")
    print_md(data)
