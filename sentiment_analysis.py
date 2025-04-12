import openai
import os
from dotenv import load_dotenv
from datetime import datetime
from zoneinfo import ZoneInfo
import tiktoken

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

client = openai.OpenAI(api_key=api_key)

# Function to analyze daily sentiment
def analyze_daily_sentiment_gpt(headlines, indices, sector_summary): 
    if not headlines:
        return "No headlines available for analysis."

    market_analysis_text = headlines

    now = datetime.now(ZoneInfo("America/New_York"))
    formatted_time = now.strftime("%A, %B %d, %Y - %I:%M %p %Z")

    # Determine if the market is open
    if now.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
        market_status = "Market is closed (Weekend)"
    elif now.hour < 9 or now.hour >= 16:
        market_status = "Market is closed (After Hours)"
    else:
        market_status = "Market is open"

    print(headlines)
    print(formatted_time)
    print(market_status)

    tokenizer = tiktoken.get_encoding("cl100k_base")

    prompt = f"""
    **Date & Time:** {formatted_time}  
    **Market Status:** {market_status}  

    Below are key stock market headlines, economic data, and index movements. Your job is to deliver a **concise and insightful market recap** for investors. Identify what mattered most today, what changed, and where attention should go next.

    Write in a sharp, professional tone. Avoid filler. Prioritize signal over noise. Highlight clear moves, reactions, and strategic takeaways — not just summaries.

    ---

    ### Core Instructions:
    - **Be brief, not shallow**: Short paragraphs with punchy insights. No wasted words.
    - **Use the data**: Headlines, descriptions, price % changes, and sector moves should drive your analysis.
    - **Don’t speculate**: All conclusions must be grounded in reported facts and clear patterns.
    - **Each section = unique insight**: Avoid restating themes between sections.

    ---

    Updates:
    {market_analysis_text}

    Indices:  
    {indices}

    Sector Performance:  
    {sector_summary}

    ---

    ### Market Summary:
    Outline the big picture. What defined today’s market — macro, sentiment, or sector moves? Keep it sharp and avoid repeating details from other sections. Point out **macro signals** or **unusual behavior**.

    ---

    ### Key Movements and Trends:
    Highlight what **actually moved** today — sectors, large caps, unexpected winners or laggards. Look for **rotations**, **momentum reversals**, or **sector divergence**.

    ---

    ### Major Catalysts:
    List major catalysts (earnings, economic data, geopolitical events). Focus on what changed market behavior — not just what happened.

    ---

    ### Sector Performance:
    Quickly scan the board — who led, who lagged, and why? Identify any **tradeable themes** or **early signals** in sectors that stood out.

    ---

    ### Market Sentiment:
    What's the tone? Bullish, bearish, or cautious? Use market behavior, VIX, volume, and sector flow to assess emotional context. Don’t rehash data — focus on interpretation.

    ---

    ### Conclusion:
    End with 2–3 **sharp takeaways** or forward-looking thoughts. Avoid fluff or summaries. Think like a strategist: what should readers watch next, or consider doing?
    """

    print(prompt)
    tokens = tokenizer.encode(prompt)
    num_tokens = len(tokens)
    print(f"Number of tokens: {num_tokens}")

    try:
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": "You are a financial analyst providing market summaries."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1
        )
        return response.choices[0].message.content.strip()

    except openai.RateLimitError:
        print("GPT-4 quota exceeded. Switching to GPT-3.5-turbo...")
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a financial analyst providing market summaries."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1
        )
        return response.choices[0].message.content.strip()

