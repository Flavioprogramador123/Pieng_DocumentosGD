"""
Gera todos os ícones necessários para Windows, Web e Favicon
a partir do logoescuro.png
"""
from PIL import Image
import os

# Caminho do logo original
LOGO_PATH = "logoescuro.png"
OUTPUT_DIR = "."

# Tamanhos necessários
SIZES = {
    # Favicon (navegador)
    'favicon-16.png': 16,
    'favicon-32.png': 32,
    'favicon-48.png': 48,

    # Apple Touch Icon
    'apple-touch-icon.png': 180,

    # Android/Chrome
    'android-chrome-192.png': 192,
    'android-chrome-512.png': 512,

    # Windows/Desktop
    'icon-48.png': 48,
    'icon-64.png': 64,
    'icon-128.png': 128,
    'icon-256.png': 256,

    # Atalho Windows
    'pieng-icon.ico': [16, 32, 48, 64, 128, 256],  # ICO com múltiplos tamanhos
}

def create_icon(input_path, output_path, size):
    """Cria ícone redimensionado mantendo proporções"""
    img = Image.open(input_path)

    # Redimensiona mantendo proporção
    img.thumbnail((size, size), Image.Resampling.LANCZOS)

    # Cria imagem quadrada com fundo transparente
    new_img = Image.new('RGBA', (size, size), (0, 0, 0, 0))

    # Centraliza a imagem
    offset = ((size - img.size[0]) // 2, (size - img.size[1]) // 2)
    new_img.paste(img, offset, img if img.mode == 'RGBA' else None)

    return new_img

def main():
    if not os.path.exists(LOGO_PATH):
        print(f"❌ Logo não encontrado: {LOGO_PATH}")
        return

    print("Gerando icones...")
    print()

    for output_name, size_or_sizes in SIZES.items():
        output_path = os.path.join(OUTPUT_DIR, output_name)

        if isinstance(size_or_sizes, list):
            # Criar ICO com multiplos tamanhos
            images = []
            for size in size_or_sizes:
                img = create_icon(LOGO_PATH, None, size)
                images.append(img)

            images[0].save(
                output_path,
                format='ICO',
                sizes=[(s, s) for s in size_or_sizes],
                append_images=images[1:]
            )
            print(f"[OK] {output_name} (tamanhos: {size_or_sizes})")
        else:
            # Criar PNG unico
            img = create_icon(LOGO_PATH, output_path, size_or_sizes)
            img.save(output_path, 'PNG', optimize=True)
            print(f"[OK] {output_name} ({size_or_sizes}x{size_or_sizes})")

    print()
    print("Todos os icones foram gerados com sucesso!")
    print()
    print("Arquivos criados:")
    print("   - Favicons: favicon-*.png")
    print("   - Apple: apple-touch-icon.png")
    print("   - Android: android-chrome-*.png")
    print("   - Windows: icon-*.png, pieng-icon.ico")

if __name__ == "__main__":
    main()
