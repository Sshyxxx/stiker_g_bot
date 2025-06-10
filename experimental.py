import deeplake
from PIL import Image
import numpy as np
import easyocr

ds_train = deeplake.load("hub://activeloop/icdar-2013-text-localize-train")
# ds_train.visualize()
# ds_test = deeplake.load("hub://activeloop/icdar-2013-text-localize-test")
# ds_test.visualize()
print(ds_train)
# print(ds_test)

results = []

for item in ds_train:
    img = item["images"]

    # Преобразуем изображение в формат, понятный для EasyOCR
    pil_img = Image.fromarray(np.array(img))

    # Распознаем текст на изображении
    ocr_result = reader.readtext(np.array(pil_img), detail=0)

    results.append({"recognized_text": ocr_result})
