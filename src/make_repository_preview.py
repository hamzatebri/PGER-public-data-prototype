from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "figures" / "repository_preview.png"

WIDTH, HEIGHT = 1280, 640
NAVY = "#0B172A"
INK = "#17243A"
BLUE = "#2F7BD8"
TEAL = "#169A7A"
ORANGE = "#ED6A2C"
GOLD = "#F4C451"
PAPER = "#F7F4ED"
WHITE = "#FFFFFF"
MUTED = "#617087"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "segoeuib.ttf" if bold else "segoeui.ttf"
    return ImageFont.truetype(str(Path("C:/Windows/Fonts") / name), size)


def rounded_card(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], fill: str) -> None:
    draw.rounded_rectangle(box, radius=18, fill=fill)


def main() -> None:
    image = Image.new("RGB", (WIDTH, HEIGHT), PAPER)
    draw = ImageDraw.Draw(image)

    draw.rectangle((0, 0, WIDTH, 18), fill=GOLD)
    draw.text((72, 58), "PGER", font=font(76, True), fill=NAVY)
    draw.text(
        (72, 150),
        "Procurement Geopolitical Event Review",
        font=font(35, True),
        fill=INK,
    )
    draw.text(
        (72, 202),
        "A reproducible public-data prototype for transparent procurement review",
        font=font(23),
        fill=MUTED,
    )

    cards = [
        ((72, 276, 392, 398), BLUE, "24,765", "source-linked notices"),
        ((416, 276, 736, 398), TEAL, "4", "official event records"),
        ((760, 276, 1080, 398), ORANGE, "51", "source-check candidates"),
    ]
    for box, colour, value, label in cards:
        rounded_card(draw, box, WHITE)
        draw.rectangle((box[0], box[1], box[0] + 10, box[3]), fill=colour)
        draw.text((box[0] + 34, box[1] + 18), value, font=font(38, True), fill=colour)
        draw.text((box[0] + 34, box[1] + 72), label, font=font(19), fill=INK)

    draw.text((72, 452), "STRUCTURAL ROUTE", font=font(15, True), fill=BLUE)
    draw.text((72, 480), "Observed indicators", font=font(22, True), fill=INK)
    draw.text((282, 480), "→", font=font(28, True), fill=BLUE)
    draw.text((330, 480), "review order", font=font(22, True), fill=INK)

    draw.text((690, 452), "EVENT-CONTEXT ROUTE", font=font(15, True), fill=TEAL)
    draw.text((690, 480), "Official records", font=font(22, True), fill=INK)
    draw.text((858, 480), "→", font=font(28, True), fill=TEAL)
    draw.text((906, 480), "source check", font=font(22, True), fill=INK)

    draw.line((72, 555, 1208, 555), fill="#D8D4CB", width=2)
    draw.text(
        (72, 575),
        "Business Intelligence & Data Analytics  |  Python • Jupyter • Streamlit",
        font=font(18),
        fill=MUTED,
    )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    image.save(OUTPUT, format="PNG", optimize=True)
    print(f"Wrote {OUTPUT} ({WIDTH} x {HEIGHT})")


if __name__ == "__main__":
    main()
