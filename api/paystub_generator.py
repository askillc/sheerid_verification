# -*- coding: utf-8 -*-
"""
Pasadena ISD Pay Stub Generator for Teacher Verification
Generates pay stub images using Pillow (no external dependencies)
"""

import os
import random
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont

# Base directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# US Names for random generation
FIRST_NAMES = [
    "James", "John", "Robert", "Michael", "William", "David", "Richard", "Joseph", "Thomas", "Christopher",
    "Charles", "Daniel", "Matthew", "Anthony", "Mark", "Donald", "Steven", "Paul", "Andrew", "Joshua",
    "Mary", "Patricia", "Jennifer", "Linda", "Barbara", "Elizabeth", "Susan", "Jessica", "Sarah", "Karen",
    "Nancy", "Lisa", "Betty", "Margaret", "Sandra", "Ashley", "Kimberly", "Emily", "Donna", "Michelle"
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez",
    "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin",
    "Lee", "Perez", "Thompson", "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson"
]

def generate_paystub_data(first_name=None, last_name=None):
    """Generate random pay stub data for Pasadena ISD"""
    if not first_name:
        first_name = random.choice(FIRST_NAMES)
    if not last_name:
        last_name = random.choice(LAST_NAMES)
    
    full_name = f"{first_name} {last_name}"
    
    # Generate dates - MUST be in the PAST (not future)
    today = datetime.now()
    days_ago = random.randint(7, 60)
    check_date = today - timedelta(days=days_ago)
    period_end = check_date - timedelta(days=5)
    
    return {
        'full_name': full_name,
        'first_name': first_name,
        'last_name': last_name,
        'check_date': check_date.strftime('%m/%d/%y'),
        'period_end_date': period_end.strftime('%m/%d/%Y'),
        'check_number': str(random.randint(210000, 220000)),
        'employee_no': str(random.randint(100000, 999999)).zfill(7),
        'mailing_id': str(random.randint(100000000, 999999999)).zfill(10),
        'earnings': [
            {'name': 'SEC PHY EDUC TCHR', 'rate': '337.31', 'current': '2,628.21', 'cytd': '21,025.68'},
            {'name': 'CAREER LADDER 3', 'rate': '16.04', 'current': '125.00', 'cytd': '1,000.04'},
            {'name': 'TENNIS COACH BOYS', 'rate': '12.24', 'current': '95.34', 'cytd': '762.72'},
            {'name': 'TENNIS COACH GIRLS', 'rate': '12.24', 'current': '95.34', 'cytd': '762.72'},
            {'name': 'COACH HS 5 DAYS', 'rate': '337.31', 'current': '70.27', 'cytd': '562.20'},
            {'name': 'TEAM TENNIS COACH', 'rate': '6.68', 'current': '52.08', 'cytd': '416.68'},
            {'name': 'DEPT HEAD MINOR', 'rate': '2.27', 'current': '17.71', 'cytd': '141.68'},
            {'name': 'COLLEGE PAY', 'rate': '1.68', 'current': '13.05', 'cytd': '104.43'},
        ],
        'deductions': [
            {'name': 'JEFF NTL CANCER', 'amount': '16.47', 'cytd': '65.88'},
            {'name': 'TEACHER RETIRE', 'amount': '204.86', 'cytd': '1,617.93'},
            {'name': 'TRS INSURANCE', 'amount': '20.81', 'cytd': '164.33'},
            {'name': 'ANNUITY 403,457', 'amount': '100.00', 'cytd': '800.00'},
            {'name': 'FEDERAL TAX', 'amount': '545.92', 'cytd': '4,167.10'},
            {'name': 'GCEFCU DEDUCT', 'amount': '230.00', 'cytd': '1,840.00'},
            {'name': 'UHC PLAN I', 'amount': '', 'cytd': '560.00'},
        ],
        'totals': {
            'gross_pay': '$3,201.00',
            'taxable': '$2,879.67',
            'deducts': '$1,118.06',
            'net_pay': '$2,082.94',
            'ytd_gross': '$25,280.15',
            'ytd_taxable': '$22,236.34',
            'ytd_deducts': '$9,215.24',
            'ytd_net': '$16,064.91'
        },
        'bank': {
            'name': 'Gulf Coast Ed',
            'type': 'CHECK',
            'account': 'XXXXXX9',
            'amount': '$2,082.94'
        }
    }

