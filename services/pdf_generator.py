
import os
from pathlib import Path
from datetime import datetime
from typing import List
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from core.models import Product

# Path for saving PDFs
ENGINE_ROOT = Path(__file__).parent.parent
PDF_DIR = ENGINE_ROOT / "data" / "generated_pdfs"
PDF_DIR.mkdir(parents=True, exist_ok=True)

class PDFGenerator:
    """
    Generates PDF product sheets for Adquify.
    """
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.setup_styles()

    def setup_styles(self):
        self.title_style = ParagraphStyle(
            'AdquifyTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.darkblue,
            spaceAfter=20
        )
        self.product_name_style = ParagraphStyle(
            'ProdName',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=colors.black,
            spaceAfter=6
        )
        self.price_style = ParagraphStyle(
            'Price',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=colors.green,
            fontName='Helvetica-Bold'
        )


import logging
logger = logging.getLogger(__name__)

    def generate_catalog_pdf(self, products: List[Product], query_context: str) -> str:
        """
        Generates a PDF for the list of products and returns the relative URL path.
        """
        # CRITICAL FIX: Safe Guard against None input
        if not query_context or not isinstance(query_context, str):
            logger.error("PDF Generation skipped: Input text is None or invalid.")
            return None

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"Adquify_Selection_{timestamp}.pdf"
        filepath = PDF_DIR / filename
        
        doc = SimpleDocTemplate(str(filepath), pagesize=A4)
        story = []
        
        # Header
        story.append(Paragraph(f"Selección Adquify: '{query_context}'", self.title_style))
        story.append(Spacer(1, 12))
        
        # Products
        for p in products:
            # Container for product info
            # Image | Info
            
            # Fetch Image
            img_path = None
            if p.images and p.images[0].local_path:
                if os.path.exists(p.images[0].local_path):
                    img_path = p.images[0].local_path
            
            # If no local image, we skip image or use placeholder logic (ReportLab needs local file or valid http)
            # For this MVP, let's just list text if image is complex
            
            p_name = Paragraph(p.name, self.product_name_style)
            p_desc = Paragraph(p.description[:200] + "..." if p.description else "", self.styles['Normal'])
            p_price = Paragraph(f"Precio: €{p.selling_price:.2f}" if p.selling_price else "Consultar", self.price_style)
            
            # Layout
            data = [[p_name], [p_desc], [p_price], [Spacer(1, 12)]]
            table = Table(data, colWidths=[400])
            table.setStyle(TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('LEFTPADDING', (0,0), (-1,-1), 0),
            ]))
            
            story.append(table)
            story.append(Spacer(1, 20))
            story.append(Paragraph("_" * 50, self.styles['Normal']))
            story.append(Spacer(1, 20))
            
        doc.build(story)
        
        # Return URL relative to mounted /files
        # Mounted at: /files -> data/
        return f"/files/generated_pdfs/{filename}"
