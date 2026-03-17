from buglib import write_file


def output_issue(issue: dict, output_dir: str = "issues") -> None:
    try:
        if 'documentation' in issue['labels']:
            write_file(f"{output_dir}/documentation/{issue['id']}", issue['title'] + '\n' + (issue['description'] or ""))
        else:
            write_file(f"{output_dir}/{issue['id']}", issue['title'] + '\n' + (issue['description'] or ""))
    except TypeError:
        print(f"error with bug {issue['id']}")
        exit()
