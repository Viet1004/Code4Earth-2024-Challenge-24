import os
import shutil
import re
import fitz


# import camelot

# A large part of this code is adapted from
# https://github.com/pymupdf/PyMuPDF-Utilities/blob/master/examples/extract-images/extract-from-pages.py

print(fitz.__doc__)

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


def extract_file(file_name, save_dir):
    """
    Input:
        file_name: pdf file
        save_dir: directory for saving the results
    Output:
        None

    The function takes a pdf file and create and organize a folder containing:
        pdf file,
        extracted texts in each page, whole content of the pdf file, clean content after removing table and figure in the text (in \texts),
        table descriptions (in \tables),
        and image descriptions (in \images).
    """
    doc = fitz.open(file_name)
    #    tables = camelot.read_pdf(file_name)

    text_dir = os.path.join(save_dir, "texts")
    os.makedirs(text_dir, exist_ok=True)

    image_dir = os.path.join(save_dir, "images")
    os.makedirs(image_dir, exist_ok=True)

    table_dir = os.path.join(save_dir, "tables")
    os.makedirs(table_dir, exist_ok=True)

    figure_pattern = re.compile(r"^Figure \d+:")
    table_pattern = re.compile(r"^Table \d+:")
    figure_descriptions = []
    table_descriptions = []
    whole_content = []
    for pageNumber, page in enumerate(doc.pages(), start=1):
        # extract texts from here
        text = page.get_text()
        report_indicator = re.compile(r"[Rr]esearch\s+[Rr]eport\s+[Nn]o\.")
        if report_indicator.match(text.split("\n")[0]):
            text_list = text.split("\n")[1:-3]
        else:
            text_list = text.split("\n")
        text = "\n".join(text_list)
        with open(os.path.join(text_dir, f"output_{pageNumber}.txt"), "w") as out:
            out.write(text)  # write text of page into a file

            whole_content.append(
                text
            )  # add text to a list of text presenting of each page
            # out.write(bytes((12,)))  # write page delimiter (form feed 0x0C)

        # extract images from here
        page = doc[pageNumber - 1]  # get the page
        image_list = page.get_images()

        # print the number of images found on the page
        if image_list:
            print(f"Found {len(image_list)} images on page {pageNumber}")
        else:
            print("No images found on page", pageNumber)

        for image_index, img in enumerate(
            image_list, start=1
        ):  # enumerate the image list
            xref = img[0]  # get the XREF of the image
            pix = fitz.Pixmap(doc, xref)  # create a Pixmap

            if pix.n - pix.alpha > 3:  # CMYK: convert to RGB first
                pix = fitz.Pixmap(fitz.csRGB, pix)
            try:
                pix.save(
                    os.path.join(
                        image_dir, "page_%s-image_%s.png" % (pageNumber, image_index)
                    )
                )  # save the image as png
            except Exception:
                continue
            pix = None

    whole_content = "\n".join(whole_content)
    with open(os.path.join(text_dir, "content.txt"), "w") as file:
        file.write(whole_content)

    # The next part is to remove the text extracted from tables and figures since they are unstructured without a proper format.
    # The idea is to detect the text that not belong to the table
    # For example, the description of figure and table stop at ".\n"
    # The figure descriptions start below the figure and the table descriptions start above the table itself
    # The step to remove the extracted text from figure:
    # Detect "Figure x:"
    # Remove the text above it until reach the line stop at ".\n" or have many words
    # Add text from "Figure x:" until the end of description (until reach .\n"")
    # The step to remove the extracted text from table:
    # Detect "Table x:"
    # Add text from "Figure x:" until the end of description (until reach .\n"")
    # Remove the text below it until reach the line stop at ".\n" or have many words

    with open(os.path.join(text_dir, "content.txt"), "r") as file:
        lines = file.readlines()
        clean_lines = []
        figure_descriptions = []
        table_descriptions = []
        figure_pattern = re.compile(
            r"^Figure \d+:"
        )  # This signifies the start of a figure
        table_pattern = re.compile(
            r"^Table \d+:"
        )  # This signifies the start of a table
        num_lines = len(lines)
        curr_line = 0
        while curr_line < num_lines:
            line = lines[curr_line]
            if figure_pattern.match(line):
                while True:
                    inloop_line = clean_lines.pop()  # if detecting figure description, remove the text above until reach ".\n" or if there are many words in the sentence. We select number 7 empirically
                    if inloop_line.endswith(".\n") or len(inloop_line.split()) > 7:
                        clean_lines.append(inloop_line)
                        break
                description_range = 0
                while (
                    description_range < 10 and curr_line + description_range < num_lines
                ):  # We add number 10 for safeguard so this don't run forever if the second condition doesn't match
                    inloop_line = lines[curr_line + description_range]

                    description_range += 1  # description_range is the position from the start of a figure description
                    clean_lines.append(inloop_line)
                    if inloop_line.endswith(
                        ".\n"
                    ):  # if a line reach ".\n" it means that it reach the end of description
                        description = " ".join(
                            [
                                line.rstrip("\n")
                                for line in lines[
                                    curr_line : curr_line + description_range
                                ]
                            ]
                        )  # concatenate the desciption
                        figure_descriptions.append(description)
                        clean_lines = (
                            clean_lines
                            + lines[curr_line : curr_line + description_range]
                        )

                        break
                curr_line = (
                    curr_line + description_range
                )  # jump the line to the text after the figure
            elif table_pattern.match(line):
                description_range = 0
                while (
                    description_range < 10 and curr_line + description_range < num_lines
                ):  # We add number 10 for safeguard so this don't run forever if the second condition doesn't match
                    inloop_line = lines[curr_line + description_range]
                    description_range += 1
                    if description_range == 9:
                        print("Potentially error!")
                    clean_lines.append(inloop_line)
                    if inloop_line.endswith(".\n"):
                        description = " ".join(
                            [
                                line.rstrip("\n")
                                for line in lines[
                                    curr_line : curr_line + description_range
                                ]
                            ]
                        )
                        table_descriptions.append(description)
                        clean_lines = (
                            clean_lines
                            + lines[curr_line : curr_line + description_range]
                        )
                        break
                curr_line = curr_line + description_range
                while (
                    curr_line < num_lines
                ):  # skip all the line until reach the the condition below
                    inloop_line = lines[curr_line]
                    if (
                        len(inloop_line.split()) > 9 or inloop_line.endswith(".\n")
                    ):  # If a sentence have more than 9 words, it has high probability of not belonging to a table. If it ends with ".\n", same.
                        break
                    curr_line += 1  # skip the lines from table
            else:
                clean_lines.append(line)
                curr_line += 1
        clean_text = "".join(clean_lines)
        with open(os.path.join(image_dir, "figure_descriptions.txt"), "w") as file:
            file.write("\n".join(figure_descriptions))
        with open(os.path.join(table_dir, "table_descriptions.txt"), "w") as file:
            file.write("\n".join(table_descriptions))
        with open(os.path.join(text_dir, "clean_content.txt"), "w") as file:
            file.write(clean_text)


