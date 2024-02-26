from pdf2image import convert_from_path

import tempfile

path_to_pdf = r"C:\Programming\ethos_penalps\examples\basic_examples.py\report_2024_02_21__11_43_50\tex_folder\enterprise_text_file.pdf"

path_to_png = path_to_pdf[:-4] + ".png"
with tempfile.TemporaryDirectory() as path:
    list_of_pillow_images = convert_from_path(path_to_pdf)

    for image in list_of_pillow_images:
        converted_image = image.convert("RGBA")
        converted_image.save(path_to_png)
