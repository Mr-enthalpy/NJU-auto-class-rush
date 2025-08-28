import cv2
import numpy as np
from sklearn.cluster import KMeans


def color_cluster_denoise(image, k=3) -> np.ndarray:
    img = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    Z = img.reshape((-1, 3))
    Z = np.float32(Z)
    kmeans = KMeans(n_clusters=k, n_init='auto')
    labels = kmeans.fit_predict(Z)
    centers = np.uint8(kmeans.cluster_centers_)
    clustered = centers[labels.flatten()]
    clustered_img = clustered.reshape((img.shape))
    return cv2.cvtColor(clustered_img, cv2.COLOR_RGB2BGR)

def preprocess_vcode(img) -> np.ndarray:
    img = color_cluster_denoise(img, k=2)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    bin_img = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                                    cv2.THRESH_BINARY_INV, 25, 10)
    return bin_img

def split_image(img: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    h = img.shape[0]
    line = int(h * 5 / 6)
    top_img = img[:line, :]
    bottom_img = img[line:, :]
    return top_img, bottom_img

def extract_characters(bin_img) -> tuple[list[np.ndarray], list[tuple[int, int]]]:
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    dilated = cv2.dilate(bin_img, kernel, iterations=1)
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    char_boxes = []

    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        area = w * h
        if 400 < area < 3000 and 10 < w < 100 and 10 < h < 100:
            char_boxes.append((x, y, w, h))

    char_boxes.sort(key=lambda box: box[0])
    char_imgs = []
    pos_list = []
    for idx, (x, y, w, h) in enumerate(char_boxes):
        char_crop = bin_img[y:y+h, x:x+w]
        pos = ((2 * y + h) // 2, (2 * x + w) // 2)
        char_imgs.append(char_crop)
        pos_list.append(pos)

    return char_imgs, pos_list

def extract_target_templates(bottom_img: np.ndarray) -> list[np.ndarray]:
    char_xs = [118, 141, 164, 187]  # 你提供的左-右边界点
    templates = []
    for i in range(len(char_xs)):
        x1, x2 = char_xs[i], char_xs[i] + 18
        char_img = bottom_img[1:19, x1:x2]
        char_img = cv2.cvtColor(char_img, cv2.COLOR_BGR2GRAY)
        templates.append(char_img)
        # cv2.imwrite(f"{i}.png", char_img)
    return templates


def solve_query(img: np.ndarray, expect_num = 4) -> list[tuple[int, int]]:
    top_img, bottom_img = split_image(img)
    processed_img = preprocess_vcode(top_img)
    char_imgs, pos_list = extract_characters(processed_img)
    if len(char_imgs) != expect_num:
        raise ValueError(f"未能正确分割出 {expect_num} 个字符，请检查图像质量或调整参数")
    # for i, char in enumerate(char_imgs):
    #     cv2.imwrite(f"char_{i}.png", char)
    templates = extract_target_templates(bottom_img)
    from same import match_bijection
    mapping, details, cost  = match_bijection(templates, char_imgs)
    return [pos_list[mapping[i]] for i in range(expect_num)]

if __name__ == "__main__":
    img = cv2.imread("img.png")
    order = solve_query(img)
    print(order)