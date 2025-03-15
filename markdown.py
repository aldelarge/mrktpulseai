import re

def markdown_to_html(md_text):
    # Convert Markdown to HTML
    
    # Convert headings (e.g., ### Heading -> <h3>Heading</h3>)
    md_text = re.sub(r'### (.*?)\n', r'<h3>\1</h3>\n', md_text)
    md_text = re.sub(r'## (.*?)\n', r'<h2>\1</h2>\n', md_text)
    md_text = re.sub(r'# (.*?)\n', r'<h1>\1</h1>\n', md_text)

    # Convert newlines into <p> (for paragraphs) and <br> (for line breaks)
    md_text = md_text.strip()

    # Replace newlines that should create new paragraphs
    md_text = re.sub(r'(\n\s*\n)', r'</p><p>', md_text)  # Multiple newlines -> separate paragraphs
    md_text = f"<p>{md_text}</p>"  # Wrap the entire content in <p> tags to ensure it's a paragraph

    # Convert bold text (e.g., **bold** -> <strong>bold</strong>)
    md_text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', md_text)

    # Convert lists (e.g., - item -> <ul><li>item</li></ul>)
    md_text = re.sub(r'^\* (.*?)\n', r'<ul><li>\1</li></ul>', md_text, flags=re.M)
    md_text = re.sub(r'\n\* (.*?)\n', r'<ul><li>\1</li></ul>', md_text, flags=re.M)

    # Convert single newlines to <br> for line breaks within paragraphs
    md_text = re.sub(r'(\n)', r'<br>', md_text)  # Replace all remaining newlines with <br>

    disclaimer_html = """
    <p><small><strong>Disclaimer:</strong> The information provided in this newsletter is for informational purposes only and does not constitute financial, investment, or trading advice. Please consult with a qualified financial advisor before making any investment decisions.</small></p>
    """

    # Add inline styles to control margins and padding, and ensure fixed width
    md_text = f"""
    <html>
        <body style="margin: 0; padding: 0; font-family: Arial, sans-serif;">
            <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                <tr>
                    <td align="center">
                        <table role="presentation" width="600" cellspacing="0" cellpadding="20" style="border: 1px solid #ccc; background-color: #fff; margin: 0 auto;">
                            <tr>
                                <td style="font-size: 16px; line-height: 1.5; color: #222;">
                                    {md_text}
                                     <br>                               <!-- Signature Section -->
                                    <p style="text-align: left; font-size: 12px; color: #777; margin-top: 30px;">
                                        <strong>Contact Us:</strong><br>
                                        Email: <a href="mailto:newsletter@mrktpulseai.com" style="color: #00ff00;">newsletter@mrktpulseai.com</a><br>
                                        Website: <a href="https://mrktpulseai.com" target="_blank" style="color: #00ff00;">mrktpulseai.com</a>
                                    </p>
                                    <br>
                                    {disclaimer_html}  <!-- Add the disclaimer at the bottom -->
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>
        </body>
    </html>
    """
    return md_text 


def format_market_summary(gpt_response):
    # Convert Markdown GPT response to HTML
    formatted_summary = markdown_to_html(gpt_response)
    return formatted_summary