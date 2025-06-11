import os
import uuid

PDF_DIRECTORY = "_data/pdfs"

def rename_pdfs_to_uuid(directory):
    """
    Renames all files in the specified directory to a random UUID,
    preserving the .pdf extension.
    """
    print(f"Scanning for files in '{directory}' to rename...")
    renamed_count = 0
    skipped_count = 0

    for filename in os.listdir(directory):
        original_file_path = os.path.join(directory, filename)

        if os.path.isfile(original_file_path) and filename.lower().endswith(".pdf"):
            new_filename = f"{uuid.uuid4()}.pdf"
            new_file_path = os.path.join(directory, new_filename)

            while os.path.exists(new_file_path):
                new_filename = f"{uuid.uuid4()}.pdf"
                new_file_path = os.path.join(directory, new_filename)

            try:
                os.rename(original_file_path, new_file_path)
                print(f"Renamed '{filename}' to '{new_filename}'")
                renamed_count += 1
            except OSError as e:
                print(f"Error renaming '{filename}': {e}")
                skipped_count += 1
        elif os.path.isfile(original_file_path):
            print(f"Skipping '{filename}' as it does not end with .pdf")
            skipped_count += 1

    print(f"\nRenaming process complete.")
    print(f"Successfully renamed: {renamed_count} files.")
    print(f"Skipped: {skipped_count} files.")

if __name__ == "__main__":
    if not os.path.isdir(PDF_DIRECTORY):
        print(f"Error: Directory '{PDF_DIRECTORY}' not found.")
        print("Please create it or update the PDF_DIRECTORY variable in the script.")
    else:
        confirm = input(f"Are you sure you want to rename all .pdf files in '{PDF_DIRECTORY}' to UUIDs? (yes/no): ")
        if confirm.lower() == 'yes':
            rename_pdfs_to_uuid(PDF_DIRECTORY)
        else:
            print("Operation cancelled by the user.")
