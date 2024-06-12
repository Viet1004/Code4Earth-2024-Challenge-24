import os
import shutil
import fitz
from Extractor import Extractor

if tuple(map(int, fitz.version[0].split("."))) < (1, 18, 18):
    raise SystemExit("require PyMuPDF v1.18.18+")

dimlimit = 0  # 100  # each image side must be greater than this
relsize = 0  # 0.05  # image : image size ratio must be larger than this (5%)
abssize = 0  # 2048  # absolute image size limit 2 KB: ignore if smaller
imgdir = "output"  # found images are stored in this subfolder


DOCS_DIRECTORY = "/home/user/large-disk/crawled_resources/"

output_subdirectory = {
    #    "memoranda": "technical_memoranda",
    "ERA": "ERA_Reports",
    #    "esa-eumetsat": "esa_eumetsat_contract_reports",
    "eumetsat-ecmwf": "eumetsat_ecmwf_fellowship_programme_research_reports",
    "report": "reports",
    # 'newsletter':"newsletter"
}

# output_subdirectory = {
#    "test": "test"
# }


def create_directories_and_move_files(output_subdirectory):
    """
    Create directories and move files into them based on the specified subdirectory mapping.

    Args:
        output_subdirectory (dict): Mapping of keys to subdirectory names.
    """
    for key, value in output_subdirectory.items():
        directory_folder = os.path.join(DOCS_DIRECTORY, value)
        files_and_dirs = os.listdir(directory_folder)
        files = [
            f
            for f in files_and_dirs
            if os.path.isfile(os.path.join(directory_folder, f))
        ]

        for file in files:
            file_path = os.path.join(directory_folder, file)
            directory_file = os.path.join(directory_folder, file[:-4])
            os.makedirs(directory_file, exist_ok=True)
            shutil.move(file_path, directory_file)


def process_directories(output_subdirectory, extractor):
    """
    Process directories to ensure each contains exactly one PDF file and extract content using the specified extractor.

    Args:
        output_subdirectory (dict): Mapping of keys to subdirectory names.
        extractor (object): Object with an `extract_file` method to process the PDFs.
    """
    for key, value in output_subdirectory.items():
        directory_folder = os.path.join(DOCS_DIRECTORY, value)
        files_and_dirs = os.listdir(directory_folder)
        dirs = [
            f
            for f in files_and_dirs
            if os.path.isdir(os.path.join(directory_folder, f))
        ]

        for directory in dirs:
            curr_dir = os.path.join(directory_folder, directory)
            print(curr_dir)
            pdf_files = get_pdf_files(curr_dir)

            if len(pdf_files) > 1:
                raise Exception("The number of PDFs in each folder should be 1!")

            full_file = os.path.join(curr_dir, pdf_files[0])
            extractor.extract_file(full_file, curr_dir)


def get_pdf_files(directory):
    """
    Get a list of PDF files in the specified directory.

    Args:
        directory (str): Path to the directory.

    Returns:
        list: List of PDF file names.
    """
    entries = os.listdir(directory)
    pdf_files = [
        f
        for f in entries
        if f.lower().endswith(".pdf") and os.path.isfile(os.path.join(directory, f))
    ]
    return pdf_files


def main():
    create_directories_and_move_files(output_subdirectory)
    process_directories(output_subdirectory, Extractor)


if __name__ == "__main__":
    main()
