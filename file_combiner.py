import os
import argparse
import time
from pathlib import Path


def combine_files(
    directory_path,
    output_file,
    exclude_folders=None,
    include_extensions=None,
    exclude_extensions=None,
):
    """
    Iterate through all files in a directory and combine them into a single file.

    Args:
        directory_path (str): Path to the directory to scan
        output_file (str): Path to the output file
        exclude_folders (list): List of folder names to exclude
        include_extensions (list): List of file extensions to include (e.g., ['.txt', '.py'])
        exclude_extensions (list): List of file extensions to exclude
    """
    # Record start time
    start_time = time.time()

    exclude_folders = exclude_folders or []
    include_extensions = include_extensions or []
    exclude_extensions = exclude_extensions or []

    # Convert paths to absolute paths
    directory_path = os.path.abspath(directory_path)
    output_file = os.path.abspath(output_file)

    # Create output file or clear it if it exists
    with open(output_file, "w", encoding="utf-8") as outfile:
        outfile.write("")  # Clear the file

    print(f"Starting to scan directory: {directory_path}")

    # Walk through the directory
    file_count = 0
    with open(output_file, "a", encoding="utf-8") as outfile:
        for root, dirs, files in os.walk(directory_path):
            # Remove excluded folders from dirs to prevent walking into them
            dirs[:] = [d for d in dirs if d not in exclude_folders]

            for file in files:
                file_path = os.path.join(root, file)
                file_extension = os.path.splitext(file)[1].lower()

                # Skip the output file itself
                if os.path.abspath(file_path) == output_file:
                    continue

                # Check if file should be included based on extensions
                if include_extensions and file_extension not in include_extensions:
                    continue
                if exclude_extensions and file_extension in exclude_extensions:
                    continue

                try:
                    # Get relative path from the directory
                    relative_path = os.path.relpath(file_path, directory_path)

                    # Write file header
                    outfile.write(f"# {relative_path}\n")

                    # Write file contents
                    try:
                        with open(file_path, "r", encoding="utf-8") as infile:
                            content = infile.read()
                            outfile.write(content)
                    except UnicodeDecodeError:
                        # Try with different encodings if UTF-8 fails
                        try:
                            with open(file_path, "r", encoding="latin-1") as infile:
                                content = infile.read()
                                outfile.write(content)
                        except Exception as e:
                            outfile.write(f"[Error reading file: {str(e)}]\n")

                    # Add a blank line after each file
                    outfile.write("\n\n")
                    file_count += 1
                    print(f"Added: {relative_path}")

                except Exception as e:
                    print(f"Error processing {file_path}: {str(e)}")

    # Calculate elapsed time
    end_time = time.time()
    elapsed_time = end_time - start_time

    # Format the elapsed time
    if elapsed_time < 1:
        time_str = f"{elapsed_time:.3f}s"
    else:
        time_str = f"{elapsed_time:.1f}s"

    print(f"\nCompleted in {time_str}! Combined {file_count} files into {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Combine multiple files into a single text file."
    )
    parser.add_argument("directory", help="Directory to scan for files")
    parser.add_argument("output", help="Output file path")
    parser.add_argument("--exclude-folders", nargs="+", help="Folders to exclude")
    parser.add_argument(
        "--include-extensions",
        nargs="+",
        help="File extensions to include (e.g., .txt .py)",
    )
    parser.add_argument(
        "--exclude-extensions", nargs="+", help="File extensions to exclude"
    )

    args = parser.parse_args()

    combine_files(
        args.directory,
        args.output,
        exclude_folders=args.exclude_folders,
        include_extensions=args.include_extensions,
        exclude_extensions=args.exclude_extensions,
    )


if __name__ == "__main__":
    main()
