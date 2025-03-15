import json
from datetime import datetime
import re

def save_daily_newsletter(date, indices, sector_summary, sentiment_summary):
    # Structure the data
    data = {
        'date': date,
        'indices': indices,
        'sector_summary': sector_summary,
        'sentiment_summary': sentiment_summary
    }

    # Save the data to a JSON file
    try:
        # Check if the file exists and load the current data
        with open('daily_newsletter.json', 'r') as file:
            all_data = json.load(file)
    except FileNotFoundError:
        # If the file doesn't exist, start a new list
        all_data = []

    # Add the new data to the list
    all_data.append(data)

    # Write the updated data back to the file
    with open('daily_newsletter.json', 'w') as file:
        json.dump(all_data, file, indent=4)

    print(f"Saved market summary for {date}.")
# Function to split the large block of text into key points


def extract_key_points(newsletter_text):
    # Regular expression to extract the first paragraph and the part before "### Key Movements"
    first_paragraph_pattern = r"^(.*?)(?=\n\n)"
    before_key_movements_pattern = r"(.*?)(?=\n\n### Key Movements)"

    # Extract the first paragraph
    first_paragraph = re.search(first_paragraph_pattern, newsletter_text, re.DOTALL)
    if first_paragraph:
        first_paragraph = first_paragraph.group(1).strip()

    # Extract the content before the Key Movements section
    before_key_movements = re.search(before_key_movements_pattern, newsletter_text, re.DOTALL)
    if before_key_movements:
        before_key_movements = before_key_movements.group(1).strip()

    # Combine the first paragraph and the part before key movements
    relevant_content = f"{first_paragraph}\n\n{before_key_movements}"

    return relevant_content


# Function to save the key points into a JSON file
def store_summary_key_points(key_points):
    # Load existing summaries
    summaries = load_summaries()

    # Get the current date as a string
    today = datetime.now().strftime("%Y-%m-%d")

    # Add today's key points to the list
    summaries.append({
        'date': today,
        'key_points': key_points
    })

    # Save the updated summaries back to the file
    save_summaries(summaries)

def load_summaries():
    try:
        with open('summaries.json', 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        # If the file doesn't exist, return an empty list
        return []

def save_summaries(summaries):
    with open('summaries.json', 'w') as file:
        json.dump(summaries, file, indent=4)

# Function to get relevant past key points for context
def get_past_key_points():
    summaries = load_summaries()

    # Retrieve summaries from the last week
    past_summaries = [summary['key_points'] for summary in summaries if (datetime.now() - datetime.strptime(summary['date'], "%Y-%m-%d")).days <= 7]
    
    # Flatten the list of past summaries
    return [point for sublist in past_summaries for point in sublist]
