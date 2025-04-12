import re
from datetime import datetime

def format_market_summary(market_summary, stock_summaries=None):
    """
    Builds the full newsletter in HTML with clean layout, heading styles, and structured summary.
    """
    current_date = datetime.now().strftime("%A, %B %d, %Y")

    html_parts = [
        "<html>",
        "<body style='margin: 0; padding: 0; font-family: Arial, sans-serif;'>",
        "<table width='100%' cellpadding='0' cellspacing='0' style='background-color: #f8f8f8; padding: 30px 0;'>",
        "<tr><td align='center'>",
        "<table width='600' cellpadding='20' cellspacing='0' style='background: #ffffff; border-radius: 8px; border: 1px solid #ccc; text-align: left;'>",
        f"<tr><td>",
        f"<h1 style='font-size: 26px; color: #009933; margin: 0 0 10px;'>Daily Market Update</h1>",
        f"<p style='color: #888; font-size: 14px; margin-bottom: 20px;'>{current_date}</p>",
        f"<div style='font-size: 16px; color: #333; line-height: 1.6;'>{convert_markdown_to_html(market_summary)}</div>",
        "<hr style='margin: 30px 0;'>"
    ]

    if stock_summaries:
        html_parts.append("<h2 style='font-size: 20px; margin-bottom: 10px;'>Stocks You're Following</h2>")
        for stock in stock_summaries:
            stock_symbol, stock_details = stock.split(":", 1)
            html_parts.append(f"""
                <div style='margin-bottom: 22px; padding-bottom: 6px; border-bottom: 1px solid #eee;'>
                    <div style='font-size: 15px; color: #333;'>
                        <p style='font-size: 20px; font-weight: bold; margin: 0 0 2px; color: #111;'>{stock_symbol.strip()}</p>
                        {convert_markdown_to_html(stock_details.strip())}
                    </div>
                </div>
            """)
    else:
        html_parts.append("<p style='color: #777;'>(No updates for your tracked stocks today.)</p>")

    html_parts.append("<hr style='margin: 30px 0;'>")
    html_parts.append("""
        <p style='font-size: 12px; color: #777;'>
            <strong>Contact Us:</strong><br>
            Email: <a href='mailto:newsletter@mrktpulseai.com' style='color: #009933;'>newsletter@mrktpulseai.com</a><br>
            Website: <a href='https://mrktpulseai.com' target='_blank' style='color: #009933;'>mrktpulseai.com</a>
        </p>
        <p style='font-size: 12px; color: #777;'>
            <strong>Disclaimer:</strong> This newsletter is for informational purposes only and does not constitute financial advice.
        </p>
    """)

    html_parts.extend(["</td></tr>", "</table>", "</td></tr>", "</table>", "</body>", "</html>"])

    return "\n".join(html_parts)


def convert_markdown_to_html(text):
    """
    Enhanced Markdown to HTML conversion for use in the newsletter.
    - Handles headings, lists, bold, paragraphs
    - Prevents wrapping <h1> in <p>
    """

    def format_heading(match):
        heading_text = match.group(1).strip()

        return (
            f"<h2 style=\""
            f"font-size: 17px;"
            f"font-weight: 600;"
            f"color: #1a1a1a;"
            f"border-bottom: 2px solid #e0e0e0;"
            f"padding-bottom: 6px;"
            f"margin: 35px 0 15px;"
            f"letter-spacing: 0.5px;"
            f"text-transform: none;"
            f"\">{heading_text}</h2>"
        )

    # ✅ Headings
    text = re.sub(r'^### (.*?)$', format_heading, text, flags=re.MULTILINE)
    
    # ✅ Bold
    text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)

    # ✅ Lists
    list_items = re.findall(r'(?m)^\* (.+)$', text)
    if list_items:
        list_html = ''.join(f'<li>{item}</li>' for item in list_items)
        text = re.sub(r'(?m)^\* .+$', '', text)
        text += f"<ul style='margin: 10px 0 20px 20px; padding-left: 10px;'>{list_html}</ul>"

    # ✅ Split into paragraphs safely (but don't wrap <h1>, <ul>, etc)
    lines = [line.strip() for line in text.strip().split('\n') if line.strip()]
    html_parts = []
    for line in lines:
        if line.startswith("<h1") or line.startswith("<ul") or line.startswith("<li") or line.startswith("</ul"):
            html_parts.append(line)
        else:
            html_parts.append(f"<p style='line-height: 1.6; font-size: 16px; color: #333;'>{line}</p>")

    return "\n".join(html_parts)