import openai
import os
from dotenv import load_dotenv
from datetime import datetime
from zoneinfo import ZoneInfo

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

client = openai.OpenAI(api_key=api_key)

def analyze_sentiment_gpt(headlines, indices, sector_summary): 

    if not headlines:
        return "No headlines available for analysis."

    market_analysis_text = "\n".join(headlines) 

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

    prompt = f"""
    **Date & Time:** {formatted_time}  
    **Market Status:** {market_status}  

    Below are several stock market headlines, key economic data, and stats from major indices. Provide a **detailed market summary** that synthesizes key movements, trends, and themes observed today. Focus on identifying **major catalysts** and **emerging patterns** that investors should be aware of, with **actionable insights**.

    - **Prioritize consequential headlines**: Identify the headlines with the most significant **market impact**. Focus on high-impact events such as rate decisions, key economic data (CPI, jobs reports), major earnings surprises, or geopolitical events. 
    - **Minimize coverage** of minor fluctuations unless they signal a **broader trend**. Provide in-depth analysis for the most impactful stories only.

    Then, assess the **overall market sentiment** (Bullish, Bearish, or Neutral), explaining the reasoning behind it. If sentiment is mixed, highlight and explain the **conflicting signals** in the market.

    - Highlight any **major catalysts** driving market movements today, such as economic reports, earnings surprises, or geopolitical developments. **Explain the broader market context** and potential **uncertainty** surrounding these events.

    **Do not** list or analyze each headline separately—focus on providing a **cohesive, in-depth market summary** that offers value for investors.

    - Briefly summarize **index performance**, noting significant gains/losses and standout movements (e.g., tech leading, small caps lagging).

    Headlines:
    {market_analysis_text}

    Indices:
    {indices}

    Sector Performance:
    {sector_summary}

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

    ### Indices:
        Summarize the performance of major indices, including **significant gains or losses**. Mention any key movements within indices (e.g., tech leading, energy lagging). Be cautious in stating the **overall sentiment** and provide context where needed.

"""




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
