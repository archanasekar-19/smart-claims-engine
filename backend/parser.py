import pdfplumber


def extract_text(file_path):

    if file_path.endswith(".txt"):
        with open(file_path, "r", encoding="utf-8") as file:
            return file.read()

    elif file_path.endswith(".pdf"):

        text = ""

        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                extracted = page.extract_text()

                if extracted:
                    text += extracted + "\n"

        return text

    else:
        raise ValueError("Unsupported file format")