### The following block move all pdf into a folder with the same name


def organize_file():
    for key, value in output_subdirectory.items():
        directory_folder = DOCS_DIRECTORY + value
        files_and_dirs = os.listdir(DOCS_DIRECTORY + value)
        files = [
            f
            for f in files_and_dirs
            if os.path.isfile(os.path.join(directory_folder, f))
        ]
        for file in files:
            file = os.path.join(directory_folder, file)
            directory_file = os.path.join(directory_folder, file[:-4])
            os.makedirs(directory_file, exist_ok=True)
            shutil.move(file, directory_file)


### The following block extract the pdf inside the folder into three dir: texts, images, tables

for key, value in output_subdirectory.items():
    directory_folder = DOCS_DIRECTORY + value
    files_and_dirs = os.listdir(DOCS_DIRECTORY + value)
    dirs = [
        f for f in files_and_dirs if os.path.isdir(os.path.join(directory_folder, f))
    ]
    for directory in dirs:
        curr_dir = os.path.join(directory_folder, directory)
        print(curr_dir)
        entries = os.listdir(curr_dir)
        pdf_files = [
            f
            for f in entries
            if f.lower().endswith(".pdf") and os.path.isfile(os.path.join(curr_dir, f))
        ]
        if len(pdf_files) > 1:
            raise Exception("The number of pdf in each folder should be 1!")
        file = pdf_files[0]
        full_file = os.path.join(curr_dir, file)
        extract_file(full_file, curr_dir)
