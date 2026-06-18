import os
import re
import tempfile
import zipfile
from pathlib import Path
from PIL import Image

# Library ReportLab untuk penyusunan PDF profesional
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, 
    TableStyle, PageBreak, KeepTogether, Image as RLImage
)

# KONFIGURASI UTAMA: Sesuaikan dengan folder tempat file ZIP Anda berada
SOURCE_DIR = r"G:\My Drive\Ceklis"

class WhatsAppReportGenerator:
    def __init__(self, zip_path: Path):
        self.zip_path = zip_path
        self.output_pdf_path = zip_path.parent / f"Report {zip_path.stem}.pdf"
        self.temp_dir = None
        self.checklist_items = []
        
        # Ambil identitas unit/nama proyek dari nama file ZIP untuk Cover Page
        self.unit_name = zip_path.stem.replace("Ceklis ", "").strip()

    def process(self):
        """Metode utama alur pemrosesan berkas arsip."""
        print(f"\n[PROSES] Memproses berkas: {self.zip_path.name}")
        try:
            with tempfile.TemporaryDirectory() as temp_dir_path:
                self.temp_dir = Path(temp_dir_path)
                
                # 1. Ekstraksi Berkas ZIP
                self._extract_zip()
                
                # 2. Cari dan Parsing File Teks Chat WhatsApp
                txt_file = self._find_txt_file()
                self._parse_chat_file(txt_file)
                
                if not self.checklist_items:
                    print(f"--> Peringatan: Tidak ditemukan data foto checklist yang valid di {self.zip_path.name}")
                    return
                
                # 3. Urutkan Data Berdasarkan Lokasi kemudian Pekerjaan (Ascending A-Z)
                self._sort_checklist_items()
                
                # 4. Generate Berkas Laporan PDF Profesional
                self._generate_pdf()
                print(f"[SUKSES] PDF Berhasil dibuat -> {self.output_pdf_path.name}")
                
        except Exception as e:
            print(f"ERROR: {self.zip_path.name}")
            print(f"Penyebab: {str(e)}")

    def _extract_zip(self):
        """Mengekstrak seluruh isi file ZIP ke dalam direktori temporer."""
        try:
            with zipfile.ZipFile(self.zip_path, 'r') as zip_ref:
                zip_ref.extractall(self.temp_dir)
        except zipfile.BadZipFile:
            raise Exception("File ZIP rusak atau tidak valid.")

    def _find_txt_file(self) -> Path:
        """Mencari berkas log teks (.txt) hasil ekspor WhatsApp."""
        txt_files = list(self.temp_dir.glob("*.txt"))
        if not txt_files:
            raise Exception("Berkas text log (.txt) hasil export chat WhatsApp tidak ditemukan di dalam ZIP.")
        return txt_files[0]

    def _parse_chat_file(self, txt_file: Path):
        """Memilah data teks baris demi baris menggunakan Regular Expression."""
        with open(txt_file, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()

        # BARU & DIPERBAIKI: Menangkap format IMG-*.jpg maupun format penomoran urut 00000*-PHOTO-*.jpg
        img_pattern = re.compile(r"([\w-]+\.jpg)")

        for i, line in enumerate(lines):
            match = img_pattern.search(line)
            if match:
                img_name = match.group(1)
                caption = "Lainnya : Tanpa Deskripsi"
                
                # Cari baris setelahnya yang bertindak sebagai deskripsi/caption
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    # Validasi jika baris berikutnya bukan penanda log waktu chat baru
                    if next_line and not re.search(r"\d{2}/\d{2}/\d{2}|\d{1,2}:\d{2}", next_line):
                        caption = next_line
                
                # Pemecahan string berdasarkan separator kustom ":"
                if ":" in caption:
                    parts = caption.split(":", 1)
                    location = parts[0].strip()
                    work = parts[1].strip()
                else:
                    location = "Lainnya"
                    work = caption.strip()
                
                # Pastikan file gambar riil terekstrak dengan benar
                img_path = self.temp_dir / img_name
                if img_path.exists():
                    self.checklist_items.append({
                        'image_name': img_name,
                        'image_path': img_path,
                        'location': location if location else "Lainnya",
                        'work': work if work else "Tanpa Deskripsi"
                    })

    def _sort_checklist_items(self):
        """Mengurutkan item data secara ascending berdasar Lokasi lalu Pekerjaan."""
        self.checklist_items.sort(key=lambda x: (x['location'].lower(), x['work'].lower()))

    def _generate_pdf(self):
        """Mengonstruksi lembar kerja PDF menggunakan layouting ReportLab Platypus Flowables."""
        # Setup Dokumen A4 Portrait dengan Margin Keliling 1 cm (28.35 points)
        margin = 28.35
        doc = SimpleDocTemplate(
            str(self.output_pdf_path),
            pagesize=A4,
            leftMargin=margin, rightMargin=margin,
            topMargin=margin, bottomMargin=margin
        )
        
        styles = getSampleStyleSheet()
        
        # Inisialisasi Gaya Tipografi Kustom (Sesuai Spesifikasi Font 12 pt)
        cover_title_style = ParagraphStyle('CoverTitle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=28, leading=34, alignment=1, spaceAfter=20, textColor=colors.HexColor('#1A365D'))
        cover_sub_style = ParagraphStyle('CoverSub', parent=styles['Normal'], fontName='Helvetica', fontSize=14, leading=18, alignment=1, textColor=colors.HexColor('#4A5568'))
        h2_style = ParagraphStyle('SectionHeader', parent=styles['Heading2'], fontName='Helvetica-Bold', fontSize=16, leading=20, spaceBefore=10, spaceAfter=15, textColor=colors.HexColor('#2B6CB0'))
        
        # Mengunci ukuran font tabel dan caption utama di 12 pt sesuai spesifikasi
        cell_text = ParagraphStyle('CellText', parent=styles['Normal'], fontName='Helvetica', fontSize=12, leading=16)
        cell_header = ParagraphStyle('CellHeader', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=12, leading=16, textColor=colors.white)
        
        photo_label_loc = ParagraphStyle('PhotoLabelLoc', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=12, leading=16, textColor=colors.HexColor('#2B6CB0'), alignment=1)
        photo_label_work = ParagraphStyle('PhotoLabelWork', parent=styles['Normal'], fontName='Helvetica', fontSize=12, leading=16, alignment=1)
        photo_label_file = ParagraphStyle('PhotoLabelFile', parent=styles['Normal'], fontName='Courier', fontSize=10, leading=12, textColor=colors.HexColor('#718096'), alignment=1)

        story = []

        # ==========================================
        # HALAMAN 1: COVER PAGE
        # ==========================================
        story.append(Spacer(1, 180))
        story.append(Paragraph("LAPORAN CEKLIS", cover_title_style))
        story.append(Spacer(1, 10))
        story.append(Paragraph(f"Unit : {self.unit_name}", cover_sub_style))
        story.append(PageBreak())

        # ==========================================
        # HALAMAN 2: CHECKLIST TABLE
        # ==========================================
        story.append(Paragraph("LIST PEKERJAAN", h2_style))
        story.append(Spacer(1, 5))
        
        # Lebar bersih area cetak penuh kertas A4 Portrait dikurangi margin: ~539.5 points
        table_data = [[
            Paragraph("No", cell_header),
            Paragraph("✓", cell_header),
            Paragraph("Lokasi", cell_header),
            Paragraph("Pekerjaan", cell_header)
        ]]
        
        for idx, item in enumerate(self.checklist_items, 1):
            table_data.append([
                Paragraph(str(idx), cell_text),
                Paragraph("☐", cell_text),
                Paragraph(item['location'], cell_text),
                Paragraph(item['work'], cell_text)
            ])
            
        col_widths = [35, 30, 144.5, 330]
        checklist_table = Table(table_data, colWidths=col_widths, repeatRows=1)
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

        # ==========================================
        # HALAMAN 3+: DOKUMENTASI FOTO
        # ==========================================
        story.append(Paragraph("DOKUMENTASI ITEM PEKERJAAN", h2_style))
        story.append(Spacer(1, 10))
        
        for item in self.checklist_items:
            try:
                with Image.open(item['image_path']) as img:
                    orig_w, orig_h = img.size
                aspect_ratio = orig_h / orig_w
            except:
                aspect_ratio = 1.0  # Fallback rasio aman jika berkas terkunci

            # Atur skala dinamis otomatis berdasarkan orientasi agar kertas maksimal terisi
            # Landscape (rasio <= 1): Muat 3 item/halaman | Portrait (rasio > 1): Muat 2 item/halaman
            if aspect_ratio <= 1.0:
                img_display_w = 260
                img_display_h = img_display_w * aspect_ratio
            else:
                img_display_w = 190
                img_display_h = img_display_w * aspect_ratio

            rl_img = RLImage(str(item['image_path']), width=img_display_w, height=img_display_h)
            rl_img.hAlign = 'CENTER'

            # Penataan caption diposisikan rata tengah (center) tepat di bawah foto
            caption_block = [
                Spacer(1, 4),
                Paragraph(item['location'], photo_label_loc),
                Paragraph(item['work'], photo_label_work),
                Paragraph(item['image_name'], photo_label_file),
                Spacer(1, 15)
            ]

            # Satukan objek Foto dan Caption ke dalam struktur KeepTogether agar tidak terpisah halaman
            photo_item_table = Table([[rl_img], [caption_block]], colWidths=[539.5])
            photo_item_table.setStyle(TableStyle([
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('BOTTOMPADDING', (0,0), (-1,-1), 0),
                ('TOPPADDING', (0,0), (-1,-1), 0),
            ]))
            
            story.append(KeepTogether(photo_item_table))

        # Eksekusi perakitan akhir berkas PDF
        doc.build(story)


def main():
    """Antarmuka pengguna berbasis teks (CLI)."""
    print("=========================================")
    print(" WHATSAPP CHECKLIST REPORT GENERATOR")
    print("=========================================\n")
    
    src_path = Path(SOURCE_DIR)
    if not src_path.exists():
        print(f"ERROR: Folder sumber direktori tidak ditemukan: {SOURCE_DIR}")
        print("Silakan sesuaikan variabel 'SOURCE_DIR' di baris kode paling atas.")
        input("\nTekan Enter untuk keluar..."); return

    # Scan seluruh file berformat .zip di dalam direktori
    zip_files = sorted(list(src_path.glob("*.zip")), key=lambda x: x.name.lower())
    
    if not zip_files:
        print(f"Informasi: Tidak ada berkas (.zip) ditemukan di dalam folder {SOURCE_DIR}")
        input("\nTekan Enter untuk keluar..."); return

    print("DAFTAR FILE ZIP\n")
    print("[0] Semua File")
    for idx, zip_file in enumerate(zip_files, 1):
        print(f"[{idx}] {zip_file.name}")
        
    print("\n-----------------------------------------")
    try:
        user_choice = input("Pilih nomor file yang ingin diproses: ").strip()
        choice_idx = int(user_choice)
    except ValueError:
        print("Pilihan tidak valid. Harus berupa angka numerik.")
        input("\nTekan Enter untuk keluar..."); return

    if choice_idx == 0:
        print(f"\n[INFO] Memproses total keseluruhan {len(zip_files)} file ZIP...")
        for zip_file in zip_files:
            generator = WhatsAppReportGenerator(zip_file)
            generator.process()
    elif 1 <= choice_idx <= len(zip_files):
        selected_zip = zip_files[choice_idx - 1]
        generator = WhatsAppReportGenerator(selected_zip)
        generator.process()
    else:
        print("Nomor pilihan di luar jangkauan daftar.")
        
    print("\n=== Selesai ===")
    input("Tekan Enter untuk menutup program...")

if __name__ == "__main__":
    main()