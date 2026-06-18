import streamlit as st
import os
import re
import tempfile
import zipfile
from pathlib import Path
from PIL import Image

# Library ReportLab untuk cetak PDF
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, 
    TableStyle, PageBreak, KeepTogether, Image as RLImage
)

st.set_page_config(page_title="WhatsApp Checklist Report Generator", page_icon="📝", layout="centered")

def parse_chat_file(txt_file, temp_dir_path):
    """Memilah teks chat dari berkas txt."""
    checklist_items = []
    with open(txt_file, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()

    # REVISI MUTAKHIR: Regex diperkuat agar mendukung .jpg, .JPG, .jpeg, .JPEG secara case-insensitive
    img_pattern = re.compile(r"([\w-]+\.(?:jpg|jpeg))", re.IGNORECASE)

    for i, line in enumerate(lines):
        match = img_pattern.search(line)
        if match:
            img_name = match.group(1)
            caption = "Lainnya : Tanpa Deskripsi"
            
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if next_line and not re.search(r"\d{2}/\d{2}/\d{2}|\d{1,2}:\d{2}", next_line):
                    caption = next_line
            
            if ":" in caption:
                parts = caption.split(":", 1)
                location = parts[0].strip()
                work = parts[1].strip()
            else:
                location = "Lainnya"
                work = caption.strip()
            
            # Cari file gambar asli secara case-insensitive di dalam folder ekstraksi
            img_path = Path(temp_dir_path) / img_name
            
            # Cari cadangan jika nama file di text dan file fisik berbeda huruf besar/kecilnya
            if not img_path.exists():
                for file_in_temp in Path(temp_dir_path).iterdir():
                    if file_in_temp.name.lower() == img_name.lower():
                        img_path = file_in_temp
                        img_name = file_in_temp.name
                        break

            if img_path.exists():
                checklist_items.append({
                    'image_name': img_name,
                    'image_path': img_path,
                    'location': location if location else "Lainnya",
                    'work': work if work else "Tanpa Deskripsi"
                })
    return checklist_items

def generate_pdf(output_pdf_path, checklist_items, unit_name):
    """Membuat dokumen PDF Laporan."""
    margin = 28.35
    doc = SimpleDocTemplate(
        str(output_pdf_path),
        pagesize=A4,
        leftMargin=margin, rightMargin=margin,
        topMargin=margin, bottomMargin=margin
    )
    
    styles = getSampleStyleSheet()
    
    cover_title_style = ParagraphStyle('CoverTitle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=28, leading=34, alignment=1, spaceAfter=20, textColor=colors.HexColor('#1A365D'))
    cover_sub_style = ParagraphStyle('CoverSub', parent=styles['Normal'], fontName='Helvetica', fontSize=14, leading=18, alignment=1, textColor=colors.HexColor('#4A5568'))
    h2_style = ParagraphStyle('SectionHeader', parent=styles['Heading2'], fontName='Helvetica-Bold', fontSize=16, leading=20, spaceBefore=10, spaceAfter=15, textColor=colors.HexColor('#2B6CB0'))
    
    cell_text = ParagraphStyle('CellText', parent=styles['Normal'], fontName='Helvetica', fontSize=12, leading=16)
    cell_header = ParagraphStyle('CellHeader', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=12, leading=16, textColor=colors.white)
    
    photo_label_loc = ParagraphStyle('PhotoLabelLoc', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=12, leading=16, textColor=colors.HexColor('#2B6CB0'), alignment=1)
    photo_label_work = ParagraphStyle('PhotoLabelWork', parent=styles['Normal'], fontName='Helvetica', fontSize=12, leading=16, alignment=1)
    photo_label_file = ParagraphStyle('PhotoLabelFile', parent=styles['Normal'], fontName='Courier', fontSize=10, leading=12, textColor=colors.HexColor('#718096'), alignment=1)

    story = []

    # COVER PAGE
    story.append(Spacer(1, 150))
    story.append(Paragraph("LAPORAN CEKLIS INSPEKSI", cover_title_style))
    story.append(Spacer(1, 10))
    story.append(Paragraph(f"Unit / Proyek : {unit_name}", cover_sub_style))
    story.append(PageBreak())

    # TABEL CHECKLIST
    story.append(Paragraph("LIST ITEM PEKERJAAN", h2_style))
    story.append(Spacer(1, 5))
    
    table_data = [[
        Paragraph("No", cell_header),
        Paragraph("✓", cell_header),
        Paragraph("Lokasi", cell_header),
        Paragraph("Pekerjaan", cell_header)
    ]]
    
    for idx, item in enumerate(checklist_items, 1):
        table_data.append([
            Paragraph(str(idx), cell_text),
            Paragraph("☐", cell_text),
            Paragraph(item['location'], cell_text),
            Paragraph(item['work'], cell_text)
        ])
        
    checklist_table = Table(table_data, colWidths=[35, 30, 144.5, 330], repeatRows=1)
    checklist_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#2B6CB0')),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E0')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F7FAFC')]),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(checklist_table)
    story.append(PageBreak())

    # DOKUMENTASI FOTO
    story.append(Paragraph("DOKUMENTASI FOTO LAPANGAN", h2_style))
    story.append(Spacer(1, 10))
    
    for item in checklist_items:
        try:
            with Image.open(item['image_path']) as img:
                orig_w, orig_h = img.size
            aspect_ratio = orig_h / orig_w
        except:
            aspect_ratio = 1.0

        if aspect_ratio <= 1.0:
            img_display_w = 260
            img_display_h = img_display_w * aspect_ratio
        else:
            img_display_w = 190
            img_display_h = img_display_w * aspect_ratio

        rl_img = RLImage(str(item['image_path']), width=img_display_w, height=img_display_h)
        rl_img.hAlign = 'CENTER'

        caption_block = [
            Spacer(1, 4),
            Paragraph(item['location'], photo_label_loc),
            Paragraph(item['work'], photo_label_work),
            Paragraph(item['image_name'], photo_label_file),
            Spacer(1, 15)
        ]

        photo_item_table = Table([[rl_img], [caption_block]], colWidths=[539.5])
        photo_item_table.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 0),
            ('TOPPADDING', (0,0), (-1,-1), 0),
        ]))
        story.append(KeepTogether(photo_item_table))

    doc.build(story)

