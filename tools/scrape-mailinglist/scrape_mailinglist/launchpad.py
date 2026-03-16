from requests import get, Response
from os import makedirs, path

def launchpad_id_valid(bug_id : str) -> bool:
    return len(bug_id) == 7 or len(bug_id) == 6

def response_valid(response : Response) -> bool:
    return 'application/json' in response.headers.get('Content-Type', '')

def process_launchpad_bug(bug_id : str, output_dir : str = "output_launchpad") -> None:
    if not launchpad_id_valid(bug_id):
        print(f"{bug_id} is not valid")
        return

    out_path = path.join(output_dir, bug_id)
    if path.exists(out_path):
        print(f"{out_path} exists already")
        return

    bug_url = f"https://api.launchpad.net/1.0/bugs/{bug_id}"
    bug_response = get(bug_url)

    if not response_valid(bug_response):
        print(f"Response for {bug_id} is not valid")
        return

    bug_data = bug_response.json()
    messages_response = get(bug_data['messages_collection_link'])
    messages_data = messages_response.json()

    makedirs(output_dir, exist_ok = True)
    with open(out_path, "w") as file:
        file.write(f"{bug_data['title']}\n\n")
        for entry in messages_data['entries']:
            file.write(f"{entry['content']}\n\n")
