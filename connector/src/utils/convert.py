import subprocess
import os

def convert_to_pdf_soffice(file_path):
    """
    Convert a DOC or DOCX file to PDF using soffice (LibreOffice).
    :param file_path: Path to the input DOC or DOCX file.
    :return: Path to the converted PDF file.
    """

    # Check if soffice is installed
    # try:
    #     subprocess.run(["soffice", "--version", " --headless"], check=True, stdout=subprocess.PIPE)
    # except subprocess.CalledProcessError:
    #     raise EnvironmentError("soffice (LibreOffice) is not installed or not found in PATH.")

    # Check if the file exists
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"The file {file_path} was not found.")

    # Define the output file path
    output_file = os.path.splitext(file_path)[0] + ".pdf"
    if not os.path.exists(output_file):
        try:
            subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir",
                            os.path.dirname(output_file), file_path], check=True)
        except subprocess.CalledProcessError as e:
            raise Exception(f"Error in conversion: {e}")

        # Check if conversion was successful
        if not os.path.exists(output_file):
            raise Exception("Failed to convert the document to PDF.")

    return output_file
