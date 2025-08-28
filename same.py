import math
from typing import List, Dict, Tuple, Optional
import numpy as np
import cv2

try:
    from scipy.optimize import linear_sum_assignment
    _HAS_SCIPY = True
except Exception:
    _HAS_SCIPY = False


# ---------------------------
# 预处理与几何工具
# ---------------------------

def _to_float01(x: np.ndarray) -> np.ndarray:
    x = x.astype(np.float32)
    xmin, xmax = float(x.min()), float(x.max())
    if xmax > xmin:
        x = (x - xmin) / (xmax - xmin)
    else:
        x = np.zeros_like(x, dtype=np.float32)
    return x

def _maybe_invert_to_dark_bg(img01: np.ndarray) -> np.ndarray:
    """
    将前景（笔画）尽量统一为“亮”(≈1)，背景为“暗”(≈0)。
    简单启发：若全局均值较高（常见于白底黑字），则取反。
    """
    return 1.0 - img01 if float(img01.mean()) > 0.5 else img01

def _gaussian_smooth(img01: np.ndarray, sigma: float = 0.6) -> np.ndarray:
    k = max(3, int(round(sigma * 6 + 1)) | 1)  # 奇数核
    return cv2.GaussianBlur(img01, (k, k), sigmaX=sigma, sigmaY=sigma, borderType=cv2.BORDER_REPLICATE)

def _center_by_mass(img01: np.ndarray) -> np.ndarray:
    """
    通过图像矩将质心平移到中心，减少后续平移搜索负担。
    """
    h, w = img01.shape[:2]
    m = cv2.moments(img01)
    if m["m00"] < 1e-6:
        return img01.copy()
    cx, cy = m["m10"] / m["m00"], m["m01"] / m["m00"]
    tx, ty = (w / 2.0 - cx), (h / 2.0 - cy)
    M = np.array([[1, 0, tx], [0, 1, ty]], dtype=np.float32)
    return cv2.warpAffine(img01, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0.0)

def _pad_to_square(img01: np.ndarray, target: int = 64) -> np.ndarray:
    """
    将图像零填充到 target x target，保持居中。
    """
    h, w = img01.shape[:2]
    s = target
    canvas = np.zeros((s, s), dtype=np.float32)
    scale = min((s - 4) / max(h, 1), (s - 4) / max(w, 1))  # 预缩放至略小于画布
    nh, nw = max(1, int(round(h * scale))), max(1, int(round(w * scale)))
    resized = cv2.resize(img01, (nw, nh), interpolation=cv2.INTER_LINEAR)
    y0 = (s - nh) // 2
    x0 = (s - nw) // 2
    canvas[y0:y0 + nh, x0:x0 + nw] = resized
    return canvas

def _pad_factor(img01: np.ndarray, factor: float = 1.5) -> np.ndarray:
    """
    将图像扩展到更大的画布（平移搜索更自由）。
    """
    h, w = img01.shape[:2]
    nh, nw = int(round(h * factor)), int(round(w * factor))
    canvas = np.zeros((nh, nw), dtype=np.float32)
    y0 = (nh - h) // 2
    x0 = (nw - w) // 2
    canvas[y0:y0 + h, x0:x0 + w] = img01
    return canvas

def _rotate_scale(img01: np.ndarray, angle_deg: float, scale: float) -> np.ndarray:
    h, w = img01.shape[:2]
    center = (w / 2.0, h / 2.0)
    M = cv2.getRotationMatrix2D(center, angle_deg, scale)
    # 使用线性插值 + 常数边界，边界为0（暗）
    return cv2.warpAffine(img01, M, (w, h), flags=cv2.INTER_LINEAR,
                          borderMode=cv2.BORDER_CONSTANT, borderValue=0.0)