def generate_paystub_image(first_name=None, last_name=None, output_path=None):
    """Generate Pasadena ISD pay stub image using Pillow"""
    
    data = generate_paystub_data(first_name, last_name)
    
    # Image dimensions - Large size for better readability
    # 1190 x 1684 pixels (A4 at 144 DPI)
    width = 1190
    height = 1000
    
    # Create image
    img = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(img)
    
    # Use default font
    font_title = ImageFont.load_default()
    font_small = font_title
    
    # Colors
    gray_bg = (192, 192, 192)
    black = (0, 0, 0)
    
    y = 20
    
    # Title
    title = "PASADENA INDEPENDENT SCHOOL DISTRICT"
    title_bbox = draw.textbbox((0, 0), title, font=font_title)
    title_width = title_bbox[2] - title_bbox[0]
    draw.text(((width - title_width) // 2, y), title, fill=black, font=font_title)
    y += 30
    
    # Main box
    box_x = 30
    box_y = y
    box_width = width - 60
    box_height = 680
    
    # Draw main border
    draw.rectangle([box_x, box_y, box_x + box_width, box_y + box_height], outline=black, width=2)
    
    # Header row 1 (gray background)
    header_height = 28
    draw.rectangle([box_x, box_y, box_x + box_width, box_y + header_height], fill=gray_bg, outline=black)
    draw.text((box_x + 10, box_y + 6), f"Check Date: {data['check_date']}", fill=black, font=font_title)
    draw.text((box_x + 300, box_y + 6), f"Period End: {data['period_end_date']}", fill=black, font=font_title)
    draw.text((box_x + 680, box_y + 6), f"Check: {data['check_number']}", fill=black, font=font_title)
    
    # Header row 2 (gray background)
    y2 = box_y + header_height
    draw.rectangle([box_x, y2, box_x + box_width, y2 + header_height], fill=gray_bg, outline=black)
    draw.text((box_x + 10, y2 + 6), f"Name: {data['full_name']}", fill=black, font=font_title)
    draw.text((box_x + 300, y2 + 6), "Marital Status: S   Exemptions: 0", fill=black, font=font_title)
    draw.text((box_x + 680, y2 + 6), f"Employee No: {data['employee_no']}", fill=black, font=font_title)
    
    # Content area
    content_y = y2 + header_height + 4
    left_width = int(box_width * 0.55)
    
    # Draw vertical divider
    draw.line([box_x + left_width, content_y, box_x + left_width, box_y + box_height], fill=black, width=2)
    
    # LEFT COLUMN - Earnings
    ex = box_x + 8
    ey = content_y + 4
    
    # Earnings header
    draw.text((ex, ey), "EARNINGS", fill=black, font=font_small)
    draw.text((ex + 200, ey), "RATE", fill=black, font=font_small)
    draw.text((ex + 320, ey), "CURRENT", fill=black, font=font_small)
    draw.text((ex + 460, ey), "CYTD", fill=black, font=font_small)
    ey += 20
    draw.line([ex, ey, box_x + left_width - 8, ey], fill=black)
    ey += 4
    
    # Earnings rows
    for e in data['earnings']:
        draw.text((ex, ey), e['name'], fill=black, font=font_small)
        draw.text((ex + 200, ey), e['rate'], fill=black, font=font_small)
        draw.text((ex + 320, ey), e['current'], fill=black, font=font_small)
        draw.text((ex + 460, ey), e['cytd'], fill=black, font=font_small)
        ey += 18
    
    # Current Transactions Above
    ey += 6
    draw.text((ex, ey), "CURRENT TRANSACTIONS ABOVE", fill=black, font=font_small)
    ey += 20
    
    # Additional transactions
    for i in range(3):
        draw.text((ex, ey), "ATHLETIC BUS DRIVER", fill=black, font=font_small)
        rate = ['162.00', '103.00', '81.00'][i]
        cytd = ['162.00', '103.00', '81.00'][i]
        draw.text((ex + 200, ey), rate, fill=black, font=font_small)
        draw.text((ex + 460, ey), cytd, fill=black, font=font_small)
        ey += 18

    # Totals table
    totals_y = box_y + box_height - 150
    draw.line([ex, totals_y, box_x + left_width - 10, totals_y], fill=black, width=2)
    
    # Totals header
    ty = totals_y + 4
    cols = ['', 'GROSS', 'TAXABLE', 'DEDUCTS', 'NET PAY']
    col_x = [ex, ex + 100, ex + 220, ex + 340, ex + 460]
    for i, col in enumerate(cols):
        draw.text((col_x[i], ty), col, fill=black, font=font_small)
    ty += 20
    
    # Current row
    vals = ['CURRENT', data['totals']['gross_pay'], data['totals']['taxable'], data['totals']['deducts'], data['totals']['net_pay']]
    for i, val in enumerate(vals):
        draw.text((col_x[i], ty), val, fill=black, font=font_small)
    ty += 20
    
    # YTD row
    vals = ['YEAR TO DATE', data['totals']['ytd_gross'], data['totals']['ytd_taxable'], data['totals']['ytd_deducts'], data['totals']['ytd_net']]
    for i, val in enumerate(vals):
        draw.text((col_x[i], ty), val, fill=black, font=font_small)
    ty += 24
    
    # Bank info
    draw.line([ex, ty, box_x + left_width - 10, ty], fill=black)
    ty += 4
    draw.text((ex, ty), "DIRECT DEPOSIT BANK", fill=black, font=font_small)
    draw.text((ex + 200, ty), "ACCT TYPE", fill=black, font=font_small)
    draw.text((ex + 320, ty), "ACCT NUMBER", fill=black, font=font_small)
    draw.text((ex + 460, ty), "AMOUNT", fill=black, font=font_small)
    ty += 18
    draw.text((ex, ty), data['bank']['name'], fill=black, font=font_small)
    draw.text((ex + 200, ty), data['bank']['type'], fill=black, font=font_small)
    draw.text((ex + 320, ty), data['bank']['account'], fill=black, font=font_small)
    draw.text((ex + 460, ty), data['bank']['amount'], fill=black, font=font_small)
    
    # RIGHT COLUMN - Deductions
    rx = box_x + left_width + 10
    ry = content_y + 4
    
    # Deductions header
    draw.text((rx, ry), "DEDUCTION / CONTRIBUTION", fill=black, font=font_small)
    draw.text((rx + 250, ry), "AMOUNT", fill=black, font=font_small)
    draw.text((rx + 370, ry), "CYTD", fill=black, font=font_small)
    ry += 20
    draw.line([rx, ry, box_x + box_width - 10, ry], fill=black)
    ry += 4
    
    # Deduction rows
    for d in data['deductions']:
        draw.text((rx, ry), d['name'], fill=black, font=font_small)
        draw.text((rx + 250, ry), d['amount'], fill=black, font=font_small)
        draw.text((rx + 370, ry), d['cytd'], fill=black, font=font_small)
        ry += 18
    
    # District contributions
    ry += 8
    draw.text((rx + 20, ry), "DISTRICT CONTRIBUTIONS PAID BELOW THIS LINE", fill=black, font=font_small)
    ry += 20
    
    district_contribs = [
        {'name': 'TRS CARE - DISTRICT CONTRIB', 'amount': '17.61', 'cytd': '139.03'},
        {'name': 'UHC PLAN I - DISTRICT PAID', 'amount': '', 'cytd': '900.00'},
        {'name': 'LIFE EMPLR PAID', 'amount': '', 'cytd': '5.20'},
    ]
    for d in district_contribs:
        draw.text((rx, ry), d['name'], fill=black, font=font_small)
        draw.text((rx + 250, ry), d['amount'], fill=black, font=font_small)
        draw.text((rx + 370, ry), d['cytd'], fill=black, font=font_small)
        ry += 18
    
    # Leave table
    leave_y = box_y + box_height - 120
    leave_x = rx + 10
    draw.rectangle([leave_x, leave_y, box_x + box_width - 15, leave_y + 110], outline=black)
    
    # Leave header
    ly = leave_y + 4
    draw.text((leave_x + 8, ly), "PLAN", fill=black, font=font_small)
    draw.text((leave_x + 140, ly), "PYB", fill=black, font=font_small)
    draw.text((leave_x + 210, ly), "ALLOC", fill=black, font=font_small)
    draw.text((leave_x + 290, ly), "USAGE", fill=black, font=font_small)
    draw.text((leave_x + 370, ly), "BAL", fill=black, font=font_small)
    ly += 18
    draw.line([leave_x, ly, box_x + box_width - 15, ly], fill=black)
    ly += 4
    
    leave_info = [
        {'plan': 'Local Leave', 'pyb': '927', 'alloc': '56', 'usage': '0', 'bal': '983'},
        {'plan': 'State Leave Bank', 'pyb': '152', 'alloc': '0', 'usage': '0', 'bal': '152'},
        {'plan': 'State Personal Leave', 'pyb': '175.5', 'alloc': '40', 'usage': '-8', 'bal': '207.5'},
        {'plan': 'Vacation Grandfathered', 'pyb': '120', 'alloc': '26.67', 'usage': '0', 'bal': '146.67'},
        {'plan': 'Vacation Leave Bank', 'pyb': '66', 'alloc': '0', 'usage': '0', 'bal': '66'},
    ]
    for l in leave_info:
        draw.text((leave_x + 8, ly), l['plan'], fill=black, font=font_small)
        draw.text((leave_x + 140, ly), l['pyb'], fill=black, font=font_small)
        draw.text((leave_x + 210, ly), l['alloc'], fill=black, font=font_small)
        draw.text((leave_x + 290, ly), l['usage'], fill=black, font=font_small)
        draw.text((leave_x + 370, ly), l['bal'], fill=black, font=font_small)
        ly += 16
    
    # Footer - NO LOGO
    footer_y = box_y + box_height + 30
    
    # Footer text only
    draw.text((box_x, footer_y), "PASADENA INDEPENDENT SCHOOL DISTRICT", fill=black, font=font_title)
    draw.text((box_x, footer_y + 16), "PAYROLL DEPARTMENT", fill=black, font=font_small)
    draw.text((box_x, footer_y + 32), "1515 Cherrybrook Lane", fill=black, font=font_small)
    draw.text((box_x, footer_y + 48), "Pasadena, TX 77502", fill=black, font=font_small)
    
    # Mailing info
    mail_y = footer_y + 80
    draw.text((box_x, mail_y), data['mailing_id'], fill=black, font=font_small)
    draw.text((box_x, mail_y + 18), data['full_name'], fill=black, font=font_small)
    draw.text((box_x, mail_y + 36), "1515 Cherrybrook", fill=black, font=font_small)
    draw.text((box_x, mail_y + 54), "Pasadena, TX 77502", fill=black, font=font_small)
    
    # Save image
    if output_path:
        img.save(output_path, 'PNG', optimize=True)
        print(f"✅ Pay stub saved to {output_path}")
        return output_path
    else:
        return img

# Test
if __name__ == "__main__":
    generate_paystub_image("Christopher", "Miller", "test_paystub_pillow.png")
    print("Done!")
