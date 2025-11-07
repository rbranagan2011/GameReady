"""
Management command to generate PNG icons from SVG for web app manifest.

This creates the required PNG icon sizes (192x192 and 512x512) from the SVG icon.
Requires cairosvg or pillow + svglib to convert SVG to PNG.
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from pathlib import Path
import os

try:
    from cairosvg import svg2png
    HAS_CAIROSVG = True
except ImportError:
    try:
        from svglib.svglib import svg2rlg
        from reportlab.graphics import renderPM
        HAS_SVGLIB = True
        HAS_CAIROSVG = False
    except ImportError:
        HAS_CAIROSVG = False
        HAS_SVGLIB = False

try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


class Command(BaseCommand):
    help = 'Generate PNG icons from SVG for web app manifest'

    def handle(self, *args, **options):
        static_dir = Path(settings.STATICFILES_DIRS[0]) if settings.STATICFILES_DIRS else Path(settings.BASE_DIR) / 'static'
        images_dir = static_dir / 'images'
        svg_path = images_dir / 'icon-gr.svg'
        
        if not svg_path.exists():
            self.stdout.write(self.style.ERROR(f'SVG icon not found at {svg_path}'))
            return
        
        # Create PNG icons using PIL if SVG conversion not available
        if not HAS_CAIROSVG and not HAS_SVGLIB:
            if HAS_PIL:
                self.stdout.write(self.style.WARNING('SVG conversion libraries not found. Creating PNG icons directly with PIL...'))
                self.create_png_with_pil(images_dir)
            else:
                self.stdout.write(self.style.ERROR(
                    'Neither cairosvg, svglib, nor PIL available. '
                    'Please install one: pip install cairosvg OR pip install svglib reportlab pillow'
                ))
                return
        else:
            # Convert SVG to PNG
            if HAS_CAIROSVG:
                self.convert_with_cairosvg(svg_path, images_dir)
            else:
                self.convert_with_svglib(svg_path, images_dir)
        
        self.stdout.write(self.style.SUCCESS('Successfully generated icon files!'))

    def create_png_with_pil(self, images_dir):
        """Create PNG icons directly using PIL (fallback method)."""
        sizes = [192, 512]
        
        for size in sizes:
            # Create image with blue background
            img = Image.new('RGB', (size, size), color='#0d6efd')
            draw = ImageDraw.Draw(img)
            
            # Try to use a nice font, fallback to default
            try:
                # Try to use a system font
                font_size = int(size * 0.55)  # ~55% of icon size
                font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
            except:
                try:
                    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", int(size * 0.55))
                except:
                    # Fallback to default font
                    font = ImageFont.load_default()
            
            # Draw "GR" text centered
            text = "GR"
            # Get text bounding box
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            # Center the text
            x = (size - text_width) / 2
            y = (size - text_height) / 2 - bbox[1]
            
            draw.text((x, y), text, fill='white', font=font)
            
            # Save the image
            output_path = images_dir / f'icon-{size}.png'
            img.save(output_path, 'PNG')
            self.stdout.write(f'Created {output_path}')

    def convert_with_cairosvg(self, svg_path, images_dir):
        """Convert SVG to PNG using cairosvg."""
        sizes = [192, 512]
        
        for size in sizes:
            output_path = images_dir / f'icon-{size}.png'
            svg2png(url=str(svg_path), write_to=str(output_path), output_width=size, output_height=size)
            self.stdout.write(f'Created {output_path}')

    def convert_with_svglib(self, svg_path, images_dir):
        """Convert SVG to PNG using svglib."""
        sizes = [192, 512]
        drawing = svg2rlg(str(svg_path))
        
        for size in sizes:
            output_path = images_dir / f'icon-{size}.png'
            # Scale drawing to target size
            scale = size / max(drawing.width, drawing.height)
            drawing.width = size
            drawing.height = size
            drawing.scale(scale, scale)
            renderPM.drawToFile(drawing, str(output_path), fmt='PNG')
            self.stdout.write(f'Created {output_path}')