def _match_ncc(template: np.ndarray, image: np.ndarray) -> Tuple[float, Tuple[int, int]]:
    """
    返回 (最大归一化互相关得分, 位置)；位置为 (y, x)。
    要求 image 尺度 >= template 尺度；若相等则只产生单值得分。
    """
    th, tw = template.shape
    ih, iw = image.shape
    if th > ih or tw > iw:
        # 若模板比图大，缩小模板以适配（保守做法，避免跳过有效匹配）
        scale = min(ih / th, iw / tw) * 0.95
        nh = max(1, int(round(th * scale)))
        nw = max(1, int(round(tw * scale)))
        template = cv2.resize(template, (nw, nh), interpolation=cv2.INTER_LINEAR)
        th, tw = template.shape

    # OpenCV 的 TM_CCOEFF_NORMED 对亮度/对比度变化较稳健
    res = cv2.matchTemplate(image, template, method=cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(res)
    y, x = max_loc[1], max_loc[0]
    return float(max_val), (y, x)


# ---------------------------
# 粗筛（可选）：Hu 矩不变矩
# ---------------------------

def _hu_descriptor(img01: np.ndarray) -> np.ndarray:
    """
    经典的平移/尺度/旋转不变描述子，低分辨率下可作粗筛。
    使用对数绝对值以压缩动态范围。
    """
    # 二值化（Otsu）前先轻度平滑
    blur = _gaussian_smooth(img01, 0.8)
    blur8 = np.clip(blur * 255.0, 0, 255).astype(np.uint8)
    _, bw = cv2.threshold(blur8, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    m = cv2.moments(bw)
    hu = cv2.HuMoments(m).reshape(-1)
    # 对数尺度
    hu = -np.sign(hu) * np.log10(np.clip(np.abs(hu), 1e-12, None))
    return hu.astype(np.float32)


# ---------------------------
# 主流程
# ---------------------------

def match_bijection(
    A: list[np.ndarray],
    B: list[np.ndarray],
    *,
    canvas_size: int = 64,
    pad_factor_search: float = 1.5,
    gaussian_sigma: float = 0.6,
    angle_step_deg: float = 7.5,
    scale_min: float = 0.75,
    scale_max: float = 1.25,
    scale_step: float = 0.05,
    coarse_prune_k: Optional[int] = None,  # 可选：仅对每个 B_j 的前 k 个最相似 A_i 做精确匹配
) -> Tuple[Dict[int, int], np.ndarray, Dict[Tuple[int, int], Dict]]:
    """
    建立从 B 到 A 的双射匹配。

    输入：
        A, B: list[np.ndarray]，灰度或二值图，尺寸约 n x n, n∈[20,30]
    参数：
        angle_step_deg / scale_(min|max|step): 旋转与缩放的搜索网格
        coarse_prune_k: 若不为 None，则用 Hu 矩做粗筛，仅保留每个 B_j 的前 k 个 A_i 进入精确阶段
    输出：
        mapping: dict { j_in_B : i_in_A }
        score_mat: shape=(len(A), len(B))，每对 (i,j) 的最优 NCC 分数
        best_params: dict[(i,j)] = {"score":..., "angle":..., "scale":..., "loc":(y,x)}
    """
    assert len(A) == len(B), "A 与 B 的元素个数必须相等（需要构造双射）。"
    n = len(A)
    # 1) 标准化与统一画布
    def _prep(img: np.ndarray) -> np.ndarray:
        g = _to_float01(img)
        g = _maybe_invert_to_dark_bg(g)
        g = _gaussian_smooth(g, gaussian_sigma)
        g = _pad_to_square(g, canvas_size)
        g = _center_by_mass(g)
        return g

    A_prep = [ _prep(a) for a in A ]
    B_prep = [ _prep(b) for b in B ]
    B_search = [ _pad_factor(b, pad_factor_search) for b in B_prep ]  # 为平移搜索留空间

    # 2) 可选粗筛：Hu 矩
    prune_lists: List[List[int]] = [ list(range(n)) for _ in range(n) ]
    if coarse_prune_k is not None and coarse_prune_k < n:
        hu_A = [ _hu_descriptor(a) for a in A_prep ]
        hu_B = [ _hu_descriptor(b) for b in B_prep ]
        prune_lists = []
        for j in range(n):
            dists = [ float(np.linalg.norm(hu_A[i] - hu_B[j])) for i in range(n) ]
            cand = np.argsort(dists)[:coarse_prune_k].tolist()
            prune_lists.append(cand)

    # 3) 预生成 A 的旋转缩放模板（避免重复计算）
    angles = np.arange(-180.0, 180.0, angle_step_deg, dtype=np.float32)
    scales = np.arange(scale_min, scale_max + 1e-6, scale_step, dtype=np.float32)

    A_templates: List[List[np.ndarray]] = []  # A_templates[i] = [templ for all (angle,scale)]
    templ_params: List[List[Tuple[float, float]]] = []
    for i in range(n):
        bank = []
        params = []
        base = A_prep[i]
        for ang in angles:
            for sc in scales:
                templ = _rotate_scale(base, float(ang), float(sc))
                bank.append(templ)
                params.append((float(ang), float(sc)))
        A_templates.append(bank)
        templ_params.append(params)

    # 4) 计算得分矩阵（最大 NCC）
    score_mat = np.full((n, n), -1.0, dtype=np.float32)
    best_params: Dict[Tuple[int, int], Dict] = {}

    for j in range(n):
        img = B_search[j]
        allowed_i = prune_lists[j]
        for i in allowed_i:
            bank = A_templates[i]
            params = templ_params[i]
            best_score = -1.0
            best_info = {"score": -1.0, "angle": 0.0, "scale": 1.0, "loc": (0, 0)}
            for templ, (ang, sc) in zip(bank, params):
                score, loc = _match_ncc(templ, img)
                if score > best_score:
                    best_score = score
                    best_info = {"score": float(score), "angle": float(ang), "scale": float(sc), "loc": loc}
            score_mat[i, j] = best_score
            best_params[(i, j)] = best_info

    # 5) 全局一一匹配：最大化总分
    # 使用匈牙利算法（SciPy），否则贪心回退（对本问题规模=4通常足够）
    if _HAS_SCIPY:
        # linear_sum_assignment 是最小化问题；这里取负号等价于最大化
        row_ind, col_ind = linear_sum_assignment(-score_mat)
        mapping = { int(col): int(row) for row, col in zip(row_ind, col_ind) }
    else:
        # 贪心：每次选当前最大分数的 (i,j)，直至匹配完
        mapping = {}
        used_i = set()
        used_j = set()
        # 将所有分数展开排序
        pairs = [ (float(score_mat[i, j]), i, j) for i in range(n) for j in range(n) ]
        pairs.sort(key=lambda x: x[0], reverse=True)
        for s, i, j in pairs:
            if i in used_i or j in used_j:
                continue
            mapping[i] = j
            used_i.add(i)
            used_j.add(j)
            if len(mapping) == n:
                break

    return mapping, score_mat, best_params


