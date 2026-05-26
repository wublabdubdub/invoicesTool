#!/usr/bin/env python3
"""
本地发票 OCR 脚本
依赖: pip install paddleocr paddlepaddle pymupdf opencv-python-headless

三层识别策略（速度递减，按需降级）：
  1. QR 码  — 毫秒级，提取：发票号码、含税金额、开票日期
  2. 文本提取 — 毫秒级，提取：销售方、税额、分类等（数字 PDF 专用）
  3. OCR     — 秒级，兜底扫描件 / 图片 PDF

用法:
  单次: python ocr.py <pdf_path>
  常驻: python ocr.py --server   (stdin/stdout JSON 通信)
"""

import sys
import json
import re
import os
import warnings

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

os.environ['PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK'] = 'True'
warnings.filterwarnings('ignore')

_MAX_MONEY_VALUE = 1_000_000_000.0
_PDF_OCR_RENDER_SCALE = 1.0
_PDF_EXTENSIONS = {'.pdf'}
_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png'}
_SUPPORTED_DOCUMENT_EXTENSIONS = _PDF_EXTENSIONS | _IMAGE_EXTENSIONS


def is_pdf_file(file_path):
    return os.path.splitext(file_path)[1].lower() in _PDF_EXTENSIONS


def is_image_file(file_path):
    return os.path.splitext(file_path)[1].lower() in _IMAGE_EXTENSIONS


def is_supported_document(file_path):
    return os.path.splitext(file_path)[1].lower() in _SUPPORTED_DOCUMENT_EXTENSIONS


def parse_money(raw):
    """
    解析金额字段，过滤税号这类长数字误识别。
    返回 float 或 None。
    """
    if raw is None:
        return None

    s = str(raw).strip().replace(',', '').replace('，', '')
    if not re.fullmatch(r'\d+(?:\.\d{1,2})?', s):
        return None

    int_part = s.split('.', 1)[0]
    # 纯数字过长通常是税号/编码，不是金额
    if '.' not in s and len(int_part) >= 15:
        return None
    if len(int_part) > 9:
        return None

    value = float(s)
    if value < 0 or value > _MAX_MONEY_VALUE:
        return None

    return round(value, 2)


# ─────────────────────────────────────────────────────────────────────────────
# 第一层：QR 码解析
# ─────────────────────────────────────────────────────────────────────────────

def extract_qr_from_pdf(pdf_path, max_pages=1):
    """用 OpenCV 从 PDF 首页提取所有 QR 码文本。失败时静默返回空列表。"""
    try:
        import fitz
        import numpy as np
        import cv2

        doc = fitz.open(pdf_path)
        qr_texts = []
        for i, page in enumerate(doc):
            if i >= max_pages:
                break
            pix = page.get_pixmap(matrix=fitz.Matrix(3.0, 3.0))
            img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
                pix.height, pix.width, pix.n
            )
            if pix.n == 4:
                img = img[:, :, :3]
            gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
            data, _, _ = cv2.QRCodeDetector().detectAndDecode(gray)
            if data:
                qr_texts.append(data.strip())
        doc.close()
        return qr_texts
    except Exception:
        return []


def read_image_rgb(image_path):
    """Unicode-safe image loading for OpenCV on Windows."""
    import numpy as np
    import cv2

    data = np.fromfile(image_path, dtype=np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if img is None:
        return None
    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)


def extract_qr_from_image(image_path):
    """用 OpenCV 从图片发票中提取 QR 码文本。失败时静默返回空列表。"""
    try:
        import cv2

        img = read_image_rgb(image_path)
        if img is None:
            return []
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        data, _, _ = cv2.QRCodeDetector().detectAndDecode(gray)
        return [data.strip()] if data else []
    except Exception:
        return []


def extract_qr_codes(file_path, max_pages=1):
    if is_pdf_file(file_path):
        return extract_qr_from_pdf(file_path, max_pages=max_pages)
    if is_image_file(file_path):
        return extract_qr_from_image(file_path)
    return []


def parse_invoice_qr(qr_text):
    """
    解析中国增值税电子发票 QR 码。

    已知格式（逗号分隔）：
      01, 省份码, 发票代码, 发票号码, 含税金额, 日期YYYYMMDD, 税前金额, 校验码

    返回提取到的字段字典（仅包含有值的字段）。
    """
    result = {}
    parts = [p.strip() for p in qr_text.split(',')]

    if len(parts) >= 6 and parts[0] in ('01', '04', '10', '11'):
        # parts[3]: 发票号码
        if len(parts) > 3 and re.match(r'^\d{8,20}$', parts[3]):
            result['invoice_no'] = parts[3]

        # parts[4]: 含税金额
        if len(parts) > 4 and re.match(r'^\d+\.?\d*$', parts[4]):
            money = parse_money(parts[4])
            if money is not None:
                result['total'] = money

        # parts[5]: 日期 YYYYMMDD
        if len(parts) > 5 and re.match(r'^\d{8}$', parts[5]):
            d = parts[5]
            result['date'] = f'{d[:4]}-{d[4:6]}-{d[6:8]}'

        # parts[6]: 税前金额（可为空）
        if len(parts) > 6 and re.match(r'^\d+\.?\d*$', parts[6]):
            amt = parse_money(parts[6])
            if amt is not None and amt > 0:
                result['amount'] = amt

        if result.get('total') is not None and result.get('amount') is not None:
            tax = round(result['total'] - result['amount'], 2)
            if tax >= 0:
                result['tax'] = tax

    return result


