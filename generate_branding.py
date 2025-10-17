"""
BookMyMovie Platform - Brand Identity Generator
Creates logo assets and branding materials for deployment
"""

import os
from PIL import Image, ImageDraw, ImageFont
import json
from datetime import datetime

class BookMyMovieBrandGenerator:
    """Generate brand assets for BookMyMovie platform"""
    
    def __init__(self):
        self.app_name = "BookMyMovie"
        self.tagline = "Your Cinema Experience, Perfected"
        
        # Brand Colors
        self.colors = {
            "primary": "#667eea",
            "primary_dark": "#764ba2", 
            "secondary": "#ff6b6b",
            "accent": "#ee5a24",
            "text": "#2c3e50",
            "text_light": "#7f8c8d",
            "background": "#f8f9fa",
            "white": "#ffffff"
        }
        
        # Create assets directory
        self.assets_dir = "assets/branding"
        os.makedirs(self.assets_dir, exist_ok=True)
    
    def hex_to_rgb(self, hex_color):
        """Convert hex color to RGB tuple"""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    def create_app_icon(self, size=512):
        """Create app icon with gradient background"""
        
        # Create image with gradient background
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Create gradient background
        primary_rgb = self.hex_to_rgb(self.colors["primary"])
        primary_dark_rgb = self.hex_to_rgb(self.colors["primary_dark"])
        
        # Simple gradient simulation
        for y in range(size):
            ratio = y / size
            r = int(primary_rgb[0] * (1 - ratio) + primary_dark_rgb[0] * ratio)
            g = int(primary_rgb[1] * (1 - ratio) + primary_dark_rgb[1] * ratio)
            b = int(primary_rgb[2] * (1 - ratio) + primary_dark_rgb[2] * ratio)
            
            draw.rectangle([0, y, size, y+1], fill=(r, g, b, 255))
        
        # Add rounded corners
        mask = Image.new('L', (size, size), 0)
        mask_draw = ImageDraw.Draw(mask)
        corner_radius = size // 8
        mask_draw.rounded_rectangle([0, 0, size, size], corner_radius, fill=255)
        
        # Apply mask for rounded corners
        img.putalpha(mask)
        
        # Add cinema icon (simplified)
        icon_size = size // 3
        icon_x = (size - icon_size) // 2
        icon_y = (size - icon_size) // 2
        
        # Draw cinema screen
        screen_width = icon_size * 0.8
        screen_height = icon_size * 0.6
        screen_x = icon_x + (icon_size - screen_width) // 2
        screen_y = icon_y + (icon_size - screen_height) // 2
        
        draw.rounded_rectangle(
            [screen_x, screen_y, screen_x + screen_width, screen_y + screen_height],
            radius=10,
            fill=(255, 255, 255, 220)
        )
        
        # Draw play button
        play_size = icon_size // 4
        play_x = screen_x + (screen_width - play_size) // 2
        play_y = screen_y + (screen_height - play_size) // 2
        
        # Triangle for play button
        play_points = [
            (play_x, play_y),
            (play_x, play_y + play_size),
            (play_x + play_size, play_y + play_size // 2)
        ]
        draw.polygon(play_points, fill=primary_rgb)
        
        return img
    
    def create_logo_variants(self):
        """Create different logo size variants"""
        
        print("🎨 Generating BookMyMovie Brand Assets...")
        
        # App icon sizes for different platforms
        icon_sizes = {
            "app_icon_1024": 1024,  # iOS App Store
            "app_icon_512": 512,    # Android Play Store
            "app_icon_192": 192,    # PWA
            "app_icon_180": 180,    # iOS
            "app_icon_152": 152,    # iPad
            "app_icon_144": 144,    # Android
            "app_icon_120": 120,    # iPhone
            "app_icon_96": 96,      # Android
            "app_icon_76": 76,      # iPad
            "app_icon_72": 72,      # Android
            "favicon_64": 64,       # Large favicon
            "favicon_32": 32,       # Standard favicon
            "favicon_16": 16,       # Small favicon
        }
        
        # Generate all icon sizes
        generated_files = []
        
        for name, size in icon_sizes.items():
            icon = self.create_app_icon(size)
            filename = f"{self.assets_dir}/{name}.png"
            icon.save(filename, "PNG")
            generated_files.append(filename)
            print(f"  ✅ Created {name}.png ({size}x{size})")
        
        return generated_files
    
    def create_social_media_assets(self):
        """Create social media branding assets"""
        
        social_specs = {
            "facebook_cover": (1200, 630),
            "twitter_header": (1500, 500),
            "instagram_post": (1080, 1080),
            "linkedin_banner": (1584, 396),
            "youtube_thumbnail": (1280, 720)
        }
        
        generated_files = []
        
        for name, (width, height) in social_specs.items():
            # Create social media asset
            img = Image.new('RGB', (width, height), self.hex_to_rgb(self.colors["primary"]))
            draw = ImageDraw.Draw(img)
            
            # Add gradient background
            primary_rgb = self.hex_to_rgb(self.colors["primary"])
            primary_dark_rgb = self.hex_to_rgb(self.colors["primary_dark"])
            
            for y in range(height):
                ratio = y / height
                r = int(primary_rgb[0] * (1 - ratio) + primary_dark_rgb[0] * ratio)
                g = int(primary_rgb[1] * (1 - ratio) + primary_dark_rgb[1] * ratio)
                b = int(primary_rgb[2] * (1 - ratio) + primary_dark_rgb[2] * ratio)
                
                draw.rectangle([0, y, width, y+1], fill=(r, g, b))
            
            # Add logo and text
            try:
                # Calculate text size based on image dimensions
                title_size = min(width, height) // 15
                tagline_size = title_size // 2
                
                # Add app name
                text_y = height // 2 - title_size
                draw.text(
                    (width // 2, text_y), 
                    self.app_name,
                    fill=(255, 255, 255),
                    anchor="mm"
                )
                
                # Add tagline
                tagline_y = height // 2 + title_size // 2
                draw.text(
                    (width // 2, tagline_y),
                    self.tagline,
                    fill=(255, 255, 255, 200),
                    anchor="mm"
                )
                
            except Exception as e:
                print(f"  ⚠️ Text rendering issue for {name}: {e}")
            
            filename = f"{self.assets_dir}/{name}.png"
            img.save(filename, "PNG")
            generated_files.append(filename)
            print(f"  ✅ Created {name}.png ({width}x{height})")
        
        return generated_files
    
    def generate_brand_guidelines(self):
        """Generate brand guidelines document"""
        
        guidelines = {
            "brand_identity": {
                "app_name": self.app_name,
                "tagline": self.tagline,
                "description": "BookMyMovie is an enterprise-grade movie booking platform that transforms the cinema experience with AI-powered recommendations, real-time features, and seamless booking."
            },
            
            "logo": {
                "primary_icon": "🎬",
                "icon_description": "Cinema/movie camera emoji representing entertainment and film industry",
                "minimum_size": "32px height",
                "clear_space": "1x logo height on all sides",
                "formats": ["PNG", "SVG", "ICO"]
            },
            
            "color_palette": self.colors,
            
            "typography": {
                "primary_font": "Segoe UI, Arial, Helvetica, sans-serif",
                "secondary_font": "Georgia, Times New Roman, serif",
                "font_weights": {
                    "light": 300,
                    "normal": 400,
                    "medium": 500,
                    "bold": 700,
                    "heavy": 800
                }
            },
            
            "usage_guidelines": {
                "do": [
                    "Use the logo on solid backgrounds",
                    "Maintain proper clear space",
                    "Use approved color combinations",
                    "Scale proportionally",
                    "Ensure good contrast"
                ],
                "dont": [
                    "Stretch or distort the logo",
                    "Change brand colors",
                    "Add effects or shadows", 
                    "Use on busy backgrounds",
                    "Rotate or flip the logo"
                ]
            },
            
            "applications": {
                "mobile_app": "iOS and Android app icons",
                "web_platform": "Favicons and website branding",
                "social_media": "Profile pictures and cover images",
                "marketing": "Advertisements and promotional materials",
                "business_cards": "Corporate identity materials"
            },
            
            "generated_on": datetime.now().isoformat()
        }
        
        # Save brand guidelines as JSON
        guidelines_file = f"{self.assets_dir}/brand_guidelines.json"
        with open(guidelines_file, 'w') as f:
            json.dump(guidelines, f, indent=2)
        
        return guidelines_file
    
    def create_deployment_assets(self):
        """Create assets needed for deployment"""
        
        # Create manifest.json for PWA
        manifest = {
            "name": self.app_name,
            "short_name": "BookMyMovie",
            "description": self.tagline,
            "start_url": "/",
            "display": "standalone",
            "theme_color": self.colors["primary"],
            "background_color": self.colors["background"],
            "orientation": "portrait",
            "icons": [
                {
                    "src": "assets/branding/app_icon_192.png",
                    "sizes": "192x192",
                    "type": "image/png"
                },
                {
                    "src": "assets/branding/app_icon_512.png", 
                    "sizes": "512x512",
                    "type": "image/png"
                }
            ]
        }
        
        manifest_file = f"{self.assets_dir}/manifest.json"
        with open(manifest_file, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        return manifest_file
    
    def generate_complete_brand_package(self):
        """Generate complete branding package"""
        
        print(f"\n🎬 BookMyMovie Brand Package Generator")
        print("=" * 45)
        
        # Generate all assets
        icon_files = self.create_logo_variants()
        social_files = self.create_social_media_assets()
        guidelines_file = self.generate_brand_guidelines()
        manifest_file = self.create_deployment_assets()
        
        # Summary
        total_files = len(icon_files) + len(social_files) + 2
        
        print(f"\n📊 Brand Package Summary:")
        print(f"App Icons Generated: {len(icon_files)}")
        print(f"Social Media Assets: {len(social_files)}")
        print(f"Total Files Created: {total_files}")
        print(f"Assets Directory: {self.assets_dir}")
        
        print(f"\n🎯 Key Brand Elements:")
        print(f"App Name: {self.app_name}")
        print(f"Tagline: {self.tagline}")
        print(f"Primary Color: {self.colors['primary']}")
        print(f"Icon: {self.colors.get('icon', '🎬')}")
        
        print(f"\n📱 Ready for Deployment:")
        print("✅ iOS App Store (1024x1024 icon)")
        print("✅ Google Play Store (512x512 icon)")
        print("✅ Website Favicons (16px, 32px, 64px)")
        print("✅ PWA Manifest (192px, 512px)")
        print("✅ Social Media Assets")
        print("✅ Brand Guidelines Document")
        
        print(f"\n🚀 Next Steps:")
        print("1. Review generated assets in assets/branding/")
        print("2. Update mobile app with new icons")
        print("3. Deploy favicon to website")
        print("4. Use social media assets for marketing")
        print("5. Proceed with demo deployment")
        
        return {
            "total_files": total_files,
            "assets_directory": self.assets_dir,
            "app_name": self.app_name,
            "tagline": self.tagline,
            "ready_for_deployment": True
        }

# Generate brand package
if __name__ == "__main__":
    generator = BookMyMovieBrandGenerator()
    result = generator.generate_complete_brand_package()
    
    print(f"\n🎉 BookMyMovie branding package complete!")
    print(f"All assets ready for demo deployment! 🚀")