import os
import pandas as pd
from scidownl import scihub_download
import pymupdf
import csv
import fitz
import pytesseract
from PIL import Image
import google.generativeai as genai
import time
from shutil import rmtree

open("main.csv", "w").close()
class DataUtils:

    def __init__(self, df):
        rmtree("pdfs")
        self.pdf_output_dir = "./pdfs"
        self.proxies = {
            'http': 'socks5://127.0.0.1:7890'
        }
        if not os.path.exists("data"):
            os.mkdir("data")
        self.log_file = "./data/data_logs.csv"
        self.df = df

        genai.configure(api_key="AIzaSyA5mNf4-R9QtlGvJq4NQT0nBuIFDPH_pUk")

        self.generation_config = {
            "temperature": 1,
            "top_p": 0.95,
            "top_k": 64,
            "max_output_tokens": 1000000,
            "response_mime_type": "text/plain",
        }

        self.model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            generation_config=self.generation_config,
        )

    def cleanData(self):
        self.df['DOI'].fillna('', inplace=True)

    def pdfDownloader(self, doi, ref_id):
        if doi:
            paper = f"https://doi.org/{doi}"
            out = os.path.join(self.pdf_output_dir, f"{ref_id}.pdf")
            scihub_download(paper, paper_type="doi",
                            out=out, proxies=self.proxies)
            yield f"Downloaded PDF: {ref_id}"
        else:
            self.df.loc[self.df['Reference_ID'] == ref_id,
                        'Comment',] = "Not Found in SciHub"

    def saveLogs(self):
        self.df.to_csv(self.log_file, index=False)

    def image_format_pdf_text_extraction(self, file_loc, ref_id):
        """
        Extracts text from a PDF file by converting pages to images and using OCR.

        Args:
            file_loc (str): Path to the PDF file.
            ref_id (str): Reference ID for image file naming.

        Returns:
            str: Extracted text from the PDF or an error message.
        """

        try:
            # Open the PDF file
            doc = fitz.open(file_loc)

            # Create the output directory for images, handling potential errors
            rmtree("pdf_imgs")
            output_dir = f"./pdf_imgs/{ref_id}"
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            # Extract text, handling potential errors at each step
            extracted_text = ""

            for i in range(doc.page_count):
                try:
                    # Load page and get pixmap
                    page = doc.load_page(i)
                    pix = page.get_pixmap(dpi=200)

                    # Generate image file name
                    output_file = os.path.join(output_dir, f"{ref_id}_{i}.png")

                    # Save pixmap as image
                    pix.save(output_file)

                    # Extract text from image using Tesseract (ensure Tesseract is installed)
                    extracted_text += pytesseract.image_to_string(
                        Image.open(output_file))
                except Exception as e:
                    raise RuntimeError(f"Error extracting text from page {i+1}: {e}")

            # Close the PDF document
            doc.close()

            # Return extracted text or error message indicating issue with Tesseract
            if not extracted_text:
                raise RuntimeError("Tesseract not found or failed to recognize text.")

            return extracted_text

        except Exception as e:
            raise RuntimeError("Something Went Wrong")

    def extractPDF(self, pdf):
        try:
            ref_id = str(pdf).replace(".pdf", "")
            doc = pymupdf.open(f"./pdfs/{pdf}")
            out = open(f"./extracted_data/{ref_id}.txt", "w", encoding="utf-8")
            text = ""
            for page in doc:
                text += page.get_text()
            if text != "":
                out.write(text)
                out.write("\f")
            else:
                pdf_ocr_data = self.image_format_pdf_text_extraction(
                    f"./pdfs/{pdf}", ref_id)
                out.write(pdf_ocr_data)
                out.write("\f")
            out.close()
        except Exception as error:
            self.df.loc[self.df['Reference_ID'] == ref_id, 'Extracted_Data_Log'] = error
            

    def convert_md_to_csv(self, md_content, csv_file, ref_id):
        headers = []
        rows = []

        # Split the Markdown content into lines
        lines = md_content.strip().splitlines()

        # Extract headers from the first row and add 'ref_id' to the header
        headers = [header.strip()
                   for header in lines[0].strip().split('|') if header]
        headers.insert(0, 'Reference_ID')  # Add ref_id as the first column

        # Extract data rows from subsequent lines, ignoring separator lines
        for line in lines[2:]:  # Skipping the header and separator line
            row = [value.strip() for value in line.strip().split('|') if value]
            if row:  # Only add non-empty rows
                # Insert the ref_id at the beginning of each row
                row.insert(0, ref_id)
                rows.append(row)

        # Write the extracted data to a CSV file
        with open(csv_file, mode='a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)

            # Add headers if the file is empty
            file.seek(0, 2)  # Move the cursor to the end of the file
            if file.tell() == 0:  # Check if the file is empty
                writer.writerow(headers)

            # Write all rows to the CSV file
            writer.writerows(rows)

    def getContext(self):
        with open("./data/training_data.txt", "r+", encoding="utf-8") as context_file:
            context = context_file.read()
            return context

    def get_data_from_pdf(self, pdfs):
        count = 1
        start_time = time.time()

        for pdf in pdfs:
            ref_id = str(pdf).replace(".txt", "")
            file = ""

            with open(f"extracted_data/{pdf}", "r+", encoding="utf-8") as new_data_file:
                file = new_data_file.read()

            if file != "":
                yield f"Thinking File {count}"
                count+=1
                self.context = self.getContext()
                response = self.model.generate_content([
                    self.context,
                    f"input:{file}",
                    "output: ",
                ])
                self.convert_md_to_csv(response.text, "main.csv", ref_id)

                elapsed_time = time.time() - start_time

                if count > 12 and elapsed_time < 60:
                    time.sleep(60)  # Wait for 1 minute
                    start_time = time.time()  # Reset the start time
            else:
                self.df.loc[self.df['Reference_ID']
                            == ref_id, 'Generating_Data_Log'] = "Text Not Found"


class DataHunter(DataUtils):

    if not os.path.exists("./pdfs"):
        os.mkdir("pdfs")
    if not os.path.exists("extracted_data"):
        os.mkdir("extracted_data")

    pdfs = os.listdir("./pdfs")
    new_datas = os.listdir("./extracted_data")

    def __init__(self, to_download_csv_file_path):
        self.df = pd.read_csv(to_download_csv_file_path)
        super().__init__(self.df)
        self.cleanData()

    def downloadPDFs(self):
        for i, row in self.df.iterrows():
            for message in self.pdfDownloader(row['DOI'], row['Reference_ID']):
                yield f"{i}, {message}"
        self.saveLogs()

    def get_pdf_text(self):
        for pdf in self.pdfs:
            self.extractPDF(pdf)
        self.saveLogs()
        return "Data Extraction completed from PDF"

    def getData(self):
        for message in self.get_data_from_pdf(self.new_datas):
            yield message
        self.saveLogs()