def is_qr_confident(fields):
    """QR is enough for fast import when it identifies the invoice and date or total."""
    return bool(
        fields.get('invoice_no')
        and (fields.get('total') is not None or fields.get('date') is not None)
    )


# ─────────────────────────────────────────────────────────────────────────────
# 第二层：PDF 文本提取
# ─────────────────────────────────────────────────────────────────────────────

_TEXT_THRESHOLD = 50  # 低于此字符数视为扫描件

def extract_text_from_pdf(pdf_path, max_pages=2):
    """
    直接提取 PDF 嵌入文本。
    返回 (lines: list[str], is_text_based: bool)
    """
    import fitz
    doc = fitz.open(pdf_path)
    all_text = ''
    for i, page in enumerate(doc):
        if i >= max_pages:
            break
        all_text += page.get_text()
    doc.close()

    stripped = all_text.strip()
    if len(stripped) < _TEXT_THRESHOLD:
        return [], False

    lines = [l.strip() for l in stripped.splitlines() if l.strip()]
    return lines, True


# ─────────────────────────────────────────────────────────────────────────────
# 第三层：OCR（扫描件兜底）
# ─────────────────────────────────────────────────────────────────────────────

_ocr = None

def get_ocr():
    global _ocr
    if _ocr is None:
        import logging
        logging.disable(logging.CRITICAL)
        from paddleocr import PaddleOCR
        _ocr = PaddleOCR(
            lang='ch',
            enable_mkldnn=False,
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
        )
    return _ocr


def pdf_to_images(pdf_path, max_pages=2, scale=_PDF_OCR_RENDER_SCALE):
    import fitz, numpy as np
    doc = fitz.open(pdf_path)
    images = []
    for i, page in enumerate(doc):
        if i >= max_pages:
            break
        pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale))
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
            pix.height, pix.width, pix.n
        )
        if pix.n == 4:
            img = img[:, :, :3]
        images.append(img)
    doc.close()
    return images


def image_to_images(image_path):
    img = read_image_rgb(image_path)
    return [img] if img is not None else []


def document_to_images(file_path, max_pages=2):
    if is_pdf_file(file_path):
        return pdf_to_images(file_path, max_pages=max_pages)
    if is_image_file(file_path):
        return image_to_images(file_path)
    return []


def run_ocr(images):
    ocr = get_ocr()
    lines = []
    for img in images:
        for res in ocr.predict(img):
            for text in res.get('rec_texts', []):
                t = text.strip()
                if t:
                    lines.append(t)
    return lines


def image_seller_region_to_images(image_path):
    img = read_image_rgb(image_path)
    if img is None:
        return []

    h, w = img.shape[:2]
    regions = [
        (0.52, 0.18, 0.99, 0.55),
        (0.60, 0.25, 0.98, 0.42),
        (0.02, 0.18, 0.99, 0.50),
    ]
    crops = []
    for x1, y1, x2, y2 in regions:
        left, top = int(w * x1), int(h * y1)
        right, bottom = int(w * x2), int(h * y2)
        crop = img[top:bottom, left:right]
        if crop.size:
            crops.append(crop)
    return crops


def extract_image_seller_fields_fast(image_path):
    """Run OCR only on likely seller-info crops for image invoices."""
    lines = []
    for crop in image_seller_region_to_images(image_path):
        lines = run_ocr([crop])
        fields = extract_seller_fields_from_lines(lines, allow_single_name=True)
        if fields.get('vendor'):
            fields['_ocr_lines'] = lines
            return fields

    return {'vendor': None, 'vendor_tax_id': None, '_ocr_lines': lines}


def extract_seller_fields_from_lines(lines, allow_single_name=False):
    text = '\n'.join(lines)
    tax_id_re = re.compile(r'^[0-9A-Z]{18}$')
    suffixes = (
        '公司|店|厂|局|院|馆|酒店|餐厅|饭店|超市|银行|科技|集团|服务|餐饮'
        '|铺|社|所|中心|部|站|处|坊|园|场|网络|贸易|商贸|工作室|诊所|药店'
    )
    company_re = re.compile(rf'[\u4e00-\u9fffA-Za-z0-9（）()·]{{2,50}}(?:{suffixes})[\u4e00-\u9fffA-Za-z0-9（）()·]{{0,12}}')

    def clean_vendor(value):
        value = re.sub(r'^(?:名\s*)?称[：:：]?', '', value.strip())
        value = value.strip().rstrip('，,。.')
        if not value or re.match(r'^[\s：:]*$', value):
            return None
        if '：' in value or ':' in value:
            return None
        label_tokens = (
            '统一社会信用代码', '纳税人识别号', '识别号', '税号',
            '名称', '地址', '电话', '开户行', '账号'
        )
        if any(tok in value for tok in label_tokens):
            return None
        if not re.search(r'[\u4e00-\u9fff]', value):
            return None
        match = company_re.search(value)
        return match.group(0) if match else value

    inline_names = [
        clean_vendor(m.group(1))
        for m in re.finditer(r'(?:名\s*)?称[：:]\s*([^\n：:]{2,60})', text)
    ]
    inline_names = [v for v in inline_names if v]
    vendor = None
    if len(inline_names) >= 2:
        vendor = inline_names[1]
    elif allow_single_name and len(inline_names) == 1:
        vendor = inline_names[0]

    if not vendor:
        candidates = []
        for line in lines:
            if tax_id_re.match(line):
                continue
            if re.search(r'[%％¥￥\d]{3,}', line):
                continue
            for match in company_re.finditer(line):
                candidate = clean_vendor(match.group(0))
                if candidate:
                    candidates.append(candidate)
        if len(candidates) >= 2:
            vendor = candidates[1]
        elif allow_single_name and candidates:
            vendor = candidates[-1]

    vendor_tax_id = None
    if not allow_single_name:
        inline_tax_ids = re.findall(
            r'(?:统一社会信用代码|纳税人识别号)[/／\w]*[：:]\s*([0-9A-Z]{18})',
            text
        )
        if len(inline_tax_ids) >= 2:
            vendor_tax_id = inline_tax_ids[1]
        else:
            standalone = [line for line in lines if tax_id_re.match(line)]
            if len(standalone) >= 2:
                vendor_tax_id = standalone[1]

    return {'vendor': vendor, 'vendor_tax_id': vendor_tax_id}


