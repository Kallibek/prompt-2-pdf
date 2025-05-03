import os
import yaml
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from .env in project root
load_dotenv()

# 1. Configure API key
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 2. Load prompts
with open("prompts.yaml") as f:
    data = yaml.safe_load(f)

# 3. Prepare a Markdown accumulator
all_md = []

# 4. Loop through each domain/topic/prompt
for domain, topics in data.items():
    all_md.append(f"\n\n# {domain}\n")
    for topic, prompts in topics.items():
        all_md.append(f"\n## {topic}\n")
        for i, user_prompt in enumerate(prompts, start=1):
            # 4a. Build message sequence
            messages = [
                {"role": "system",
                 "content": (
                     #"You are a concise assistant. "
                     #"Respond in Markdown. "
                     "Use **bold** for all headers (e.g. **Header**). "
                 )
                },
                {"role": "user", "content": user_prompt}
            ]
            # 4b. Call ChatCompletion
            # response = client.chat.completions.create(
            #     model="gpt-4o-mini",
            #     messages=messages,
            # )
            
            response = client.responses.create(
                model="gpt-4o-mini",
                tools=[{"type": "web_search_preview"}],
                input=messages
            )
            
            # md = response.choices[0].message.content
            md = response.output_text
            # 4c. Append numbered response
            all_md.append(f"\n### {i}. {user_prompt} ###\n\n{md}\n\n---")

# 5. Write out a single Markdown file
md_content = "\n".join(all_md)
with open("output.md", "w") as f:
    f.write(md_content)