# --- TAMPILAN ANTARMUKA WEB (UI) ---
st.title("📝 WhatsApp Checklist Report Generator")
st.write("Ekstrak chat export WhatsApp (.zip) menjadi laporan PDF resmi secara instan.")

uploaded_file = st.file_uploader("Pilih Berkas ZIP Ceklis dari HP / PC", type=["zip"])

if uploaded_file is not None:
    unit_name = uploaded_file.name.replace("Ceklis ", "").replace(".zip", "").strip()
    st.info(f"Mendeteksi Unit/Proyek: **{unit_name}**")
    
    if st.button("Generate Laporan PDF", type="primary"):
        with st.spinner("Sedang memproses gambar dan menyusun PDF..."):
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_dir_path = Path(temp_dir)
                
                with zipfile.ZipFile(uploaded_file, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir_path)
                
                txt_files = list(temp_dir_path.glob("*.txt"))
                if not txt_files:
                    st.error("Gagal: Tidak ditemukan file teks chat (.txt) di dalam ZIP WhatsApp Anda.")
                else:
                    checklist_items = parse_chat_file(txt_files[0], temp_dir_path)
                    
                    if not checklist_items:
                        st.warning("Peringatan: Tidak ditemukan format foto checklist atau deskripsi pekerjaan yang valid di dalam berkas ini. Periksa format penulisan teks chat Anda.")
                    else:
                        # Urutkan A-Z lokasi
                        checklist_items.sort(key=lambda x: (x['location'].lower(), x['work'].lower()))
                        
                        output_pdf = temp_dir_path / f"Report_{uploaded_file.stem}.pdf"
                        generate_pdf(output_pdf, checklist_items, unit_name)
                        
                        with open(output_pdf, "rb") as f:
                            pdf_bytes = f.read()
                            
                        st.success("🎉 Laporan berhasil dikonstruksi!")
                        st.download_button(
                            label="📥 Unduh Laporan PDF Hasil",
                            data=pdf_bytes,
                            file_name=f"Report_{uploaded_file.stem}.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )