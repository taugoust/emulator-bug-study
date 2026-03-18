from requests import get, Response
from os import makedirs, path

def launchpad_id_valid(bug_id: str) -> bool:
    return bug_id.isdigit() and len(bug_id) > 0

def response_valid(response: Response) -> bool:
    return 'application/json' in response.headers.get('Content-Type', '')

def fetch_launchpad_bug(bug_id: str) -> dict | None:
    """Fetch a Launchpad bug and return it as a dict, or None on failure."""
    if not launchpad_id_valid(bug_id):
        print(f"{bug_id} is not valid")
        return None

    bug_url = f"https://api.launchpad.net/1.0/bugs/{bug_id}"
    bug_response = get(bug_url)

    if not response_valid(bug_response):
        print(f"Response for {bug_id} is not valid")
        return None

    bug_data = bug_response.json()
    messages_response = get(bug_data['messages_collection_link'])
    messages_data = messages_response.json()

    parts = [bug_data['title']] + [entry['content'] for entry in messages_data['entries']]
    content = "\n\n".join(parts)

    return {
        "id": bug_id,
        "source": "launchpad",
        "title": bug_data['title'],
        "content": content,
    }

def process_launchpad_bug(bug_id: str, output_dir: str = "output_launchpad") -> None:
    out_path = path.join(output_dir, bug_id)
    if path.exists(out_path):
        print(f"{out_path} exists already")
        return

    result = fetch_launchpad_bug(bug_id)
    if result is None:
        return

    makedirs(output_dir, exist_ok=True)
    with open(out_path, "w") as file:
        file.write(result["content"])