# ─────────────────────────────────────────────────────────────────────────────
# 字段提取（从文本行中解析结构化字段）
# ─────────────────────────────────────────────────────────────────────────────

def extract_fields(lines):
    text = '\n'.join(lines)
    normalized_text = text.replace(' ', '').replace('\t', '')

    def _extract_line_money_values(line):
        values = []
        for raw in re.findall(r'(?<!\d)(\d[\d,，]*\.\d{1,2})(?!\d)', line):
            money = parse_money(raw)
            if money is not None:
                values.append(money)
        return values

    def _parse_date_candidate(line):
        line = line.strip()
        for pat in [
            r'(\d{4})[年\-/](\d{1,2})[月\-/](\d{1,2})',
            r'(\d{4})(\d{2})(\d{2})',
        ]:
            m = re.search(pat, line)
            if m:
                return f'{m.group(1)}-{m.group(2).zfill(2)}-{m.group(3).zfill(2)}'
        return None

    def _looks_like_air_ticket_invoice():
        return (
            '航空运输电子客票行程单' in normalized_text
            or ('电子客票' in normalized_text and ('承运人' in normalized_text or '航班号' in normalized_text))
            or ('民航发展基金' in normalized_text and ('客票' in normalized_text or '航班' in normalized_text))
        )

    def _extract_nearby_money(label):
        label_re = re.escape(label)
        for idx, line in enumerate(lines):
            if label not in line:
                continue
            window = ' '.join(lines[idx: idx + 3])
            m = re.search(
                rf'{label_re}[^\d\n]{{0,80}}(?:CNY|RMB|人民币|¥|￥)?\s*([\d,，]+(?:\.\d{{1,2}})?)',
                window,
                re.IGNORECASE
            )
            if m:
                money = parse_money(m.group(1))
                if money is not None:
                    return money
        return None

    def _extract_air_ticket_date():
        for pat in [
            r'填开日期[：:]?\s*(\d{4})[年\-/](\d{1,2})[月\-/](\d{1,2})',
            r'开具日期[：:]?\s*(\d{4})[年\-/](\d{1,2})[月\-/](\d{1,2})',
        ]:
            m = re.search(pat, text)
            if m:
                return f'{m.group(1)}-{m.group(2).zfill(2)}-{m.group(3).zfill(2)}'
        return None

    def _extract_air_ticket_vendor():
        def clean_air_vendor(value):
            value = value.strip()
            value = re.split(r'\s{2,}|填开日期|销售网点|购买方|统一社会信用代码', value)[0].strip(' ：:,，。')
            label_tokens = (
                '旅客姓名', '有效身份证件号码', '签注', '承运人', '航班号', '座位等级',
                '日期', '时间', '客票级别', '票价', '燃油附加费', '增值税',
                '民航发展基金', '其他税费', '合计', '电子客票号码', '验证码'
            )
            if not value or any(token in value for token in label_tokens):
                return None
            if not re.search(r'[\u4e00-\u9fff]', value):
                return None
            return value

        for pat in [
            r'(?:填开单位|开单位|开具单位)[：:]?[ \t]*([^\n]{2,60})',
            r'承运人[：:][ \t]*([^\n]{2,40})',
        ]:
            m = re.search(pat, text)
            if m:
                value = clean_air_vendor(m.group(1))
                if value:
                    return value
        return None

    def _extract_air_ticket_money_values(segment):
        values = []
        for line in segment.splitlines():
            if re.search(r'\d+(?:\.\d+)?\s*%', line):
                continue
            for raw in re.findall(r'(?<!\d)(\d[\d,，]*(?:\.\d{1,2})?)(?!\d)', line):
                money = parse_money(raw)
                if money is not None:
                    values.append(money)
        return values

    def _extract_air_ticket_money_map():
        start = None
        for idx, line in enumerate(lines):
            if '票价' in line:
                start = idx
                break
        if start is None:
            return {}

        end = min(len(lines), start + 40)
        for idx in range(start + 1, end):
            if any(marker in lines[idx] for marker in ['电子客票号码', '验证码', '提示信息', '保险费']):
                end = idx
                break

        segment = '\n'.join(lines[start:end])
        labels = []
        for label in ['票价', '燃油附加费', '增值税税额', '民航发展基金', '其他税费', '合计']:
            pos = segment.find(label)
            if pos >= 0:
                labels.append((pos, label))
        labels.sort()

        values = _extract_air_ticket_money_values(segment)
        result = {}

        if len(values) >= 6:
            standard_labels = ['票价', '燃油附加费', '增值税税额', '民航发展基金', '其他税费', '合计']
            result.update({label: values[idx] for idx, label in enumerate(standard_labels)})
            return result

        for idx, (_, label) in enumerate(labels):
            if idx < len(values):
                result[label] = values[idx]

        if values:
            result.setdefault('合计', max(values))
        return result

    # 发票号码
    invoice_no = None
    for pat in [
        r'发票号码[：:]\s*(\d{8,20})',
        r'No[.．]\s*(\d{8,20})',
        r'票号[：:]\s*(\d{8,20})',
    ]:
        m = re.search(pat, text)
        if m:
            invoice_no = m.group(1)
            break

    # 标签和值分离：发票号码在后续独立一行
    if invoice_no is None:
        for idx, line in enumerate(lines):
            if '发票号码' not in line and '票号' not in line:
                continue
            for j in range(idx + 1, min(idx + 4, len(lines))):
                candidate = lines[j].strip()
                if re.fullmatch(r'\d{8,20}', candidate):
                    invoice_no = candidate
                    break
            if invoice_no is not None:
                break

    # 兜底：独立长数字行，且附近出现过"发票号码"
    if invoice_no is None:
        label_positions = [i for i, line in enumerate(lines) if '发票号码' in line or '票号' in line]
        for idx, line in enumerate(lines):
            candidate = line.strip()
            if not re.fullmatch(r'\d{8,20}', candidate):
                continue
            if any(abs(idx - pos) <= 4 for pos in label_positions):
                invoice_no = candidate
                break

    # 开票日期
    date = None
    for pat in [
        r'开票日期[：:]\s*(\d{4})[年\-/](\d{1,2})[月\-/](\d{1,2})',
        r'填开日期[：:]?\s*(\d{4})[年\-/](\d{1,2})[月\-/](\d{1,2})',
        r'日\s*期[：:]\s*(\d{4})[年\-/](\d{1,2})[月\-/](\d{1,2})',
        r'(\d{4})[年\-/](\d{1,2})[月\-/](\d{1,2})[日号]',
    ]:
        m = re.search(pat, text)
        if m:
            date = f'{m.group(1)}-{m.group(2).zfill(2)}-{m.group(3).zfill(2)}'
            break

    # 票号/日期分离布局：独立数字行旁边有日期，且靠近页头标签区
    if invoice_no is None:
        label_positions = [i for i, line in enumerate(lines) if '发票号码' in line or '开票日期' in line or '票号' in line]
        for idx, line in enumerate(lines):
            candidate = line.strip()
            if not re.fullmatch(r'\d{8,20}', candidate):
                continue

            nearby_dates = []
            for j in range(max(0, idx - 2), min(len(lines), idx + 3)):
                if j == idx:
                    continue
                parsed = _parse_date_candidate(lines[j])
                if parsed:
                    nearby_dates.append(parsed)

            if nearby_dates and any(abs(idx - pos) <= 40 for pos in label_positions):
                invoice_no = candidate
                if date is None:
                    date = nearby_dates[0]
                break

    # ── 销售方名称 & 税号 ────────────────────────────────────────────────────
    # 发票布局分三类：
    #   A  名称：公司名  同行（盒马、滴滴等）
    #   B  标签/值分离，值区：买方名→买方税号→卖方名→卖方税号（或名1→名2→税号1→税号2）
    #   C  特殊票据（高铁电子客票，无销售方字段）
    vendor = None
    vendor_tax_id = None

    _TAX_ID_RE = re.compile(r'^[0-9A-Z]{18}$')

    def _clean_vendor(v):
        """清理并校验 vendor 候选值；无效返回 None。"""
        v = v.strip().rstrip('，,。.')
        if not v or re.match(r'^[\s：:]*$', v):
            return None
        if '：' in v or ':' in v:          # 另一个标签，不是名称值
            return None
        # 标签文本误识别（不是公司名称）
        _LABEL_TOKENS = (
            '统一社会信用代码', '纳税人识别号', '识别号', '税号',
            '名称', '地址', '电话', '开户行', '账号'
        )
        if any(tok in v for tok in _LABEL_TOKENS):
            return None
        if not re.search(r'[\u4e00-\u9fff]', v):  # 必须含汉字
            return None
        return v

    # ── 策略1：内联名称对（Layout A / 滴滴等）─────────────────────────────
    # 找所有 "名称：公司名" 内联行；同一发票中出现顺序为 买方在前、卖方在后
    _inline_names = [
        _clean_vendor(m.group(1))
        for m in re.finditer(r'名\s*称[：:]\s*([^\n：:]{2,40})', text)
    ]
    _inline_names = [v for v in _inline_names if v]
    if len(_inline_names) >= 2:
        vendor = _inline_names[1]          # 第2个=销售方

    # 含标签的内联税号（"统一社会信用代码/纳税人识别号:XXXXXXXXXX"）
    _inline_tax_ids = re.findall(
        r'(?:统一社会信用代码|纳税人识别号)[/／\w]*[：:]\s*([0-9A-Z]{15,20})',
        text
    )
    if len(_inline_tax_ids) >= 2:
        vendor_tax_id = _inline_tax_ids[1]  # 第2个=销售方税号

    # ── 高铁/火车票：无销售方企业字段，直接设为"中国铁路"──────────────────
    if not vendor and ('铁路电子客票' in text or '电子客票号' in text):
        vendor = '中国铁路'

    # ── 策略2A：后缀匹配（Layout B，找第2家公司名=销售方）──────────────────
    if not vendor:
        _SUFFIXES = (
            '公司|店|厂|局|院|馆|酒店|餐厅|饭店|超市|银行|科技|集团|服务|餐饮'
            '|铺|社|所|中心|部|站|处|坊|园|场|网络|贸易|商贸|工作室|诊所|药店'
        )
        company_pat = re.compile(rf'^[\s\S]{{2,40}}(?:{_SUFFIXES})[\S]{{0,8}}$')
        _GOVT_PREFIXES = ('国家税务', '全国统一', '省税务', '市税务')
        companies = [
            l for l in lines
            if company_pat.match(l)
            and not _TAX_ID_RE.match(l)
            and not re.search(r'[%％¥￥\d]{3,}', l)
            and not any(l.startswith(p) for p in _GOVT_PREFIXES)
        ]
        if len(companies) >= 2:
            vendor = companies[1]           # 第1个=买方，第2个=销售方

    # ── 策略2B：以独立行税号为锚点（Layout B type 2）──────────────────────
    if not vendor:
        tax_positions = [i for i, l in enumerate(lines) if _TAX_ID_RE.match(l)]
        if len(tax_positions) >= 2:
            p1, p2 = tax_positions[0], tax_positions[1]
            between = [lines[i] for i in range(p1 + 1, p2)
                       if lines[i].strip() and not _TAX_ID_RE.match(lines[i])]
            if between:
                vendor = between[-1]
            else:
                for j in range(p2 - 1, max(p2 - 8, -1), -1):
                    c = lines[j].strip()
                    if c and not _TAX_ID_RE.match(c) and '：' not in c and ':' not in c:
                        vendor = c
                        break

    # ── 税号补充：从独立行提取（内联未找到时）─────────────────────────────
    if not vendor_tax_id:
        standalone = [l for l in lines if _TAX_ID_RE.match(l)]
        if len(standalone) >= 2:
            vendor_tax_id = standalone[1]


    # 金额
    total = amount = tax = None
    for pat in [
        r'价税合计[（(]大写[）)][^¥￥\d]*[¥￥]\s*([\d,，.]+)',
        # 分离布局：（小写）单独一行，金额在后几行（支持全角半角括号）
        r'[（(]小写[）)][^\d¥￥]{0,40}([\d,，.]{3,})',
        r'合\s*计[：:]\s*[¥￥]\s*([\d,，.]+)',
        r'实付金额[：:]\s*[¥￥]?\s*([\d,，.]+)',
        # 高铁/出租车票价
        r'票价[：:]\s*[¥￥￥]\s*([\d,，.]+)',
    ]:
        m = re.search(pat, text)
        if m:
            money = parse_money(m.group(1))
            if money is not None:
                total = money
                break

    for pat in [r'不含税金额[：:]\s*[¥￥]?\s*([\d,，.]+)',
                r'税前金额[：:]\s*[¥￥]?\s*([\d,，.]+)']:
        m = re.search(pat, text)
        if m:
            money = parse_money(m.group(1))
            if money is not None:
                amount = money
                break

    for pat in [r'税\s*额[：:]\s*[¥￥]?\s*([\d,，.]+)',
                r'增值税额[：:]\s*[¥￥]?\s*([\d,，.]+)']:
        m = re.search(pat, text)
        if m:
            money = parse_money(m.group(1))
            if money is not None:
                tax = money
                break

    # 合计税额（汇总行）
    if tax is None:
        m = re.search(r'合\s*计.*?[¥￥]\s*[\d.]+\s*[¥￥]\s*([\d.]+)', text)
        if m:
            tax = parse_money(m.group(1))

    # 常见电子发票汇总行：合计 123.45 7.41
    if amount is None or tax is None:
        for line in lines:
            normalized = line.replace('　', ' ').strip()
            if '价税合计' in normalized:
                continue
            if '合计' not in normalized:
                continue
            nums = _extract_line_money_values(normalized)
            if len(nums) >= 2:
                cand_amount, cand_tax = nums[-2], nums[-1]
                if cand_amount >= cand_tax:
                    if amount is None:
                        amount = cand_amount
                    if tax is None:
                        tax = cand_tax
                    break

    # 邻近标签布局：金额 / 税额 分行或同行出现
    if amount is None or tax is None:
        for idx, line in enumerate(lines):
            window = ' '.join(lines[idx: idx + 3])

            if amount is None and ('金额' in line or '金额' in window):
                nums = _extract_line_money_values(window)
                if nums:
                    amount = nums[0]

            if tax is None and ('税额' in line or '增值税额' in line or '税额' in window):
                nums = _extract_line_money_values(window)
                if nums:
                    tax = nums[-1]

    # 兜底：从带货币符号的值中推断 amount/tax/total（适配分行表格票）
    currency_vals = []
    plain_money_vals = []
    for line in lines:
        plain_money_vals.extend(_extract_line_money_values(line))
        for raw in re.findall(r'[¥￥]\s*([\d,，]+(?:\.\d{1,2})?)', line):
            money = parse_money(raw)
            if money is not None:
                currency_vals.append(money)

    money_candidates = currency_vals[:] if currency_vals else []
    if plain_money_vals:
        seen = set(money_candidates)
        for value in plain_money_vals:
            if value not in seen:
                money_candidates.append(value)
                seen.add(value)

    if money_candidates:
        inferred_amount = inferred_tax = inferred_total = None
        if len(money_candidates) >= 3:
            for i in range(len(money_candidates) - 2):
                a, t, tot = money_candidates[i], money_candidates[i + 1], money_candidates[i + 2]
                if t <= tot and a <= tot and abs((a + t) - tot) <= 0.05:
                    inferred_amount, inferred_tax, inferred_total = a, t, tot
                    break

        # 已有 total 时，再尝试从所有货币值里找一对 amount + tax = total
        if total is not None and (amount is None or tax is None):
            pair_candidates = []
            for i in range(len(money_candidates)):
                for j in range(i + 1, len(money_candidates)):
                    x, y = money_candidates[i], money_candidates[j]
                    if x > total or y > total:
                        continue
                    diff = abs((x + y) - total)
                    if diff <= 0.05:
                        cand_amount, cand_tax = max(x, y), min(x, y)
                        pair_candidates.append((diff, cand_amount, cand_tax))

            if pair_candidates:
                pair_candidates.sort(key=lambda item: (item[0], -item[1], item[2]))
                _, pair_amount, pair_tax = pair_candidates[0]
                if amount is None:
                    amount = pair_amount
                if tax is None:
                    tax = pair_tax

        if inferred_total is None:
            inferred_total = max(money_candidates)

        if amount is None and inferred_amount is not None:
            amount = inferred_amount
        if tax is None and inferred_tax is not None:
            tax = inferred_tax
        if total is None and inferred_total is not None:
            total = inferred_total

    if total and tax and not amount:
        amount = round(total - tax, 2)
    if total is not None and amount is not None and tax is None:
        inferred_tax = round(total - amount, 2)
        if inferred_tax >= 0:
            tax = inferred_tax

    if total is not None and tax is not None and tax > total:
        tax = None
    if total is not None and amount is not None and amount > total:
        amount = None

    is_air_ticket_invoice = _looks_like_air_ticket_invoice()
    if is_air_ticket_invoice:
        air_money = _extract_air_ticket_money_map()

        air_date = _extract_air_ticket_date()
        if air_date:
            date = air_date

        air_vendor = _extract_air_ticket_vendor()
        if air_vendor:
            vendor = air_vendor

        air_total = air_money.get('合计') or _extract_nearby_money('合计')
        if air_total is not None:
            total = air_total

        air_tax = air_money.get('增值税税额') or _extract_nearby_money('增值税税额') or _extract_nearby_money('税额')
        if air_tax is not None:
            tax = air_tax

        if total is not None and tax is not None:
            amount = round(total - tax, 2)

    # 发票类型
    invoice_type = '其他'
    for t, kws in [
        ('增值税专用发票', ['增值税专用发票', '专用发票']),
        ('增值税普通发票', ['增值税普通发票', '普通发票', '电子普通发票', '电子发票']),
        ('行程单',       ['行程单', '机票', '火车票', '高铁', '航空', '电子客票']),
        ('酒店发票',     ['住宿', '酒店', '宾馆', '客房', '房费']),
        ('出租车票',     ['出租车', '打车', '滴滴', '快车', '网约车', '的士']),
    ]:
        if any(kw in text for kw in kws):
            invoice_type = t
            break

    if is_air_ticket_invoice:
        invoice_type = '行程单'

    def _vendor_startswith(value, prefix):
        if not value:
            return False
        normalized = re.sub(r'\s+', '', value)
        return normalized.startswith(prefix)

    # 费用分类（四类，优先级从高到低）
    category = '餐饮外卖'
    for cat, kws in [
        ('城市间交通', ['机票', '火车票', '高铁', '铁路', '行程单', '电子客票', '铁路电子客票', '航空运输', '航班号', '民航发展基金']),
        ('打车',     ['出租车', '滴滴', '打车', '地铁', '公交', '快车', '网约车', '旅客运输']),
        ('住宿',     ['住宿', '酒店', '宾馆', '客房', '民宿', '房费']),
    ]:
        if any(kw in text for kw in kws):
            category = cat
            break

    if any(_vendor_startswith(vendor, prefix) for prefix in ('上海蒜芽科技', '上海蒜芽信息科技')):
        category = '城市间交通'

    return {
        'invoice_no': invoice_no,
        'date': date,
        'vendor': vendor,
        'vendor_tax_id': vendor_tax_id,
        'amount': amount,
        'tax': tax,
        'total': total,
        'category': category,
        'invoice_type': invoice_type,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 主处理逻辑：三层合并
# ─────────────────────────────────────────────────────────────────────────────

def process(file_path, deep_ocr=False, enrich_image_seller=True):
    sources = []

    # ── 第一层：QR 码 ──────────────────────────────────────────────────────
    qr_fields = {}
    for qr_text in extract_qr_codes(file_path):
        parsed = parse_invoice_qr(qr_text)
        qr_fields.update({k: v for k, v in parsed.items() if v is not None})
    if qr_fields:
        sources.append('qr')

    # ── 第二层：PDF 文本提取 ────────────────────────────────────────────────
    if is_pdf_file(file_path):
        lines, is_text_based = extract_text_from_pdf(file_path)
    else:
        lines, is_text_based = [], False

    if is_text_based:
        text_fields = extract_fields(lines)
        sources.append('text')
    else:
        if enrich_image_seller and is_image_file(file_path) and is_qr_confident(qr_fields):
            seller_fields = extract_image_seller_fields_fast(file_path)
            if seller_fields.get('vendor'):
                text_fields = extract_fields([])
                result = text_fields.copy()
                for key in ('invoice_no', 'total', 'date', 'amount', 'tax'):
                    if qr_fields.get(key) is not None:
                        result[key] = qr_fields[key]
                result['vendor'] = seller_fields['vendor']
                if seller_fields.get('vendor_tax_id'):
                    result['vendor_tax_id'] = seller_fields['vendor_tax_id']
                result['_source'] = '+'.join(sources + ['seller_crop'])
                result['_ocr_lines'] = seller_fields.get('_ocr_lines', [])
                return result

        if not deep_ocr:
            text_fields = extract_fields([])
            sources.append('qr_fast' if is_qr_confident(qr_fields) else 'ocr_skipped')
            result = text_fields.copy()
            for key in ('invoice_no', 'total', 'date', 'amount', 'tax'):
                if qr_fields.get(key) is not None:
                    result[key] = qr_fields[key]
            result['_source'] = '+'.join(sources)
            if '_ocr_lines' not in result:
                result['_ocr_lines'] = []
            return result

        # ── 第三层：OCR（扫描件兜底）─────────────────────────────────────
        try:
            lines = run_ocr(document_to_images(file_path, max_pages=1))
            text_fields = extract_fields(lines)
            sources.append('ocr')
        except Exception:
            if not qr_fields:
                raise
            lines = []
            text_fields = extract_fields(lines)
            sources.append('qr_only')

    # ── 合并：QR 字段优先（最可靠），其余用文本/OCR 补充 ──────────────────
    # QR 提供：invoice_no、total、date、amount、tax
    # 文本/OCR 提供：vendor、tax、category、invoice_type（及 QR 没有的字段）
    result = text_fields.copy()
    for key in ('invoice_no', 'total', 'date', 'amount', 'tax'):
        if qr_fields.get(key) is not None:
            result[key] = qr_fields[key]

    # 如果 QR 有 total 但文本没解析出 tax，尝试从合计行补算
    if result.get('total') and result.get('tax') and not result.get('amount'):
        result['amount'] = round(result['total'] - result['tax'], 2)

    result['_source'] = '+'.join(sources)
    result['_ocr_lines'] = lines
    return result


# ─────────────────────────────────────────────────────────────────────────────
# 入口
# ─────────────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────────────
# 目录扫描：三阶段判断
#   1) 先扫码（QR）
#   2) 再文本提取补全判断
#   3) 文本为空/低置信时做轻量 OCR（仅第一页）
# ─────────────────────────────────────────────────────────────────────────────

_SCAN_STRONG_KEYWORDS = [
    '发票代码', '发票号码', '开票日期', '价税合计', '纳税人识别号',
    '统一社会信用代码', '销售方', '购买方', '增值税',
    '航空运输电子客票行程单',
]

_SCAN_WEAK_KEYWORDS = [
    '电子发票', '普通发票', '专用发票', '税务总局', '行程单',
    '电子客票', '铁路', '票价', '酒店', '出租车',
    '航班号', '承运人', '民航发展基金', '填开单位',
]

_TRIP_ITINERARY_KEYWORDS = [
    '行程单', '滴滴出行', '网约车', '快车', '专车', '订单号',
    '上车时间', '下车时间', '行程起点', '行程终点', '实付金额',
]

_TRIP_RIDE_KEYWORDS = ['滴滴', '网约车', '快车', '专车', '出租车', '打车', '的士']

_SCAN_SCORE_CONFIDENT = 4
_SCAN_SCORE_LOW_CONF = 3
_SCAN_MODE_SET = {'fast', 'balanced', 'accurate'}

def _scan_text_score(text):
    normalized = text.replace(' ', '').replace('\t', '')
    strong_hits = [kw for kw in _SCAN_STRONG_KEYWORDS if kw in normalized]
    weak_hits = [kw for kw in _SCAN_WEAK_KEYWORDS if kw in normalized]
    score = len(strong_hits) * 2 + len(weak_hits)
    if '¥' in text or '￥' in text:
        score += 1
    return score, strong_hits, weak_hits


def _looks_like_trip_itinerary(text):
    normalized = text.replace(' ', '').replace('\t', '')
    strong_hits = sum(1 for kw in _SCAN_STRONG_KEYWORDS if kw in normalized)
    itinerary_hits = sum(1 for kw in _TRIP_ITINERARY_KEYWORDS if kw in normalized)
    ride_hits = sum(1 for kw in _TRIP_RIDE_KEYWORDS if kw in normalized)

    if strong_hits > 0:
        return False
    if '发票号码' in normalized or '发票代码' in normalized or '纳税人识别号' in normalized:
        return False

    return itinerary_hits >= 2 and ride_hits >= 1


def _scan_with_qr(file_path, mode='balanced'):
    qr_fields = {}
    for qr_text in extract_qr_codes(file_path, max_pages=1):
        parsed = parse_invoice_qr(qr_text)
        qr_fields.update({k: v for k, v in parsed.items() if v is not None})

    # 常见可靠组合：有发票号 + (金额或日期)
    qr_confident = is_qr_confident(qr_fields)
    return qr_fields, qr_confident


def _scan_with_text(file_path, mode='balanced'):
    if not is_pdf_file(file_path):
        return {
            'is_text_based': False,
            'text': '',
            'score': 0,
            'confident': False,
            'low_confidence': True,
            'trip_itinerary': False,
        }

    max_pages = 1 if mode == 'fast' else 2
    lines, is_text_based = extract_text_from_pdf(file_path, max_pages=max_pages)
    text = '\n'.join(lines) if lines else ''
    score, strong_hits, _ = _scan_text_score(text)
    confident = len(strong_hits) >= 2 or score >= _SCAN_SCORE_CONFIDENT
    low_confidence = (not is_text_based) or score < _SCAN_SCORE_LOW_CONF
    return {
        'is_text_based': is_text_based,
        'text': text,
        'score': score,
        'confident': confident,
        'low_confidence': low_confidence,
        'trip_itinerary': _looks_like_trip_itinerary(text),
    }


def _scan_with_light_ocr(file_path):
    try:
        lines = run_ocr(document_to_images(file_path, max_pages=1))
    except Exception:
        lines = []
    text = '\n'.join(lines) if lines else ''
    score, strong_hits, _ = _scan_text_score(text)
    confident = len(strong_hits) >= 2 or score >= _SCAN_SCORE_CONFIDENT
    return {'score': score, 'confident': confident, 'trip_itinerary': _looks_like_trip_itinerary(text)}


def _classify_document_kind(file_path, mode='balanced'):
    qr_fields, qr_confident = _scan_with_qr(file_path, mode=mode)
    if qr_confident:
        return 'invoice'

    text_result = _scan_with_text(file_path, mode=mode)
    if text_result['trip_itinerary']:
        return 'trip_itinerary'
    if text_result['confident']:
        return 'invoice'

    allow_light_ocr = mode != 'fast' or is_image_file(file_path)
    if allow_light_ocr and text_result['low_confidence']:
        ocr_result = _scan_with_light_ocr(file_path)
        if ocr_result['trip_itinerary']:
            return 'trip_itinerary'
        if ocr_result['confident']:
            return 'invoice'

    # QR 有部分字段时，放宽为候选发票（降低漏判）
    if mode in ('balanced', 'accurate') and (qr_fields.get('invoice_no') or qr_fields.get('total') is not None):
        return 'invoice'

    return 'other'

def _scan_one_document(args):
    file_path, mode = args
    return file_path, _classify_document_kind(file_path, mode=mode)


def scan_folder_for_invoices(folder_path, mode='balanced'):
    """递归扫描目录，返回所有支持格式中属于发票的路径列表"""
    if mode not in _SCAN_MODE_SET:
        mode = 'balanced'

    document_paths = []
    for root, dirs, files in os.walk(folder_path):
        dirs.sort()
        for fname in sorted(files):
            if not fname.startswith('.') and is_supported_document(fname):
                document_paths.append(os.path.join(root, fname))

    invoices = []
    trip_itineraries = []
    non_invoices = []

    def add_classified_path(full_path, document_kind):
        if document_kind == 'invoice':
            invoices.append(full_path)
        elif document_kind == 'trip_itinerary':
            trip_itineraries.append(full_path)
        else:
            non_invoices.append(full_path)

    # Keep scan classification sequential. PyMuPDF/OpenCV calls used by QR
    # extraction can crash the whole Python process when run from threads on
    # Windows, which makes Electron receive no JSON result from scan-folder.
    if mode == 'fast' and document_paths:
        pdf_paths = [p for p in document_paths if is_pdf_file(p)]
        image_paths = [p for p in document_paths if is_image_file(p)]
        for full_path in pdf_paths:
            add_classified_path(full_path, _classify_document_kind(full_path, mode=mode))
        for full_path in image_paths:
            add_classified_path(full_path, _classify_document_kind(full_path, mode=mode))
    else:
        for full_path in document_paths:
            document_kind = _classify_document_kind(full_path, mode=mode)
            add_classified_path(full_path, document_kind)

    return {
        'total': len(document_paths),
        'invoices': invoices,
        'trip_itineraries': trip_itineraries,
        'non_invoices': non_invoices,
    }


def main():
    if len(sys.argv) >= 3 and sys.argv[1] == '--scan':
        folder = sys.argv[2]
        mode = 'balanced'
        if '--mode' in sys.argv:
            mode_idx = sys.argv.index('--mode')
            if mode_idx + 1 < len(sys.argv):
                mode = sys.argv[mode_idx + 1].strip().lower()

        if not os.path.isdir(folder):
            print(json.dumps({'error': f'目录不存在: {folder}'}))
            sys.exit(1)
        if mode not in _SCAN_MODE_SET:
            print(json.dumps({'error': f'不支持的扫描模式: {mode}'}))
            sys.exit(1)
        result = scan_folder_for_invoices(folder, mode=mode)
        print(json.dumps(result, ensure_ascii=False))
        return

    if len(sys.argv) >= 2 and sys.argv[1] == '--server':
        # 常驻模式：先启动进程，按需懒加载 OCR 模型。这样 QR-only 发票不受 OCR 模型故障影响。
        sys.stdout.write(json.dumps({'_ready': True}) + '\n')
        sys.stdout.flush()

        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            req = {}
            try:
                req = json.loads(line)
                req_id = req.get('id', '')
                file_path = req.get('path', '')
                if file_path == '__test__':
                    get_ocr()
                    result = {'ok': True}
                elif not os.path.exists(file_path):
                    result = {'error': f'文件不存在: {file_path}'}
                else:
                    result = process(
                        file_path,
                        deep_ocr=bool(req.get('deep_ocr')),
                        enrich_image_seller=req.get('enrich_image_seller') is not False
                    )
                result['id'] = req_id
            except Exception as e:
                result = {'id': req.get('id', ''), 'error': str(e)}
            sys.stdout.write(json.dumps(result, ensure_ascii=False) + '\n')
            sys.stdout.flush()

    else:
        if len(sys.argv) < 2:
            print(json.dumps({'error': '用法: ocr.py <pdf_path>'}))
            sys.exit(1)
        pdf_path = sys.argv[1]
        if not os.path.exists(pdf_path):
            print(json.dumps({'error': f'文件不存在: {pdf_path}'}))
            sys.exit(1)
        try:
            result = process(pdf_path)
            print(json.dumps(result, ensure_ascii=False))
        except Exception as e:
            print(json.dumps({'error': str(e)}))
            sys.exit(1)


if __name__ == '__main__':
    main()
