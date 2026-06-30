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
    """Memilah teks chat dari berkas txt dan menghindari duplikasi gambar."""
    checklist_items = []
    seen_images = set() # Menghindari duplikasi gambar ganda
    
    with open(txt_file, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()

    img_pattern = re.compile(r"([\w-]+\.(?:jpg|jpeg))", re.IGNORECASE)

    for i, line in enumerate(lines):
        match = img_pattern.search(line)
        if match:
            img_name = match.group(1)
            
            # Jika gambar sudah pernah diproses, lewati agar tidak dobel
            if img_name.lower() in seen_images:
                continue
                
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
            
            img_path = Path(temp_dir_path) / img_name
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
                seen_images.add(img_name.lower())
                
    return checklist_items

def generate_pdf(output_pdf_path, checklist_items, unit_name):
    """Membuat dokumen PDF Laporan dengan susunan grid 4 foto per halaman."""
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
    
    photo_label_loc = ParagraphStyle('PhotoLabelLoc', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=10, leading=13, textColor=colors.HexColor('#2B6CB0'), alignment=1)
    photo_label_work = ParagraphStyle('PhotoLabelWork', parent=styles['Normal'], fontName='Helvetica', fontSize=10, leading=13, alignment=1)

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
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(checklist_table)
    story.append(PageBreak())

    # DOKUMENTASI FOTO - LAYOUT GRID 2X2 (4 FOTO PER HALAMAN)
    story.append(Paragraph("DOKUMENTASI FOTO LAPANGAN", h2_style))
    story.append(Spacer(1, 10))
    
    # Kelompokkan item foto menjadi paket berisi maksimal 4 item per halaman
    for i in range(0, len(checklist_items), 4):
        page_items = checklist_items[i:i+4]
        grid_cells = []
        
        for item in page_items:
            try:
                with Image.open(item['image_path']) as img:
                    orig_w, orig_h = img.size
                aspect_ratio = orig_h / orig_w
            except:
                aspect_ratio = 1.0

            # Dimensi maksimal sel foto agar pas 4 kotak di kertas A4
            img_display_w = 240
            img_display_h = img_display_w * aspect_ratio
            if img_display_h > 240: # Batasi tinggi agar tidak meluber ke halaman baru
                img_display_h = 240
                img_display_w = img_display_h / aspect_ratio

            rl_img = RLImage(str(item['image_path']), width=img_display_w, height=img_display_h)
            rl_img.hAlign = 'CENTER'

            caption_block = [
                rl_img,
                Spacer(1, 4),
                Paragraph(f"<b>{item['location']}</b>", photo_label_loc),
                Paragraph(item['work'], photo_label_work),
                Spacer(1, 15)
            ]
            grid_cells.append(caption_block)
            
        # Isih kotak kosong jika jumlah foto di halaman terakhir kurang dari 4
        while len(grid_cells) < 4:
            grid_cells.append("")
            
        # Susun matriks tabel grid 2 baris x 2 kolom
        grid_data = [
            [grid_cells[0], grid_cells[1]],
            [grid_cells[2], grid_cells[3]]
        ]
        
        grid_table = Table(grid_data, colWidths=[265, 265])
        grid_table.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('LEFTPADDING', (0,0), (-1,-1), 5),
            ('RIGHTPADDING', (0,0), (-1,-1), 5),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ]))
        
        story.append(KeepTogether(grid_table))
        
        # Tambahkan page break antar halaman foto, kecuali untuk kelompok terakhir
        if i + 4 < len(checklist_items):
            story.append(PageBreak())

    doc.build(story)

# --- TAMPILAN ANTARMUKA WEB ---
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
                        st.warning("Peringatan: Tidak ditemukan format foto checklist atau deskripsi pekerjaan.")
                    else:
                        # Urutkan A-Z lokasi
                        checklist_items.sort(key=lambda x: (x['location'].lower(), x['work'].lower()))
                        
                        output_pdf = temp_dir_path / f"Report_{unit_name}.pdf"
                        generate_pdf(output_pdf, checklist_items, unit_name)
                        
                        with open(output_pdf, "rb") as f:
                            pdf_bytes = f.read()
                            
                        st.success("🎉 Laporan berhasil dikonstruksi!")
                        st.download_button(
                            label="📥 Unduh Laporan PDF Hasil (4 Foto/Halaman)",
                            data=pdf_bytes,
                            file_name=f"Report_{unit_name}.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
