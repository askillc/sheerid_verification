# -*- coding: utf-8 -*-
"""
Transcript Generator
Tạo transcript từ template HTML, render thành hình ảnh và upload

Render methods (priority order for Vercel):
1. Satori/OG Edge Function - Tối ưu nhất, miễn phí, không giới hạn
2. External APIs (HCTI, ApiFlash, ScreenshotOne) - Miễn phí có giới hạn
3. Pillow fallback - Luôn hoạt động
"""

import os
import random
import asyncio
import io
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode


def optimize_image(image_path_or_bytes, output_path=None, max_size_kb=500, quality_start=95):
    """
    Tối ưu ảnh PNG/JPEG để giảm dung lượng nhưng giữ chất lượng
    
    Args:
        image_path_or_bytes: Đường dẫn file ảnh hoặc bytes
        output_path: Đường dẫn output (None = overwrite)
        max_size_kb: Dung lượng tối đa mong muốn (KB)
        quality_start: Chất lượng bắt đầu (95 = cao nhất)
    
    Returns:
        bytes hoặc str: Ảnh đã tối ưu (bytes nếu input là bytes, path nếu input là path)
    """
    try:
        from PIL import Image
    except ImportError:
        print("⚠️ Pillow not installed, skipping optimization")
        return image_path_or_bytes
    
    # Load image
    if isinstance(image_path_or_bytes, bytes):
        img = Image.open(io.BytesIO(image_path_or_bytes))
        is_bytes = True
    else:
        img = Image.open(image_path_or_bytes)
        is_bytes = False
        if output_path is None:
            output_path = image_path_or_bytes
    
    # Convert RGBA to RGB if needed (for JPEG)
    if img.mode == 'RGBA':
        # Create white background
        background = Image.new('RGB', img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[3])  # Use alpha channel as mask
        img = background
    elif img.mode != 'RGB':
        img = img.convert('RGB')
    
    # Try different quality levels to meet size target
    quality = quality_start
    max_bytes = max_size_kb * 1024
    
    while quality >= 60:
        buffer = io.BytesIO()
        # Save as JPEG for better compression
        img.save(buffer, format='JPEG', quality=quality, optimize=True)
        size = buffer.tell()
        
        if size <= max_bytes:
            print(f"✅ Image optimized: {size/1024:.1f}KB (quality={quality})")
            break
        
        quality -= 5
    
    if is_bytes:
        buffer.seek(0)
        return buffer.read()
    else:
        # Save to file
        buffer.seek(0)
        with open(output_path, 'wb') as f:
            f.write(buffer.read())
        print(f"✅ Saved optimized image to {output_path}")
        return output_path


def optimize_png_image(image_path_or_bytes, output_path=None, colors=256):
    """
    Tối ưu ảnh PNG bằng cách giảm số màu (palette)
    Giữ định dạng PNG nhưng giảm dung lượng đáng kể
    
    Args:
        image_path_or_bytes: Đường dẫn file ảnh hoặc bytes
        output_path: Đường dẫn output (None = overwrite)
        colors: Số màu tối đa (256 = tốt nhất cho PNG-8)
    
    Returns:
        bytes hoặc str: Ảnh đã tối ưu
    """
    try:
        from PIL import Image
    except ImportError:
        print("⚠️ Pillow not installed, skipping optimization")
        return image_path_or_bytes
    
    # Load image
    if isinstance(image_path_or_bytes, bytes):
        img = Image.open(io.BytesIO(image_path_or_bytes))
        is_bytes = True
    else:
        img = Image.open(image_path_or_bytes)
        is_bytes = False
        if output_path is None:
            output_path = image_path_or_bytes
    
    # Convert to palette mode (PNG-8) for smaller size
    if img.mode == 'RGBA':
        # Preserve transparency
        img = img.convert('P', palette=Image.ADAPTIVE, colors=colors)
    else:
        img = img.convert('P', palette=Image.ADAPTIVE, colors=colors)
    
    buffer = io.BytesIO()
    img.save(buffer, format='PNG', optimize=True)
    
    size = buffer.tell()
    print(f"✅ PNG optimized: {size/1024:.1f}KB (colors={colors})")
    
    if is_bytes:
        buffer.seek(0)
        return buffer.read()
    else:
        buffer.seek(0)
        with open(output_path, 'wb') as f:
            f.write(buffer.read())
        return output_path

# Import config - support both direct run and module import
try:
    from .universities_config import (
        get_random_university,
        get_random_student_name,
        get_random_dob,
        generate_student_id,
        generate_ssn_masked,
        get_random_courses,
        calculate_gpa,
        UNIVERSITIES
    )
except ImportError:
    from universities_config import (
        get_random_university,
        get_random_student_name,
        get_random_dob,
        generate_student_id,
        generate_ssn_masked,
        get_random_courses,
        calculate_gpa,
        UNIVERSITIES
    )


def get_template_path():
    """Lấy đường dẫn template"""
    current_dir = Path(__file__).parent
    return current_dir / "transcript.html"


def generate_courses_html(courses):
    """Tạo HTML cho bảng môn học"""
    rows = []
    for course in courses:
        row = f"""
                <tr>
                    <td>{course['code']}</td>
                    <td>{course['title']}</td>
                    <td>{course['credits']}</td>
                    <td>{course['grade']}</td>
                    <td>{course['term']}</td>
                </tr>"""
        rows.append(row)
    return "\n".join(rows)


def generate_transcript_html(
    university=None,
    first_name=None,
    last_name=None,
    dob=None,
    student_id=None,
    ssn=None,
    program=None,
    courses=None,
    expected_graduation=None
):
    """
    Tạo HTML transcript với dữ liệu được cung cấp hoặc random
    
    Args:
        university: dict chứa thông tin trường (nếu None sẽ random)
        first_name: Tên (nếu None sẽ random)
        last_name: Họ (nếu None sẽ random)
        dob: Ngày sinh (nếu None sẽ random - năm 2002-2005)
        student_id: Mã sinh viên (nếu None sẽ random)
        ssn: SSN masked (nếu None sẽ random)
        program: Chương trình học (nếu None sẽ random từ university)
        courses: Danh sách môn học (nếu None sẽ random)
        expected_graduation: Ngày tốt nghiệp dự kiến
    
    Returns:
        str: HTML content đã được fill
    """
    from datetime import timedelta
    
    # Import issue date function
    try:
        from .universities_config import get_random_issue_date
    except ImportError:
        from universities_config import get_random_issue_date
    
    # Random nếu không có dữ liệu
    if university is None:
        university = get_random_university()
    
    if first_name is None or last_name is None:
        name = get_random_student_name()
        first_name = first_name or name["first_name"]
        last_name = last_name or name["last_name"]
    
    # Năm sinh random từ 2002-2005
    if dob is None:
        dob = get_random_dob()
    
    if student_id is None:
        student_id = generate_student_id(university)
    
    if ssn is None:
        ssn = generate_ssn_masked()
    
    if program is None:
        program = random.choice(university["programs"])
    
    if courses is None:
        courses = get_random_courses(6)
    
    if expected_graduation is None:
        grad_year = random.randint(2025, 2027)
        expected_graduation = f"May {grad_year}"
    
    # Random GPA - US scale (0.0-4.0)
    gpa = round(random.uniform(3.20, 3.95), 2)
    total_credits = random.randint(60, 120)  # US credits (3 per course)
    
    # Issue date trong vòng 90 ngày gần đây
    issue_date = get_random_issue_date()
    
    # Generate enrollment number
    enrollment_number = f"{random.randint(20, 24)}{random.randint(1000000, 9999999)}"
    
    # Generate dates based on birth year
    birth_year = int(dob.split(", ")[-1])
    start_year = birth_year + 18  # Bắt đầu học năm 18 tuổi
    grad_year = start_year + random.randint(3, 4)
    
    start_month = random.choice(["01", "08", "09"])
    start_day = random.randint(1, 28)
    start_date = f"{start_month}/{start_day:02d}/{str(start_year)[-2:]}"
    
    grad_month = random.choice(["05", "12"])
    grad_day = random.randint(15, 25)
    grad_date = f"{grad_month}/{grad_day:02d}/{str(grad_year)[-2:]}"
    
    # Last date attended (gần với ngày hiện tại)
    today = datetime.now()
    lda_days_ago = random.randint(30, 180)
    lda = today - timedelta(days=lda_days_ago)
    last_date_attended = lda.strftime("%m/%d/%Y")
    
    # Random student address
    street_numbers = random.randint(100, 9999)
    streets = ["Oak St", "Main St", "Elm Ave", "Park Blvd", "Cedar Ln", "Maple Dr", "Pine Rd", "Lake View Dr"]
    cities = ["Austin", "Denver", "Phoenix", "Seattle", "Portland", "Atlanta", "Miami", "Chicago"]
    states = ["TX", "CO", "AZ", "WA", "OR", "GA", "FL", "IL"]
    city_idx = random.randint(0, len(cities) - 1)
    zip_code = random.randint(10000, 99999)
    student_address = f"{street_numbers} {random.choice(streets)}<br>{cities[city_idx]}, {states[city_idx]} {zip_code}"
    
    # Transfer from colleges
    transfer_colleges = [
        "ROANE STATE COMMUNITY COLLEGE",
        "AUSTIN COMMUNITY COLLEGE",
        "DENVER COMMUNITY COLLEGE",
        "PHOENIX COLLEGE",
        "SEATTLE CENTRAL COLLEGE",
        "PORTLAND COMMUNITY COLLEGE",
        "ATLANTA TECHNICAL COLLEGE",
        "MIAMI DADE COLLEGE"
    ]
    transfer_from = random.choice(transfer_colleges)
    
    # Read template
    template_path = get_template_path()
    with open(template_path, "r", encoding="utf-8") as f:
        template = f.read()
    
    # Generate Tax Invoice specific data
    # Payment date within last 60 days (format: DD/MM/YYYY)
    payment_days_ago = random.randint(0, 60)
    payment_date_obj = today - timedelta(days=payment_days_ago)
    payment_date = payment_date_obj.strftime("%d/%m/%Y")
    
    # Generate random amounts for tuition fees
    unit_amount1 = random.randint(1800, 3500)
    unit_amount2 = random.randint(3000, 5500)
    total_amount = unit_amount1 + unit_amount2
    
    # Generate invoice number: PREFIX + 8 digits
    invoice_prefix = university.get("invoice_prefix", "CQUP")
    invoice_no = f"{invoice_prefix}{random.randint(10000000, 99999999)}"
    
    # Generate bank auth: NAB + 6 digits
    bank_auth = f"NAB {random.randint(100000, 999999)}"
    
    # Generate ref number: WEB + 7 digits
    ref_number = f"WEB{random.randint(1000000, 9999999)}"
    
    # Get fee codes from university config
    fee_codes = university.get("fee_codes", ["COIT20250", "COIT20265"])
    fee_description1 = f"International Tuition Fee {fee_codes[0]}"
    fee_description2 = f"International Tuition Fee {fee_codes[1] if len(fee_codes) > 1 else fee_codes[0]}"
    
    # Footer datetime format: DD/M/YY, H:MM pm (same date as payment)
    # Windows doesn't support %-d, use manual formatting
    footer_datetime = f"{payment_date_obj.day}/{payment_date_obj.month}/{payment_date_obj.strftime('%y')}, {random.randint(8, 17)}:{random.randint(10, 59):02d} {'am' if random.random() < 0.5 else 'pm'}"
    
    # Replace all placeholders (Tax Invoice format)
    replacements = {
        # University info
        "{{universityName}}": university["name"],
        "{{universityLogo}}": university.get("logo", ""),
        "{{universityDepartment}}": university.get("department", "Financial Services Division"),
        "{{universityBuilding}}": university.get("building", ""),
        "{{universityStreet}}": university.get("street", ""),
        "{{universityCity}}": university.get("full_city", f"{university.get('city', '')} {university.get('state', '')}"),
        "{{universityPhone}}": university.get("phone", ""),
        "{{universityABN}}": university.get("abn", ""),
        
        # Payer info
        "{{firstName}}": first_name,
        "{{lastName}}": last_name,
        "{{paymentDate}}": payment_date,
        "{{totalValue}}": f"{total_amount:,.2f}",
        "{{paymentProcessed}}": f"{total_amount:,.2f}",
        "{{invoiceNo}}": invoice_no,
        "{{bankAuth}}": bank_auth,
        "{{refNumber}}": ref_number,
        
        # Receipt items
        "{{studentId}}": student_id,
        "{{feeDescription1}}": fee_description1,
        "{{unitAmount1}}": f"{unit_amount1:,.2f}",
        "{{amount1}}": f"{unit_amount1:,.2f}",
        "{{feeDescription2}}": fee_description2,
        "{{unitAmount2}}": f"{unit_amount2:,.2f}",
        "{{amount2}}": f"{unit_amount2:,.2f}",
        
        # Totals
        "{{totalAmount}}": f"{total_amount:,.2f}",
        "{{taxAmount}}": "0.00",
        
        # Footer
        "{{footerDateTime}}": footer_datetime
    }
    
    html = template
    for placeholder, value in replacements.items():
        html = html.replace(placeholder, str(value))
    
    return html, {
        "university": university,
        "first_name": first_name,
        "last_name": last_name,
        "dob": dob,
        "student_id": student_id,
        "ssn": ssn,
        "program": program,
        "gpa": gpa,
        "total_credits": total_credits,
        "expected_graduation": expected_graduation,
        "issue_date": issue_date,
        "payment_date": payment_date,
        "total_amount": total_amount,
        "invoice_no": invoice_no
    }


def render_transcript_with_pillow(transcript_info, output_path="transcript.png"):
    """
    Render Tax Invoice/Receipt thành image bằng Pillow (fallback cho Vercel)
    Format giống CQ University Tax Invoice/Receipt
    """
    from PIL import Image, ImageDraw, ImageFont
    import os
    import requests
    from io import BytesIO
    
    # Create image - A4 ratio
    width, height = 800, 1100
    img = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(img)
    
    # Try to load fonts
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "DejaVuSans-Bold.ttf",
        "DejaVuSans.ttf",
        "arialbd.ttf",
        "arial.ttf"
    ]
    
    def load_font(size, bold=False):
        for path in font_paths:
            if bold and 'Bold' in path:
                try:
                    return ImageFont.truetype(path, size)
                except:
                    pass
            elif not bold and 'Bold' not in path:
                try:
                    return ImageFont.truetype(path, size)
                except:
                    pass
        return ImageFont.load_default()
    
    title_font = load_font(16, bold=True)
    header_font = load_font(10, bold=True)
    label_font = load_font(10, bold=False)
    value_font = load_font(10, bold=False)
    small_font = load_font(9, bold=False)
    bold_font = load_font(10, bold=True)
    
    # Colors
    black = (0, 0, 0)
    gray = (102, 102, 102)
    
    # Margins
    left_margin = 50
    right_margin = width - 50
    
    y = 40
    
    # Header: TAX INVOICE / RECEIPT title
    draw.text((left_margin, y), "TAX INVOICE / RECEIPT", fill=black, font=title_font)
    
    # Try to load and paste university logo
    university = transcript_info['university']
    logo_url = university.get('logo', '')
    if logo_url:
        try:
            response = requests.get(logo_url, timeout=5)
            if response.status_code == 200:
                logo_img = Image.open(BytesIO(response.content))
                # Resize logo to fit
                logo_img.thumbnail((150, 60), Image.Resampling.LANCZOS)
                # Convert to RGB if needed
                if logo_img.mode == 'RGBA':
                    bg = Image.new('RGB', logo_img.size, (255, 255, 255))
                    bg.paste(logo_img, mask=logo_img.split()[3])
                    logo_img = bg
                # Paste logo at top right
                logo_x = right_margin - logo_img.width
                img.paste(logo_img, (logo_x, y - 10))
        except:
            pass  # Skip logo if can't load
    
    y += 50
    
    # SUMMARY section
    draw.line([(left_margin, y), (right_margin, y)], fill=black, width=1)
    y += 8
    draw.text((left_margin, y), "SUMMARY", fill=black, font=header_font)
    y += 15
    draw.line([(left_margin, y), (right_margin, y)], fill=black, width=1)
    y += 15
    
    # Summary content - two columns
    col1_x = left_margin
    col2_x = 500
    
    first_name = transcript_info['first_name']
    last_name = transcript_info['last_name']
    student_id = transcript_info.get('student_id', 'AI202558968')
    # Payment date within last 60 days
    if 'payment_date' in transcript_info:
        payment_date = transcript_info['payment_date']
    else:
        days_ago = random.randint(0, 60)
        payment_date = (datetime.now() - timedelta(days=days_ago)).strftime("%d/%m/%Y")
    total_amount = transcript_info.get('total_amount', 7128)
    invoice_no = transcript_info.get('invoice_no', 'CQUP10105611')
    
    # Left column - Payer info
    info_items = [
        ("Payer:", f"{first_name} {last_name}"),
        ("Payment Date:", payment_date),
        ("Total Value:", f"${total_amount:,.2f}"),
        ("Payment Processed:", f"${total_amount:,.2f}"),
        ("Payment/Invoice No:", invoice_no),
        ("Bank Auth:", f"NAB {random.randint(100000, 999999)}"),
        ("Ref Number:", f"WEB{random.randint(1000000, 9999999)}")
    ]
    
    for label, value in info_items:
        draw.text((col1_x, y), label, fill=black, font=label_font)
        draw.text((col1_x + 120, y), value, fill=black, font=value_font)
        y += 16
    
    # Right column - University info (positioned at top of summary)
    right_y = 130
    draw.text((col2_x, right_y), university['name'], fill=black, font=bold_font)
    right_y += 14
    draw.text((col2_x, right_y), university.get('department', 'Financial Services Division'), fill=black, font=small_font)
    right_y += 18
    draw.text((col2_x, right_y), university.get('building', ''), fill=black, font=small_font)
    right_y += 12
    draw.text((col2_x, right_y), university.get('street', ''), fill=black, font=small_font)
    right_y += 18
    draw.text((col2_x, right_y), university.get('full_city', ''), fill=black, font=small_font)
    right_y += 18
    draw.text((col2_x, right_y), f"Phone {university.get('phone', '')}", fill=black, font=small_font)
    right_y += 14
    draw.text((col2_x, right_y), university.get('abn', ''), fill=black, font=bold_font)
    
    y += 10
    draw.line([(left_margin, y), (right_margin, y)], fill=black, width=1)
    y += 30
    
    # RECEIPT DESCRIPTION section
    draw.line([(left_margin, y), (right_margin, y)], fill=black, width=1)
    y += 8
    
    # Table header
    col_desc = left_margin
    col_qty = 420
    col_unit = 500
    col_amt = 620
    
    draw.text((col_desc, y), "RECEIPT DESCRIPTION", fill=black, font=header_font)
    draw.text((col_qty, y), "QUANTITY", fill=black, font=header_font)
    draw.text((col_unit, y), "UNIT AMOUNT", fill=black, font=header_font)
    draw.text((col_amt, y), "AMOUNT", fill=black, font=header_font)
    y += 15
    draw.line([(left_margin, y), (right_margin, y)], fill=black, width=1)
    y += 15
    
    # Receipt items
    fee_codes = university.get('fee_codes', ['COIT20250', 'COIT20265'])
    unit_amount1 = random.randint(1800, 3500)
    unit_amount2 = random.randint(3000, 5500)
    
    # Item 1
    draw.text((col_desc, y), "Student Online Payment", fill=black, font=value_font)
    draw.text((col_qty, y), "1", fill=black, font=value_font)
    draw.text((col_unit, y), f"${unit_amount1:,.2f}", fill=black, font=value_font)
    draw.text((col_amt, y), f"${unit_amount1:,.2f}", fill=black, font=value_font)
    y += 14
    draw.text((col_desc + 20, y), f"{student_id} {first_name} {last_name}", fill=black, font=small_font)
    y += 12
    draw.text((col_desc + 20, y), f"International Tuition Fee {fee_codes[0]}", fill=black, font=small_font)
    y += 25
    
    # Item 2
    draw.text((col_desc, y), "Student Online Payment", fill=black, font=value_font)
    draw.text((col_qty, y), "1", fill=black, font=value_font)
    draw.text((col_unit, y), f"${unit_amount2:,.2f}", fill=black, font=value_font)
    draw.text((col_amt, y), f"${unit_amount2:,.2f}", fill=black, font=value_font)
    y += 14
    draw.text((col_desc + 20, y), f"{student_id} {first_name} {last_name}", fill=black, font=small_font)
    y += 12
    fee_code2 = fee_codes[1] if len(fee_codes) > 1 else fee_codes[0]
    draw.text((col_desc + 20, y), f"International Tuition Fee {fee_code2}", fill=black, font=small_font)
    y += 20
    
    # Total row
    total = unit_amount1 + unit_amount2
    draw.line([(left_margin, y), (right_margin, y)], fill=black, width=1)
    y += 10
    draw.text((col_desc, y), "TOTAL", fill=black, font=bold_font)
    draw.text((col_amt, y), f"${total:,.2f}", fill=black, font=bold_font)
    y += 15
    draw.line([(left_margin, y), (right_margin, y)], fill=black, width=1)
    y += 30
    
    # TAX SUMMARY section
    draw.line([(left_margin, y), (right_margin, y)], fill=black, width=1)
    y += 8
    draw.text((left_margin, y), "TAX SUMMARY", fill=black, font=header_font)
    y += 15
    draw.line([(left_margin, y), (right_margin, y)], fill=black, width=1)
    y += 15
    draw.text((col_amt, y), "$0.00", fill=black, font=value_font)
    y += 15
    draw.line([(left_margin, y), (right_margin, y)], fill=black, width=1)
    
    # Footer
    y = height - 50
    draw.text((left_margin, y), "1 of 1", fill=black, font=small_font)
    footer_date = datetime.now().strftime("%d/%m/%y, %I:%M %p").lower()
    draw.text((right_margin - 100, y), footer_date, fill=black, font=small_font)
    
    # Save as PNG
    if not output_path.endswith('.png'):
        output_path = output_path.replace('.jpg', '.png')
    
    img.save(output_path, 'PNG', optimize=True)
    
    # Check file size
    file_size = os.path.getsize(output_path)
    print(f"✅ Tax Invoice saved: {output_path} ({file_size/1024:.1f}KB)")
    
    return output_path


