import cv2
import numpy as np
from doctr.models import detection, recognition
from doctr.datasets import Vocabulary
from doctr.io import DocumentFile
from doctr.utils.visualization import draw_prediction

# Загружаем модель детекции текста
detection_model = detection.linknet_detector(pretrained=True).eval()

# Загружаем модель распознавания текста
vocab = Vocabulary(
    [
        "<pad>",
        "!",
        '"',
        "#",
        "&",
        "'",
        "(",
        ")",
        "*",
        "+",
        ",",
        "-",
        ".",
        "/",
        "0",
        "1",
        "2",
        "3",
        "4",
        "5",
        "6",
        "7",
        "8",
        "9",
        ":",
        ";",
        "<",
        "=",
        ">",
        "?",
        "@",
        "A",
        "B",
        "C",
        "D",
        "E",
        "F",
        "G",
        "H",
        "I",
        "J",
        "K",
        "L",
        "M",
        "N",
        "O",
        "P",
        "Q",
        "R",
        "S",
        "T",
        "U",
        "V",
        "W",
        "X",
        "Y",
        "Z",
        "[",
        "\\",
        "]",
        "^",
        "_",
        "`",
        "a",
        "b",
        "c",
        "d",
        "e",
        "f",
        "g",
        "h",
        "i",
        "j",
        "k",
        "l",
        "m",
        "n",
        "o",
        "p",
        "q",
        "r",
        "s",
        "t",
        "u",
        "v",
        "w",
        "x",
        "y",
        "z",
        "{",
        "|",
        "}",
        "~",
    ]
)
recognition_model = recognition.crnn_vgg16(pretrained=True, vocab=vocab).eval()


# Определяем функцию для предсказания
def predict(doc, detection_model, recognition_model):
    # Детекция текста
    detected = detection_model([doc.file])

    # Распознавание текста
    recognized = recognition_model(detected)

    return recognized


# Прогоняем все изображения через модель
dataset_root = "/path/to/your/dataset/"
output_folder = "/path/to/output/folder/"

for file in os.listdir(dataset_root):
    if file.endswith(".jpg") or file.endswith(".png"):
        doc = DocumentFile.from_images(os.path.join(dataset_root, file))
        recognized = predict(doc, detection_model, recognition_model)

        # Сохраняем результаты
        cv2.imwrite(os.path.join(output_folder, file), recognized.export())