# Function to analyze weekly sentiment
def analyze_weekly_sentiment_gpt(weekend_headlines, weekly_data):
    if not weekend_headlines:
        return "No headlines available for analysis."

    # Extract market summaries from weekly data (excluding headlines and other data)
    market_summaries = []
    for data in weekly_data:
        if isinstance(data, dict) and "market_summary" in data:
            market_summaries.append(data["market_summary"])

    # Combine weekend headlines with weekly data
    market_analysis_text = "\n".join(weekend_headlines)

    weekly_data_text = "\n".join(market_summaries)  # Only use market summaries

    now = datetime.now(ZoneInfo("America/New_York"))
    formatted_time = now.strftime("%A, %B %d, %Y - %I:%M %p %Z")

    # Determine if the market is closed
    market_status = "Market is closed (Weekend)" if now.weekday() >= 5 else "Market is open"

    prompt = f"""
    **Date & Time:** {formatted_time}  
    **Market Status:** {market_status}  

    Below are stock market summaries from the past week. There are also stock news headlines from this weekend. Provide a **weekly market summary** that synthesizes key movements, trends, and themes observed during the past week. Focus on identifying **major catalysts** and **emerging patterns** that investors should be aware of, with **actionable insights**.

    - **Prioritize consequential headlines**: Identify the headlines with the most significant **market impact**. Focus on high-impact events such as rate decisions, key economic data (CPI, jobs reports), major earnings surprises, or geopolitical events. 
    - **Consider both stock performance data and headlines** when assessing overall market sentiment. The stock data, including sector and index performance, provides valuable insights into broader market trends.
    - **Minimize coverage** of minor fluctuations unless they signal a **broader trend**. Provide in-depth analysis for the most impactful stories only.

    Then, assess the **overall market sentiment** (Bullish, Bearish, or Neutral), explaining the reasoning behind it. If sentiment is mixed, highlight and explain the **conflicting signals** in the market.

    **Weekly Data (Past Week's Data & News):**
    {weekly_data_text}
    **Headlines from this Weekend***
    {market_analysis_text}

     **Stock Data (Indices and Sector Performance):**
    - **Indices:** Include significant changes, trends, and standout performances from major indices.
    - **Sectors:** Summarize the performance of key sectors, noting which sectors performed better or worse.

    Structure:
    ### Market Summary:
        Provide a concise, cohesive overview of today's market activity, including the most important trends and major market-moving events. Focus on providing **insights** that can influence investor decision-making. Avoid jumping to conclusions, and instead, present data-driven analysis that reflects the **uncertainty** of the current market.

    ### Key Movements and Trends:
        1. **Identify the top 3 key trends** in the market today. Prioritize trends that signal significant shifts or patterns. **Explain why these trends matter** for investors and if they represent long-term shifts or short-term fluctuations.
        2. **Explain the broader market context** around these trends and **discuss the potential risks** that could arise.

    ### Major Catalysts:
        Identify and describe the **top 3 catalysts** driving today's market movements. These could include macroeconomic data, earnings, or geopolitical events. Provide **insights into the potential market impact** of each catalyst.
        - If applicable, discuss **multiple interpretations** of the catalyst’s impact on the market (e.g., "rate cuts could stimulate growth, but may also signal a potential economic slowdown").

    ### Sector Performance:
        Summarize sector performance, focusing on which sectors **outperformed** and which **underperformed**. Identify any **sector rotations** or standout moves. 
        - For example, did **technology** outperform, or did **energy** take a hit? Are there signs of investors **rotating into defensive sectors**?
        - Discuss any **uncertainty** or **potential risks** related to sector performance.

    ### Overall Market Sentiment:
        Provide a clear analysis of market sentiment: **Bullish**, **Bearish**, or **Neutral**. Explain the reasoning behind your sentiment assessment and **highlight any conflicting signals** or risks that investors should be aware of.

    ### Conclusion:
        **Summarize key takeaways** for investors, providing actionable insights or strategies based on the day’s market performance. Ensure that any recommendations are data-backed and include a **clear risk assessment**.

    ### Forward Guidance (Investor Tips):
        Based on the analysis above, provide guidance and recommendations for investors moving forward:
        - **What are the best strategies for the coming week?**
        - **Should investors be cautious or optimistic?**
        - **What sectors or indices should investors focus on?**
        - **Are there any risks to watch out for or opportunities to seize?**
        - **Is now a good time to buy, hold, or sell?**
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a financial analyst providing market summaries."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1
        )
        return response.choices[0].message.content.strip()
    
    except openai.RateLimitError:
        print("GPT-4 quota exceeded. Switching to GPT-3.5-turbo...")
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a financial analyst providing market summaries."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1
        )
        return response.choices[0].message.content.strip()