async def render_html_to_image(html_content, output_path="transcript.png"):
    """
    Render HTML thành hình ảnh sử dụng Playwright
    
    Args:
        html_content: Nội dung HTML
        output_path: Đường dẫn file output
    
    Returns:
        str: Đường dẫn file ảnh đã tạo
    
    Raises:
        ImportError: If Playwright is not available
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        raise ImportError("Playwright not available - use render_transcript_with_pillow instead")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 900, "height": 1200})
        
        # Set HTML content
        await page.set_content(html_content)
        
        # Wait for render
        await page.wait_for_timeout(500)
        
        # Screenshot element
        cert_element = await page.query_selector(".cert-container")
        if cert_element:
            await cert_element.screenshot(path=output_path)
        else:
            await page.screenshot(path=output_path, full_page=True)
        
        await browser.close()
    
    return output_path


def render_html_to_image_sync(html_content, output_path="transcript.png"):
    """Sync wrapper cho render_html_to_image - raises ImportError if Playwright unavailable"""
    return asyncio.run(render_html_to_image(html_content, output_path))


def render_html_with_imgkit(html_content, output_path="transcript.png"):
    """
    Render HTML to image using imgkit (wkhtmltoimage)
    FREE - No API limits, runs locally
    
    Requires: pip install imgkit
    And wkhtmltopdf installed: https://wkhtmltopdf.org/downloads.html
    """
    try:
        import imgkit
    except ImportError:
        raise ImportError("imgkit not installed. Run: pip install imgkit")
    
    # Options for high quality rendering
    options = {
        'format': 'png',
        'width': 800,
        'quality': 100,
        'enable-local-file-access': None,
        'encoding': 'UTF-8',
        'quiet': ''
    }
    
    try:
        imgkit.from_string(html_content, output_path, options=options)
        print(f"✅ Rendered with imgkit to {output_path}")
        return output_path
    except Exception as e:
        raise Exception(f"imgkit error: {e}")


def render_html_with_weasyprint(html_content, output_path="transcript.png"):
    """
    Render HTML to image using WeasyPrint + Pillow
    FREE - No API limits, pure Python
    
    Requires: pip install weasyprint pillow
    """
    try:
        from weasyprint import HTML
        from PIL import Image
        import io
    except ImportError:
        raise ImportError("weasyprint not installed. Run: pip install weasyprint pillow")
    
    # First render to PDF
    pdf_bytes = HTML(string=html_content).write_pdf()
    
    # Convert PDF to PNG using pdf2image or similar
    # For simplicity, we'll save as PDF first then convert
    try:
        from pdf2image import convert_from_bytes
        images = convert_from_bytes(pdf_bytes, dpi=150)
        if images:
            images[0].save(output_path, 'PNG')
            print(f"✅ Rendered with WeasyPrint to {output_path}")
            return output_path
    except ImportError:
        # Fallback: save as PDF
        pdf_path = output_path.replace('.png', '.pdf')
        with open(pdf_path, 'wb') as f:
            f.write(pdf_bytes)
        raise Exception(f"pdf2image not available. PDF saved to {pdf_path}")


def render_html_with_selenium(html_content, output_path="transcript.png"):
    """
    Render HTML to image using Selenium + Chrome
    FREE - No API limits
    
    Requires: pip install selenium webdriver-manager
    """
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        import tempfile
        import time
    except ImportError:
        raise ImportError("selenium not installed. Run: pip install selenium webdriver-manager")
    
    # Create temp HTML file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
        f.write(html_content)
        temp_html = f.name
    
    try:
        # Setup Chrome options
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--window-size=900,1200')
        
        # Try to use webdriver-manager for auto driver management
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
        except:
            driver = webdriver.Chrome(options=chrome_options)
        
        # Load HTML
        driver.get(f'file://{temp_html}')
        time.sleep(0.5)  # Wait for render
        
        # Find element and screenshot
        element = driver.find_element("css selector", ".cert-container")
        element.screenshot(output_path)
        
        driver.quit()
        print(f"✅ Rendered with Selenium to {output_path}")
        return output_path
        
    finally:
        import os
        os.unlink(temp_html)


def render_html_with_hcti(html_content, output_path="transcript.png"):
    """
    Render HTML to image using hcti.io API (html-css-to-image)
    Free tier: 50 images/month
    
    Requires HCTI_USER_ID and HCTI_API_KEY environment variables
    """
    import requests
    
    user_id = os.getenv("HCTI_USER_ID")
    api_key = os.getenv("HCTI_API_KEY")
    
    if not user_id or not api_key:
        raise ValueError("HCTI_USER_ID and HCTI_API_KEY not configured")
    
    # Call hcti.io API
    response = requests.post(
        "https://hcti.io/v1/image",
        auth=(user_id, api_key),
        data={
            "html": html_content,
            "css": "",
            "google_fonts": "Arial"
        },
        timeout=30
    )
    
    if response.status_code != 200:
        raise Exception(f"HCTI API error: {response.status_code} - {response.text}")
    
    result = response.json()
    image_url = result.get("url")
    
    if not image_url:
        raise Exception("HCTI API did not return image URL")
    
    # Download image
    img_response = requests.get(image_url, timeout=30)
    if img_response.status_code != 200:
        raise Exception(f"Failed to download image from HCTI")
    
    # Save to file
    with open(output_path, "wb") as f:
        f.write(img_response.content)
    
    print(f"✅ Rendered with HCTI API to {output_path}")
    return output_path


def render_html_with_apiflash(html_content, output_path="transcript.png"):
    """
    Render HTML to image using ApiFlash (screenshot API)
    Free tier: 100 screenshots/month
    
    Requires APIFLASH_ACCESS_KEY environment variable
    Sign up: https://apiflash.com/
    """
    import requests
    import base64
    import tempfile
    
    access_key = os.getenv("APIFLASH_ACCESS_KEY")
    
    if not access_key:
        raise ValueError("APIFLASH_ACCESS_KEY not configured")
    
    # Save HTML to temp file and encode as data URL
    html_base64 = base64.b64encode(html_content.encode('utf-8')).decode('utf-8')
    data_url = f"data:text/html;base64,{html_base64}"
    
    # Call ApiFlash API
    params = {
        "access_key": access_key,
        "url": data_url,
        "width": 800,
        "height": 1100,
        "format": "png",
        "quality": 100,
        "full_page": "false",
        "fresh": "true"
    }
    
    response = requests.get(
        "https://api.apiflash.com/v1/urltoimage",
        params=params,
        timeout=30
    )
    
    if response.status_code != 200:
        raise Exception(f"ApiFlash error: {response.status_code}")
    
    # Save image
    with open(output_path, "wb") as f:
        f.write(response.content)
    
    print(f"✅ Rendered with ApiFlash to {output_path}")
    return output_path


def render_html_with_screenshotone(html_content, output_path="transcript.png"):
    """
    Render HTML to image using ScreenshotOne API
    Free tier: 100 screenshots/month
    
    Requires SCREENSHOTONE_ACCESS_KEY environment variable
    Sign up: https://screenshotone.com/
    """
    import requests
    import base64
    
    access_key = os.getenv("SCREENSHOTONE_ACCESS_KEY")
    
    if not access_key:
        raise ValueError("SCREENSHOTONE_ACCESS_KEY not configured")
    
    # Encode HTML as base64
    html_base64 = base64.b64encode(html_content.encode('utf-8')).decode('utf-8')
    
    # Call ScreenshotOne API with HTML
    params = {
        "access_key": access_key,
        "html": html_content,
        "viewport_width": 800,
        "viewport_height": 1100,
        "format": "png",
        "full_page": "false"
    }
    
    response = requests.get(
        "https://api.screenshotone.com/take",
        params=params,
        timeout=30
    )
    
    if response.status_code != 200:
        raise Exception(f"ScreenshotOne error: {response.status_code} - {response.text}")
    
    # Save image
    with open(output_path, "wb") as f:
        f.write(response.content)
    
    print(f"✅ Rendered with ScreenshotOne to {output_path}")
    return output_path


def render_with_satori_edge(transcript_info):
    """
    Render transcript using Satori/OG Edge Function
    TỐI ƯU NHẤT cho Vercel - miễn phí, không giới hạn, render chính xác
    
    Gọi /api/og-transcript Edge Function
    
    Returns:
        bytes: PNG image data
    """
    import requests
    
    # Use production URL to avoid deployment protection issues
    # VERCEL_URL points to preview deployment which requires auth
    base_url = os.getenv("PRODUCTION_URL", "https://sheerid-verify-pro.vercel.app")
    
    # Build query params cho Tax Invoice format - US format
    university = transcript_info["university"]
    params = {
        # University info
        "university": university["name"],
        "universityDepartment": university.get("department", "Office of the Registrar"),
        "universityBuilding": university.get("building", "3501 University Blvd East"),
        "universityStreet": university.get("street", "Adelphi"),
        "universityCity": university.get("full_city", "Adelphi, MD 20783"),
        "universityPhone": university.get("phone", "(800) 888-8682"),
        "universityABN": university.get("abn", ""),  # US universities don't have ABN
        # Payer info
        "firstName": transcript_info["first_name"],
        "lastName": transcript_info["last_name"],
        "studentId": transcript_info.get("student_id", "12345678"),
        "paymentDate": transcript_info.get("payment_date", datetime.now().strftime("%m/%d/%Y")),
        "invoiceNo": transcript_info.get("invoice_no", f"UMGC{random.randint(10000000, 99999999)}"),
        "bankAuth": f"AUTH {random.randint(100000, 999999)}",
        "refNumber": f"REF{random.randint(1000000, 9999999)}",
        # Fee items - US tuition format
        "feeDescription1": f"Tuition - {university.get('fee_codes', ['CMSC'])[0]}",
        "feeDescription2": f"Tuition - {university.get('fee_codes', ['CMSC', 'CMIT'])[-1]}",
        "unitAmount1": f"{transcript_info.get('unit_amount1', random.randint(1200, 2500)):,.2f}",
        "unitAmount2": f"{transcript_info.get('unit_amount2', random.randint(1500, 3000)):,.2f}",
        "totalAmount": f"{transcript_info.get('total_amount', 4500):,.2f}",
        "taxAmount": "0.00",
        "footerDateTime": transcript_info.get("footer_datetime", datetime.now().strftime("%m/%d/%y, %I:%M %p").lower())
    }
    
    # Call Edge Function with bypass header for deployment protection
    url = f"{base_url}/api/og-transcript?{urlencode(params)}"
    print(f"🔄 Calling Satori Edge Function: {url}")
    
    # Add bypass header if configured
    headers = {}
    bypass_token = os.getenv("VERCEL_AUTOMATION_BYPASS_SECRET")
    if bypass_token:
        headers["x-vercel-protection-bypass"] = bypass_token
    
    response = requests.get(url, headers=headers, timeout=30)
    
    if response.status_code == 200:
        print("✅ Rendered with Satori/OG Edge Function")
        return response.content
    else:
        raise Exception(f"Satori Edge Function error: {response.status_code} - {response.text[:200]}")


def render_teacher_paystub_with_satori(first_name, last_name, output_path=None, school_id=None, school_name=None):
    """
    Render Teacher Pay Stub using Satori/OG Edge Function (og-teacher-paystub.js)
    
    Gọi /api/og-teacher-paystub Edge Function để tạo pay stub cho teacher verification
    
    Args:
        first_name: Teacher first name
        last_name: Teacher last name
        output_path: Path to save PNG file (optional)
        school_id: School ID from HIGH_SCHOOLS config (optional)
        school_name: School name to search (optional)
    
    Returns:
        bytes: PNG image data (if output_path is None)
        str: Path to saved file (if output_path is provided)
    """
    import requests
    
    # Use production URL to avoid deployment protection issues
    base_url = os.getenv("PRODUCTION_URL", "https://sheerid-verify-pro.vercel.app")
    
    # Build query params - pass school info to match verification request
    params = {
        "firstName": first_name,
        "lastName": last_name,
        "t": random.randint(1000, 9999)  # Cache buster
    }
    
    # Add school info if provided - use snake_case for og-teacher-paystub.js
    if school_id:
        params["school_id"] = school_id
    if school_name:
        params["school_name"] = school_name
    
    # Call Edge Function - using og-teacher-paystub for Pay Stub format
    url = f"{base_url}/api/og-teacher-paystub?{urlencode(params)}"
    print(f"🎓 Calling Teacher Pay Stub Edge Function: {url}")
    
    # Add bypass header if configured
    headers = {}
    bypass_token = os.getenv("VERCEL_AUTOMATION_BYPASS_SECRET")
    if bypass_token:
        headers["x-vercel-protection-bypass"] = bypass_token
    
    response = requests.get(url, headers=headers, timeout=60)
    
    if response.status_code == 200:
        print("✅ Teacher Pay Stub rendered with Satori/OG Edge Function")
        
        if output_path:
            # Save to file
            with open(output_path, 'wb') as f:
                f.write(response.content)
            print(f"✅ Teacher Pay Stub saved to {output_path}")
            return output_path
        else:
            return response.content
    else:
        raise Exception(f"Teacher Pay Stub Edge Function error: {response.status_code} - {response.text[:200]}")


def render_html_to_image_bytes(html_content, transcript_info):
    """
    Render HTML to image và trả về bytes (cho Vercel - không cần filesystem)
    
    Priority order:
    1. Satori/OG Edge Function - TỐI ƯU NHẤT, miễn phí, không giới hạn
    2. External APIs (HCTI, ApiFlash, ScreenshotOne) - Miễn phí có giới hạn
    3. Pillow fallback - Luôn hoạt động
    
    Returns:
        bytes: PNG image data
    """
    import io
    import requests
    
    # 1. Try Satori/OG Edge Function first (BEST for Vercel)
    try:
        return render_with_satori_edge(transcript_info)
    except Exception as e:
        print(f"⚠️ Satori Edge Function failed: {e}")
    
    # 2. Try HCTI.io API (50/month free)
    try:
        user_id = os.getenv("HCTI_USER_ID")
        api_key = os.getenv("HCTI_API_KEY")
        
        if user_id and api_key:
            response = requests.post(
                "https://hcti.io/v1/image",
                auth=(user_id, api_key),
                data={"html": html_content, "css": "", "google_fonts": "Arial"},
                timeout=30
            )
            if response.status_code == 200:
                image_url = response.json().get("url")
                if image_url:
                    img_response = requests.get(image_url, timeout=30)
                    if img_response.status_code == 200:
                        print("✅ Rendered with HCTI API")
                        # Optimize image to reduce size
                        return optimize_image(img_response.content, max_size_kb=500)
    except Exception as e:
        print(f"⚠️ HCTI failed: {e}")
    
    # 2. Try ApiFlash (100/month free)
    try:
        import base64
        access_key = os.getenv("APIFLASH_ACCESS_KEY")
        
        if access_key:
            html_base64 = base64.b64encode(html_content.encode('utf-8')).decode('utf-8')
            response = requests.get(
                "https://api.apiflash.com/v1/urltoimage",
                params={
                    "access_key": access_key,
                    "url": f"data:text/html;base64,{html_base64}",
                    "width": 800, "height": 1100, "format": "png"
                },
                timeout=30
            )
            if response.status_code == 200:
                print("✅ Rendered with ApiFlash")
                # Optimize image to reduce size
                return optimize_image(response.content, max_size_kb=500)
    except Exception as e:
        print(f"⚠️ ApiFlash failed: {e}")
    
    # 3. Try ScreenshotOne (100/month free)
    try:
        access_key = os.getenv("SCREENSHOTONE_ACCESS_KEY")
        
        if access_key:
            response = requests.get(
                "https://api.screenshotone.com/take",
                params={
                    "access_key": access_key,
                    "html": html_content,
                    "viewport_width": 800, "viewport_height": 1100, "format": "png"
                },
                timeout=30
            )
            if response.status_code == 200:
                print("✅ Rendered with ScreenshotOne")
                # Optimize image to reduce size
                return optimize_image(response.content, max_size_kb=500)
    except Exception as e:
        print(f"⚠️ ScreenshotOne failed: {e}")
    
    # 4. Fallback to Pillow (always works on Vercel)
    print("🔄 Using Pillow fallback")
    return render_transcript_with_pillow_bytes(transcript_info)


def render_transcript_with_pillow_bytes(transcript_info):
    """
    Render transcript bằng Pillow và trả về bytes (cho Vercel)
    Sử dụng dữ liệu random từ transcript_info
    """
    from PIL import Image, ImageDraw, ImageFont
    import io
    
    # Create image
    width, height = 800, 1100
    img = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(img)
    
    # Load fonts
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    
    def load_font(size, bold=False):
        for path in font_paths:
            if bold and 'Bold' in path:
                try:
                    return ImageFont.truetype(path, size)
                except:
                    pass
            elif not bold and 'Bold' not in path:
                try:
                    return ImageFont.truetype(path, size)
                except:
                    pass
        return ImageFont.load_default()
    
    title_font = load_font(22, bold=True)
    header_font = load_font(14, bold=True)
    label_font = load_font(11, bold=True)
    value_font = load_font(12, bold=False)
    small_font = load_font(10, bold=False)
    table_font = load_font(10, bold=False)
    gpa_font = load_font(18, bold=True)
    
    # Colors
    blue = (30, 58, 138)
    gray = (102, 102, 102)
    light_gray = (200, 200, 200)
    black = (51, 51, 51)
    red = (220, 38, 38)
    
    left_margin = 60
    right_margin = width - 60
    y = 35
    
    # University name (random)
    uni_name = transcript_info['university']['name']
    draw.text((width//2, y), uni_name, fill=blue, font=title_font, anchor="mm")
    y += 30
    
    # Address (from university config)
    uni_address = transcript_info['university'].get('address', '').replace(' | ', ' - ')
    draw.text((width//2, y), uni_address, fill=gray, font=small_font, anchor="mm")
    y += 20
    
    # Divider
    draw.line([(left_margin, y), (right_margin, y)], fill=blue, width=2)
    y += 30
    
    # Title
    draw.text((width//2, y), "OFFICIAL ACADEMIC TRANSCRIPT", fill=black, font=header_font, anchor="mm")
    y += 40
    
    # Student info
    col1_x = left_margin
    col2_x = 420
    
    # Row 1: Name / Student ID (random)
    draw.text((col1_x, y), "Student Name", fill=blue, font=label_font)
    draw.text((col2_x, y), "Student ID", fill=blue, font=label_font)
    y += 16
    draw.text((col1_x, y), f"{transcript_info['first_name']} {transcript_info['last_name']}", fill=black, font=value_font)
    draw.text((col2_x, y), transcript_info.get('student_id', 'AI202558968'), fill=black, font=value_font)
    y += 30
    
    # Row 2: Program / Expected Graduation (random)
    draw.text((col1_x, y), "Program", fill=blue, font=label_font)
    draw.text((col2_x, y), "Expected Graduation", fill=blue, font=label_font)
    y += 16
    program = transcript_info.get('program', 'Bachelor of Fine Arts')
    if len(program) > 35:
        program = program[:32] + "..."
    draw.text((col1_x, y), program, fill=black, font=value_font)
    draw.text((col2_x, y), transcript_info.get('expected_graduation', 'May 2026'), fill=black, font=value_font)
    y += 30
    
    # Row 3: DOB / SSN (random - năm sinh 2002-2005)
    draw.text((col1_x, y), "Date of Birth", fill=blue, font=label_font)
    draw.text((col2_x, y), "SSN/ID", fill=blue, font=label_font)
    y += 16
    draw.text((col1_x, y), transcript_info.get('dob', 'January 15, 2003'), fill=black, font=value_font)
    draw.text((col2_x, y), transcript_info.get('ssn', '***-**-5965'), fill=black, font=value_font)
    y += 35
    
    # Course table
    draw.line([(left_margin, y), (right_margin, y)], fill=light_gray, width=1)
    y += 8
    
    col_code = left_margin
    col_title = left_margin + 90
    col_credits = left_margin + 380
    col_grade = left_margin + 450
    col_term = left_margin + 520
    
    draw.text((col_code, y), "Course Code", fill=gray, font=small_font)
    draw.text((col_title, y), "Course Title", fill=gray, font=small_font)
    draw.text((col_credits, y), "Credits", fill=gray, font=small_font)
    draw.text((col_grade, y), "Grade", fill=gray, font=small_font)
    draw.text((col_term, y), "Term", fill=gray, font=small_font)
    y += 18
    draw.line([(left_margin, y), (right_margin, y)], fill=light_gray, width=1)
    y += 8
    
    courses = [
        {"code": "DES 101", "title": "Introduction to Design Thinking", "credits": 3, "grade": "A-", "term": "Fall 2022"},
        {"code": "ART 105", "title": "Visual Foundations I", "credits": 4, "grade": "A", "term": "Fall 2022"},
        {"code": "HIS 200", "title": "Modern Art History", "credits": 3, "grade": "B+", "term": "Fall 2022"},
        {"code": "DES 102", "title": "Design Methods & Processes", "credits": 3, "grade": "A", "term": "Winter 2023"},
        {"code": "COM 110", "title": "Digital Communication", "credits": 3, "grade": "A-", "term": "Winter 2023"},
        {"code": "ART 106", "title": "Visual Foundations II", "credits": 4, "grade": "A", "term": "Winter 2023"},
    ]
    
    for course in courses:
        title = course['title'][:29] + "..." if len(course['title']) > 32 else course['title']
        draw.text((col_code, y), course['code'], fill=black, font=table_font)
        draw.text((col_title, y), title, fill=black, font=table_font)
        draw.text((col_credits, y), str(course['credits']), fill=black, font=table_font)
        draw.text((col_grade, y), course['grade'], fill=black, font=table_font)
        draw.text((col_term, y), course['term'], fill=black, font=table_font)
        y += 22
        draw.line([(left_margin, y), (right_margin, y)], fill=(240, 240, 240), width=1)
        y += 5
    
    y += 20
    
    # GPA (random)
    gpa = transcript_info.get('gpa', 3.87)
    total_credits = transcript_info.get('total_credits', 39)
    draw.text((right_margin - 200, y), "Cumulative GPA", fill=blue, font=label_font)
    y += 18
    draw.text((right_margin - 200, y), f"{gpa:.2f}", fill=red, font=gpa_font)
    y += 30
    draw.text((right_margin - 200, y), f"Total Credits Earned: {total_credits}", fill=blue, font=label_font)
    
    # Footer
    y = height - 100
    draw.line([(left_margin, y), (right_margin, y)], fill=light_gray, width=1)
    y += 15
    
    # Issue date (trong vòng 90 ngày)
    issue_date = transcript_info.get('issue_date', datetime.now().strftime("%B %d, %Y"))
    draw.text((width//2, y), f"Official transcript issued on: {issue_date}", fill=gray, font=small_font, anchor="mm")
    y += 18
    draw.text((width//2 - 100, y), "Authorized Signature:", fill=gray, font=small_font)
    draw.line([(width//2, y + 5), (width//2 + 150, y + 5)], fill=gray, width=1)
    y += 20
    
    # Registrar title (from university)
    registrar_title = transcript_info['university'].get('registrar_title', f"Registrar, {uni_name}")
    draw.text((width//2, y), registrar_title, fill=gray, font=small_font, anchor="mm")
    
    # Return as optimized JPEG bytes (much smaller than PNG)
    # Convert to RGB if needed
    if img.mode == 'RGBA':
        background = Image.new('RGB', img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[3])
        img = background
    elif img.mode != 'RGB':
        img = img.convert('RGB')
    
    buffer = io.BytesIO()
    # JPEG quality 85 = good balance of size/quality (typically 3-5x smaller than PNG)
    img.save(buffer, format='JPEG', quality=85, optimize=True)
    buffer.seek(0)
    
    size_kb = len(buffer.getvalue()) / 1024
    print(f"✅ Transcript rendered: {size_kb:.1f}KB (JPEG optimized)")
    
    return buffer.getvalue()


def render_transcript_auto(html_content, transcript_info, output_path="transcript.png"):
    """
    Auto-render transcript - optimized for Vercel serverless
    
    Priority order:
    1. HCTI.io API (50/month free) - exact HTML rendering
    2. ApiFlash (100/month free) - exact HTML rendering  
    3. ScreenshotOne (100/month free) - exact HTML rendering
    4. Pillow fallback - Always works on Vercel
    
    For local development, also tries:
    - imgkit, Playwright, Selenium, WeasyPrint
    
    Args:
        html_content: HTML content
        transcript_info: Transcript info dict (used by Pillow fallback)
        output_path: Output file path
    
    Returns:
        str: Path to rendered image
    """
    import os
    is_vercel = os.getenv("VERCEL") == "1" or os.getenv("VERCEL_ENV") is not None
    
    # On Vercel - only use APIs and Pillow
    if is_vercel:
        # Get image bytes
        image_bytes = render_html_to_image_bytes(html_content, transcript_info)
        
        # Save to /tmp (only writable location on Vercel)
        if not output_path.startswith("/tmp"):
            output_path = f"/tmp/{os.path.basename(output_path)}"
        
        with open(output_path, "wb") as f:
            f.write(image_bytes)
        
        return output_path
    
    # Local development - try all methods
    errors = []
    
    # 1. Try HCTI.io API first (works everywhere)
    try:
        return render_html_with_hcti(html_content, output_path)
    except Exception as e:
        errors.append(f"HCTI: {e}")
        print(f"⚠️ HCTI unavailable ({e})")
    
    # 2. Try ApiFlash
    try:
        return render_html_with_apiflash(html_content, output_path)
    except Exception as e:
        errors.append(f"ApiFlash: {e}")
        print(f"⚠️ ApiFlash unavailable ({e})")
    
    # 3. Try ScreenshotOne
    try:
        return render_html_with_screenshotone(html_content, output_path)
    except Exception as e:
        errors.append(f"ScreenshotOne: {e}")
        print(f"⚠️ ScreenshotOne unavailable ({e})")
    
    # 4. Try imgkit (local only)
    try:
        return render_html_with_imgkit(html_content, output_path)
    except Exception as e:
        errors.append(f"imgkit: {e}")
        print(f"⚠️ imgkit unavailable ({e})")
    
    # 5. Try Playwright (local only)
    try:
        return render_html_to_image_sync(html_content, output_path)
    except (ImportError, Exception) as e:
        errors.append(f"Playwright: {e}")
        print(f"⚠️ Playwright unavailable ({e})")
    
    # 6. Try Selenium (local only)
    try:
        return render_html_with_selenium(html_content, output_path)
    except Exception as e:
        errors.append(f"Selenium: {e}")
        print(f"⚠️ Selenium unavailable ({e})")
    
    # 7. Fallback to Pillow (always works)
    print("🔄 Using Pillow fallback")
    return render_transcript_with_pillow(transcript_info, output_path)


async def upload_document(file_path, upload_url=None):
    """
    Upload document lên server
    
    Args:
        file_path: Đường dẫn file cần upload
        upload_url: URL để upload (nếu None sẽ dùng default)
    
    Returns:
        dict: Response từ server
    """
    import aiohttp
    
    if upload_url is None:
        # Default upload URL - cần config
        upload_url = os.getenv("DOCUPLOAD_URL", "https://your-upload-endpoint.com/upload")
    
    async with aiohttp.ClientSession() as session:
        with open(file_path, "rb") as f:
            data = aiohttp.FormData()
            data.add_field("file", f, filename=os.path.basename(file_path))
            
            async with session.post(upload_url, data=data) as response:
                return await response.json()


class TranscriptGenerator:
    """Class để quản lý việc tạo và upload transcript"""
    
    def __init__(self, output_dir="transcripts"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
    
    async def generate_and_save(self, **kwargs):
        """
        Tạo transcript và lưu thành file ảnh
        
        Returns:
            tuple: (file_path, student_info)
        """
        # Generate HTML
        html_content, student_info = generate_transcript_html(**kwargs)
        
        # Tạo filename unique
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"transcript_{student_info['student_id']}_{timestamp}.png"
        output_path = self.output_dir / filename
        
        # Render to image
        await render_html_to_image(html_content, str(output_path))
        
        return str(output_path), student_info
    
    async def generate_upload(self, upload_url=None, **kwargs):
        """
        Tạo transcript, render và upload
        
        Returns:
            dict: Kết quả upload và thông tin sinh viên
        """
        file_path, student_info = await self.generate_and_save(**kwargs)
        
        # Upload
        upload_result = await upload_document(file_path, upload_url)
        
        return {
            "file_path": file_path,
            "student_info": student_info,
            "upload_result": upload_result
        }


# Hàm tiện ích để sử dụng trong verification flow
async def create_random_transcript():
    """Tạo transcript ngẫu nhiên và trả về đường dẫn file"""
    generator = TranscriptGenerator()
    file_path, info = await generator.generate_and_save()
    print(f"Created transcript for {info['first_name']} {info['last_name']}")
    print(f"University: {info['university']['name']}")
    print(f"Student ID: {info['student_id']}")
    print(f"File saved: {file_path}")
    return file_path, info


def create_random_transcript_sync():
    """Sync version của create_random_transcript"""
    return asyncio.run(create_random_transcript())


# Test
if __name__ == "__main__":
    # Test generate HTML
    html, info = generate_transcript_html()
    print("Generated transcript for:")
    print(f"  Name: {info['first_name']} {info['last_name']}")
    print(f"  University: {info['university']['name']}")
    print(f"  Student ID: {info['student_id']}")
    print(f"  GPA: {info['gpa']}")
    
    # Save HTML for preview
    with open("test_transcript.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("\nSaved test_transcript.html for preview")
    
    # Uncomment to test image rendering (requires playwright)
    # file_path, info = create_random_transcript_sync()
    # print(f"\nImage saved to: {file_path}")
