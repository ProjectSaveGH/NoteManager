import os
import pyperclip

def dir_to_dict(root_path):
    """
    Return a mapping of each file's path (relative to root_path) to its UTF-8 contents.
    
    Walks the directory tree under `root_path` and builds a dict where keys are file paths relative to `root_path` and values are the file contents read with UTF-8. The `node_modules` directory is skipped. If a file cannot be read, its value is a string of the form "<<Error reading file: {exception}>>".
    
    Parameters:
        root_path (str): Root directory to walk.
    
    Returns:
        dict: Mapping from relative file path (str) to file contents or an error string (str).
    """
    file_dict = {}
    for root, dirs, files in os.walk(root_path):
        # node_modules skippen
        if "node_modules" in dirs:
            dirs.remove("node_modules")
        for file in files:
            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_path, root_path)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception as e:
                content = f"<<Error reading file: {e}>>"
            file_dict[rel_path] = content
    return file_dict

if __name__ == "__main__":
    project_root = "."  # aktuelles Verzeichnis
    data = dir_to_dict(project_root)

    # in Clipboard kopieren (als String)
    print(data)
    print("✅ Projektinhalt wurde ins Clipboard kopiert (ohne node_modules).")

