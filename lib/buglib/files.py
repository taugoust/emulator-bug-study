"""File output helpers and recursive file listing."""

from os import path, listdir, makedirs


def write_file(file_path: str, string: str) -> None:
    """Write *string* to *file_path*, creating parent directories as needed."""
    makedirs(path.dirname(file_path), exist_ok=True)
    with open(file_path, "w") as file:
        file.write(string)


def list_files_recursive(directory: str, basename: bool = False) -> list[str]:
    """Return all file paths under *directory*, recursively.

    If *basename* is ``True`` only the file name (no directory component) is
    returned for each entry.  Returns an empty list when *directory* does not
    exist.
    """
    result: list[str] = []
    if not path.isdir(directory):
        return result
    for entry in listdir(directory):
        full_path = path.join(directory, entry)
        if path.isdir(full_path):
            result.extend(list_files_recursive(full_path, basename))
        else:
            if basename:
                result.append(path.basename(full_path))
            else:
                result.append(full_path)
    return result
